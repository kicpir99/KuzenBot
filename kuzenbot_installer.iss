[Setup]
; --- Podstawowe informacje ---
AppName=KuzenBot App
AppVersion=1.1.8
AppPublisher=kicpir99
DefaultDirName={autopf}\KuzenBot
DefaultGroupName=KuzenBot

; --- Ustawienia pliku wyjściowego ---
OutputDir=Output
OutputBaseFilename=KuzenBot_Setup_v1_1_8
Compression=lzma
SolidCompression=yes
SetupIconFile=assets\logo.ico
CloseApplications=yes

; --- WYBÓR JĘZYKA ---
ShowLanguageDialog=yes
LanguageDetectionMethod=none

[Languages]
; Angielski i Polski
Name: "en"; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: "info_en.rtf"; InfoAfterFile: "after_en.rtf"
Name: "pl"; MessagesFile: "compiler:Languages\Polish.isl"; InfoBeforeFile: "info_pl.rtf"; InfoAfterFile: "after_pl.rtf"

; Francuski, Niemiecki, Hiszpański
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"; InfoBeforeFile: "info_fr.rtf"; InfoAfterFile: "after_fr.rtf"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"; InfoBeforeFile: "info_de.rtf"; InfoAfterFile: "after_de.rtf"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"; InfoBeforeFile: "info_es.rtf"; InfoAfterFile: "after_es.rtf"

; Rosyjski, Ukraiński, Portugalski, Chiński
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"; InfoBeforeFile: "info_ru.rtf"; InfoAfterFile: "after_ru.rtf"
Name: "uk"; MessagesFile: "compiler:Languages\Ukrainian.isl"; InfoBeforeFile: "info_uk.rtf"; InfoAfterFile: "after_uk.rtf"
Name: "pt"; MessagesFile: "compiler:Languages\Portuguese.isl"; InfoBeforeFile: "info_pt.rtf"; InfoAfterFile: "after_pt.rtf"
Name: "zh"; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: "info_zh.rtf"; InfoAfterFile: "after_zh.rtf"

[Tasks]
; Opcja utworzenia skrótu na pulpicie (zaznaczona domyślnie)
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkablealone

[Files]
Source: "dist\KuzenBot_App\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\KuzenBot"; Filename: "{app}\KuzenBot_App.exe"
Name: "{autodesktop}\KuzenBot"; Filename: "{app}\KuzenBot_App.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\KuzenBot_App.exe"; Description: "{cm:LaunchProgram,KuzenBot}"; Flags: nowait postinstall shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  // Wymuszone zamknięcie starej aplikacji w tle przed startem instalatora
  ShellExec('open', 'taskkill.exe', '/F /IM KuzenBot_App.exe', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
  Result := True;
end;