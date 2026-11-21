$ErrorActionPreference = "Stop"

$projectFolder = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherPath = Join-Path $projectFolder "iniciar_mateo.vbs"
$startupFolder = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupFolder "Mateo.lnk"

if (-not (Test-Path -LiteralPath $launcherPath)) {
    throw "No encuentro iniciar_mateo.vbs en $projectFolder"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "$env:WINDIR\System32\wscript.exe"
$shortcut.Arguments = "`"$launcherPath`""
$shortcut.WorkingDirectory = $projectFolder
$shortcut.Description = "Iniciar el asistente local Mateo al iniciar sesión"
$shortcut.Save()

Write-Host "Inicio automático configurado: Mateo se abrirá al iniciar sesión en Windows."
Write-Host "Para desactivarlo, elimina este acceso directo: $shortcutPath"
