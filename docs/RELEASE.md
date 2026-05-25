# Релизный процесс

## Перед релизом

1. Обновите `README.md` и docs.
2. Проверьте запуск:

```powershell
.\setup.ps1
.\start.ps1
```

3. Проверьте API и UI вручную.

## Публикация

```powershell
git add .
git commit -m "release: <version>"
git push origin main
```

## Сборка инсталлятора

```powershell
cd installer
.\build-installer.ps1 -RepoUrl https://github.com/ohehelv/clipmaker.git -RepoRef main
```

## Артефакты

- GitHub репозиторий (`main`).
- `installer/output/KaraokeMakerSetup.exe`.
