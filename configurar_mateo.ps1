$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$projectFolder = Split-Path -Parent $MyInvocation.MyCommand.Path
$requirementsPath = Join-Path $projectFolder "requirements.txt"
$venvFolder = Join-Path $projectFolder ".venv"
$pythonPath = Join-Path $venvFolder "Scripts\python.exe"
$modelsFolder = Join-Path $projectFolder "modelos"
$voskName = "vosk-model-small-es-0.42"
$voskFolder = Join-Path $modelsFolder $voskName
$piperFolder = Join-Path $modelsFolder "piper"
$whisperFolder = Join-Path $modelsFolder "whisper"
$ollamaModel = "qwen3:8b"

function Assert-LastExitCode([string]$step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$step terminó con el código $LASTEXITCODE. Revisa el mensaje anterior y vuelve a ejecutar este instalador."
    }
}

function Find-Ollama {
    $command = Get-Command "ollama" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $possiblePaths = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"),
        (Join-Path $env:ProgramFiles "Ollama\ollama.exe")
    )
    foreach ($path in $possiblePaths) {
        if ($path -and (Test-Path -LiteralPath $path -PathType Leaf)) {
            return $path
        }
    }
    return $null
}

function Get-OllamaTags {
    try {
        return Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3
    }
    catch {
        return $null
    }
}

Write-Host "Configurando Mateo en: $projectFolder" -ForegroundColor Cyan

if (-not (Get-Command "py" -ErrorAction SilentlyContinue)) {
    throw "No encuentro el lanzador de Python. Instala Python 3.13 y vuelve a ejecutar configurar_mateo.ps1."
}

& py -3.13 --version
Assert-LastExitCode "La comprobación de Python 3.13"

if (-not (Test-Path -LiteralPath $requirementsPath -PathType Leaf)) {
    throw "No encuentro requirements.txt en $projectFolder"
}

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    Write-Host "Creando un entorno Python aislado..." -ForegroundColor Cyan
    & py -3.13 -m venv $venvFolder
    Assert-LastExitCode "La creación del entorno virtual"
}

Write-Host "Instalando dependencias de Python..." -ForegroundColor Cyan
& $pythonPath -m pip install --upgrade pip
Assert-LastExitCode "La actualización de pip"
& $pythonPath -m pip install -r $requirementsPath
Assert-LastExitCode "La instalación de dependencias"

New-Item -ItemType Directory -Path $modelsFolder -Force | Out-Null
New-Item -ItemType Directory -Path $piperFolder -Force | Out-Null
New-Item -ItemType Directory -Path $whisperFolder -Force | Out-Null

$voskConfig = Join-Path $voskFolder "conf\model.conf"
if (-not (Test-Path -LiteralPath $voskConfig -PathType Leaf)) {
    if (Test-Path -LiteralPath $voskFolder) {
        throw "La carpeta $voskFolder existe, pero el modelo Vosk parece incompleto. Revisa esa carpeta y vuelve a ejecutar el instalador."
    }

    Write-Host "Descargando el reconocimiento de voz español (39 MB)..." -ForegroundColor Cyan
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    $downloadRoot = [IO.Path]::GetFullPath((Join-Path $tempRoot ("mateo-vosk-" + [Guid]::NewGuid().ToString("N"))))
    if (-not $downloadRoot.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "La carpeta temporal calculada no es segura: $downloadRoot"
    }
    New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
    $zipPath = Join-Path $downloadRoot "$voskName.zip"
    try {
        Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/$voskName.zip" -OutFile $zipPath -UseBasicParsing
        Expand-Archive -LiteralPath $zipPath -DestinationPath $downloadRoot -Force
        $extractedVosk = Join-Path $downloadRoot $voskName
        if (-not (Test-Path -LiteralPath (Join-Path $extractedVosk "conf\model.conf") -PathType Leaf)) {
            throw "El archivo descargado no contiene el modelo Vosk esperado."
        }
        Move-Item -LiteralPath $extractedVosk -Destination $voskFolder
    }
    finally {
        if ($downloadRoot.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $downloadRoot)) {
            Remove-Item -LiteralPath $downloadRoot -Recurse -Force
        }
    }
}
else {
    Write-Host "Modelo Vosk español ya disponible." -ForegroundColor DarkGray
}

$piperVoice = Join-Path $piperFolder "es_ES-sharvard-medium.onnx"
if (-not (Test-Path -LiteralPath $piperVoice -PathType Leaf)) {
    Write-Host "Descargando la voz española de Mateo..." -ForegroundColor Cyan
    & $pythonPath -m piper.download_voices es_ES-sharvard-medium --data-dir $piperFolder
    Assert-LastExitCode "La descarga de la voz Piper"
}
else {
    Write-Host "Voz Piper ya disponible." -ForegroundColor DarkGray
}

Write-Host "Preparando el reconocimiento Whisper para que no descargue al primer arranque..." -ForegroundColor Cyan
$env:MATEO_WHISPER_DIR = $whisperFolder
$whisperSetup = "import os; from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8', download_root=os.environ['MATEO_WHISPER_DIR']); print('Modelo Whisper listo.')"
& $pythonPath -c $whisperSetup
Assert-LastExitCode "La descarga del modelo Whisper"
Remove-Item Env:\MATEO_WHISPER_DIR -ErrorAction SilentlyContinue

$ollamaPath = Find-Ollama
if (-not $ollamaPath) {
    throw "No encuentro Ollama. Instálalo desde https://ollama.com/download/windows y vuelve a ejecutar este instalador."
}

$ollamaTags = Get-OllamaTags
if (-not $ollamaTags) {
    Write-Host "Iniciando el servicio local de Ollama..." -ForegroundColor Cyan
    Start-Process -FilePath $ollamaPath -ArgumentList "serve" -WindowStyle Hidden
    for ($attempt = 0; $attempt -lt 30 -and -not $ollamaTags; $attempt++) {
        Start-Sleep -Seconds 2
        $ollamaTags = Get-OllamaTags
    }
}
if (-not $ollamaTags) {
    throw "Ollama está instalado, pero no responde en localhost:11434. Abre Ollama y vuelve a ejecutar este instalador."
}

$modelIsInstalled = @($ollamaTags.models | ForEach-Object { $_.name }) -contains $ollamaModel
if (-not $modelIsInstalled) {
    Write-Host "Falta el modelo local $ollamaModel (descarga aproximada: 5,2 GB; no consume créditos de API)." -ForegroundColor Yellow
    $downloadModel = Read-Host "¿Quieres descargarlo ahora? (S/N)"
    if ($downloadModel -notmatch "^(s|si|sí|y|yes)$") {
        Write-Host "No lo he descargado. Para continuar más tarde, ejecuta: ollama pull $ollamaModel" -ForegroundColor Yellow
        Write-Host "Cuando termine, vuelve a ejecutar configurar_mateo.ps1 para añadir Mateo al inicio automático."
        return
    }
    & $ollamaPath pull $ollamaModel
    Assert-LastExitCode "La descarga del modelo Ollama"
}
else {
    Write-Host "Modelo Ollama $ollamaModel ya disponible." -ForegroundColor DarkGray
}

Write-Host "Configurando el inicio automático de Mateo..." -ForegroundColor Cyan
$startupScript = Join-Path $projectFolder "instalar_inicio_automatico.ps1"
if (-not (Test-Path -LiteralPath $startupScript -PathType Leaf)) {
    throw "No encuentro instalar_inicio_automatico.ps1 en $projectFolder"
}
& $startupScript
Assert-LastExitCode "La configuración del inicio automático"

Write-Host "" 
Write-Host "Mateo ya está configurado. Para abrirlo ahora, ejecuta:" -ForegroundColor Green
Write-Host "  wscript.exe `"$(Join-Path $projectFolder 'iniciar_mateo.vbs')`"" -ForegroundColor Green
Write-Host "También se iniciará al entrar en Windows."
