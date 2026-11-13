; Inno Setup script para NutricionAgent
; Build:
;   iscc installer.iss
; Requiere: dist\NutricionAgent\ generado por PyInstaller.

#define MyAppName "NutricionAgent"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "NutricionAgent"
#define MyAppURL "https://github.com/tu-usuario/NutricionAgent"
#define MyAppExeName "NutricionAgent.exe"

[Setup]
AppId={{8D3B5C1E-9A2F-4B7D-8C1E-5F6A7B8C9D0E}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=NutricionAgent-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableDirPage=no
UsePreviousAppDir=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "dist\NutricionAgent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
Filename: "https://ollama.com/download/windows"; Description: "Descargar Ollama (necesario para la IA)"; Flags: shellexec nowait postinstall skipifsilent unchecked

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir, EnvFile, ExampleEnv, VaultDir: string;
  Lines: TArrayOfString;
  i: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigDir := ExpandConstant('{localappdata}\NutricionAgent');
    EnvFile := ConfigDir + '\.env';
    ExampleEnv := ExpandConstant('{app}\.env.example');
    VaultDir := ConfigDir + '\data\vault';

    if not DirExists(ConfigDir) then
      ForceDirectories(ConfigDir);
    if not DirExists(VaultDir) then
      ForceDirectories(VaultDir);

    if (not FileExists(EnvFile)) and FileExists(ExampleEnv) then
    begin
      if LoadStringsFromFile(ExampleEnv, Lines) then
        SaveStringsToFile(EnvFile, Lines, False);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigDir: string;
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    ConfigDir := ExpandConstant('{localappdata}\NutricionAgent');
    if DirExists(ConfigDir) then
    begin
      if MsgBox('¿Quieres borrar también tus datos de NutricionAgent?' + #13#10 +
                '(' + ConfigDir + ')', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      begin
        DelTree(ConfigDir, True, True, True);
      end;
    end;
  end;
end;