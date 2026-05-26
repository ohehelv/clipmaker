"""Выравнивание лирики по аудио через faster-whisper.

Идея: транскрибируем с word-level таймкодами, затем строка пользовательской
лирики прижимается к диапазону распознанных слов методом нечёткого совпадения
(rapidfuzz). Это даёт устойчивость к опечаткам и неточностям ASR.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from rapidfuzz import fuzz

from ..config import settings


@dataclass
class WordTs:
    word: str
    start: float
    end: float


@dataclass
class LyricLine:
    text: str
    start: float
    end: float


_WORD_RE = re.compile(r"[\w']+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


_whisper_model = None
_whisper_backend: tuple[str, str] | None = None


def _is_cuda_runtime_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return (
        "cuda failed" in msg
        or "cuda driver version is insufficient" in msg
        or "cudart" in msg
    )


def _build_whisper(device: str, compute_type: str):
    from faster_whisper import WhisperModel  # отложенный импорт (тяжёлый)
    import os
    cpu_threads = settings.whisper_cpu_threads
    if device == "cpu" and cpu_threads <= 0:
        cpu_threads = os.cpu_count() or 4
    return WhisperModel(
        settings.whisper_model,
        device=device,
        compute_type=compute_type,
        cpu_threads=cpu_threads,
        num_workers=max(1, settings.whisper_num_workers),
    )


def _get_whisper():
    global _whisper_model, _whisper_backend
    if _whisper_model is None:
        try:
            _whisper_model = _build_whisper(settings.whisper_device, settings.whisper_compute_type)
            _whisper_backend = (settings.whisper_device, settings.whisper_compute_type)
        except RuntimeError as e:
            # На серверах/контейнерах без совместимого CUDA не валим задачу, а уходим на CPU.
            if settings.whisper_device.startswith("cuda") and _is_cuda_runtime_error(e):
                print("[alignment] CUDA недоступна для Whisper, fallback на CPU int8")
                _whisper_model = _build_whisper("cpu", "int8")
                _whisper_backend = ("cpu", "int8")
            else:
                raise
    return _whisper_model


def transcribe_words(audio_path: Path, language: Optional[str] = None) -> List[WordTs]:
    global _whisper_model, _whisper_backend
    model = _get_whisper()
    try:
        segments, _info = model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=True,
            vad_filter=True,
        )
    except RuntimeError as e:
        # Если CUDA отвалилась уже во время transcribe — пересоздаём модель на CPU и ретраим один раз.
        if _whisper_backend and _whisper_backend[0].startswith("cuda") and _is_cuda_runtime_error(e):
            print("[alignment] CUDA ошибка во время transcribe, переключение Whisper на CPU int8")
            _whisper_model = _build_whisper("cpu", "int8")
            _whisper_backend = ("cpu", "int8")
            segments, _info = _whisper_model.transcribe(
                str(audio_path),
                language=language,
                word_timestamps=True,
                vad_filter=True,
            )
        else:
            raise
    words: List[WordTs] = []
    for seg in segments:
        if not seg.words:
            continue
        for w in seg.words:
            txt = (w.word or "").strip().lower()
            txt = "".join(ch for ch in txt if ch.isalnum() or ch in "'-")
            if not txt:
                continue
            words.append(WordTs(word=txt, start=float(w.start), end=float(w.end)))
    return words


def align_lyrics(
    audio_path: Path,
    lyrics_text: str,
    language: Optional[str] = None,
    audio_duration: Optional[float] = None,
) -> List[LyricLine]:
    """Возвращает список строк лирики с временными границами.

    Если лирика пустая — возвращает строки, восстановленные из ASR
    (одна "строка" = одна сегментная фраза). Если лирика задана, пытаемся
    прижать каждую строку к лучшей подпоследовательности распознанных слов.
    """
    lines = [ln.strip() for ln in lyrics_text.splitlines() if ln.strip()]
    words = transcribe_words(audio_path, language=language)

    if not words:
        # ASR ничего не дал — равномерно разложим строки или вернём пусто
        if not lines or not audio_duration:
            return []
        step = audio_duration / max(1, len(lines))
        return [LyricLine(text=ln, start=i * step, end=(i + 1) * step) for i, ln in enumerate(lines)]

    if not lines:
        # сделаем по словам грубые "строки" по 6-8 слов
        chunks: list[list[WordTs]] = []
        size = 7
        for i in range(0, len(words), size):
            chunks.append(words[i:i + size])
        return [
            LyricLine(text=" ".join(w.word for w in c), start=c[0].start, end=c[-1].end)
            for c in chunks if c
        ]

    # Жадное выравнивание: для каждой строки подбираем окно слов с лучшим fuzz.
    out: List[LyricLine] = []
    cursor = 0
    n = len(words)
    last_end = words[0].start if n else 0.0
    for li, line in enumerate(lines):
        if cursor >= n:
            # слова закончились — равномерно раскидать остаток до конца аудио
            remaining = lines[li:]
            tail_start = last_end
            tail_end = audio_duration if audio_duration else (words[-1].end if n else tail_start + len(remaining))
            step = max(0.5, (tail_end - tail_start) / max(1, len(remaining)))
            for k, rl in enumerate(remaining):
                s = tail_start + k * step
                out.append(LyricLine(text=rl, start=s, end=s + step))
            break
        toks = _tokens(line)
        win_len = max(2, len(toks))
        best_score = -1.0
        best_i = cursor
        best_j = min(n, cursor + win_len)
        # окно вокруг курсора +- 50% длины
        search_from = cursor
        search_to = min(n, cursor + win_len * 4 + 10)
        for i in range(search_from, max(search_from + 1, search_to - win_len + 1)):
            for span in (win_len, win_len + 1, win_len + 2, max(2, win_len - 1)):
                j = min(n, i + span)
                if j <= i:
                    continue
                cand = " ".join(w.word for w in words[i:j])
                score = fuzz.token_set_ratio(" ".join(toks), cand)
                if score > best_score:
                    best_score = score
                    best_i, best_j = i, j
        # защита от выхода за границы
        best_i = max(0, min(best_i, n - 1))
        best_j = max(best_i + 1, min(best_j, n))
        start = words[best_i].start
        end = words[best_j - 1].end
        out.append(LyricLine(text=line, start=start, end=end))
        last_end = end
        cursor = best_j

    # пост-обработка: убрать пересечения и нулевые длины
    for i, ln in enumerate(out):
        if i > 0 and ln.start < out[i - 1].end:
            ln.start = out[i - 1].end
        if ln.end <= ln.start:
            ln.end = ln.start + 1.0
    return out
