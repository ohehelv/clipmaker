#define MyAppName "Karaoke Maker"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "ClipMaker"
#define MyAppExeName "run-karaoke-maker.ps1"

; Перед сборкой замените URL на ваш репозиторий.
#ifndef RepoUrl
  #define RepoUrl "https://github.com/REPLACE_ME/clipmaker.git"
#endif

#ifndef RepoRef
  #define RepoRef "main"
#endif

[Setup]
AppId={{2D65B6EE-92AE-41AF-B9D0-0B90A8D4CC68}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\KaraokeMaker
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=output
OutputBaseFilename=KaraokeMakerSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupLogging=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

[Files]
Source: "bootstrap-install.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "run-karaoke-maker.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Запустить {#MyAppName}"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\run-karaoke-maker.ps1"""; WorkingDir: "{app}"
Name: "{autodesktop}\Запустить {#MyAppName}"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\run-karaoke-maker.ps1"""; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: unchecked

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\bootstrap-install.ps1"" -RepoUrl ""{#RepoUrl}"" -RepoRef ""{#RepoRef}"" -InstallRoot ""{app}"" -AppName ""{#MyAppName}"""; \
  StatusMsg: "Первичная настройка Docker-проекта..."; \
  Flags: postinstall waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
