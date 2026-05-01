<#
.SYNOPSIS
    Ejecuta en paralelo la Cuenta 1 y Cuenta 2 del config.json.

.DESCRIPTION
    Lanza dos procesos de Python en paralelo:
    - Cuenta activa #1
    - Cuenta activa #2

    Simplificado: toda la salida se guarda en un unico log:
    - task_log.txt
#>

param(
    [string]$ConfigPath = "config.json",
    [string]$PythonExe = "C:\Users\ArielPlayit\AppData\Local\Programs\Python\Python312\python.exe",
    [string]$ScriptName = "post_to_groups_selenium.py",
    [string]$MainLogPath = "task_log.txt"
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$FullConfigPath = Join-Path $ScriptDir $ConfigPath
$FullScriptPath = Join-Path $ScriptDir $ScriptName
$FullMainLogPath = Join-Path $ScriptDir $MainLogPath
$TempLogDir = Join-Path ([System.IO.Path]::GetTempPath()) "facebook-upload-automatization"
$RunId = Get-Date -Format "yyyyMMdd_HHmmss_fff"
$ReadyDir = Join-Path $TempLogDir "ready_$RunId"

function Write-MainLog {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $FullMainLogPath -Value "[$ts] $Message"
}

if (-not (Test-Path $FullConfigPath)) {
    throw "No se encontro config: $FullConfigPath"
}
if (-not (Test-Path $FullScriptPath)) {
    throw "No se encontro script principal: $FullScriptPath"
}
if (-not (Test-Path $PythonExe)) {
    throw "No se encontro Python en: $PythonExe"
}

# Verificar que haya al menos 2 cuentas activas.
$rawConfig = Get-Content -Path $FullConfigPath -Raw -Encoding UTF8
$configJson = $rawConfig | ConvertFrom-Json

$accounts = @()
if ($null -ne $configJson.accounts) {
    $accounts = @($configJson.accounts)
} else {
    $accounts = @($configJson)
}

$activeAccounts = @($accounts | Where-Object { -not $_.suspended })
if ($activeAccounts.Count -lt 1) {
    throw "No hay cuentas activas (suspended=false) para ejecutar."
}

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
# Evita que un proceso cierre Edge del otro cuando ambos corren a la vez.
$env:FB_DISABLE_EDGE_CLEANUP = "1"

# Limpia logs legacy de ejecuciones anteriores para reducir ruido.
$legacyLogs = @(
    "task_log_parallel.txt",
    "task_log_account1.txt",
    "task_log_account2.txt",
    "task_log_account1.error.txt",
    "task_log_account2.error.txt"
)
foreach ($legacyLog in $legacyLogs) {
    $legacyPath = Join-Path $ScriptDir $legacyLog
    if (Test-Path $legacyPath) {
        Remove-Item $legacyPath -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path $TempLogDir)) {
    New-Item -Path $TempLogDir -ItemType Directory -Force | Out-Null
}
New-Item -Path $ReadyDir -ItemType Directory -Force | Out-Null

Get-ChildItem -Path $TempLogDir -Filter "__tmp_account*.log" -File -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

# Limpieza de temporales antiguos que vivian en la carpeta del proyecto.
Get-ChildItem -Path $ScriptDir -Filter "__tmp_account*.log" -File -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-MainLog "Iniciando modo paralelo: cuenta activa #1 y #2"
Write-MainLog "Config: $FullConfigPath"

$expectedReady = if ($activeAccounts.Count -eq 1) { 1 } else { 2 }
$env:FB_PARALLEL_READY_DIR = $ReadyDir
$env:FB_PARALLEL_EXPECTED_READY = [string]$expectedReady
$env:FB_PARALLEL_READY_TIMEOUT = "90"
Write-MainLog "Barrera de navegadores activa: esperando $expectedReady navegador(es)"

$argsAccount1 = @(
    "-u",
    $FullScriptPath,
    "--config", $FullConfigPath,
    "--account-index", "1"
)

$argsAccount2 = @(
    "-u",
    $FullScriptPath,
    "--config", $FullConfigPath,
    "--account-index", "2"
)
$tmpOut1 = Join-Path $TempLogDir "__tmp_account1.out.log"
$tmpErr1 = Join-Path $TempLogDir "__tmp_account1.err.log"
$tmpOut2 = Join-Path $TempLogDir "__tmp_account2.out.log"
$tmpErr2 = Join-Path $TempLogDir "__tmp_account2.err.log"

foreach ($tmpFile in @($tmpOut1, $tmpErr1, $tmpOut2, $tmpErr2)) {
    if (Test-Path $tmpFile) {
        Remove-Item $tmpFile -Force -ErrorAction SilentlyContinue
    }
}

if ($activeAccounts.Count -eq 1) {
    Write-MainLog "Solo hay una cuenta activa; ejecutando en modo simple con la cuenta #1 activa."
    $env:FB_PARALLEL_READY_NAME = "account1"
    $p1 = Start-Process -FilePath $PythonExe -ArgumentList @(
        "-u",
        $FullScriptPath,
        "--config", $FullConfigPath,
        "--account-index", "1"
    ) -WorkingDirectory $ScriptDir -RedirectStandardOutput $tmpOut1 -RedirectStandardError $tmpErr1 -WindowStyle Hidden -PassThru
    $p2 = $null
} else {
    $env:FB_PARALLEL_READY_NAME = "account1"
    $p1 = Start-Process -FilePath $PythonExe -ArgumentList $argsAccount1 -WorkingDirectory $ScriptDir -RedirectStandardOutput $tmpOut1 -RedirectStandardError $tmpErr1 -WindowStyle Hidden -PassThru
    $env:FB_PARALLEL_READY_NAME = "account2"
    $p2 = Start-Process -FilePath $PythonExe -ArgumentList $argsAccount2 -WorkingDirectory $ScriptDir -RedirectStandardOutput $tmpOut2 -RedirectStandardError $tmpErr2 -WindowStyle Hidden -PassThru
}
Remove-Item Env:\FB_PARALLEL_READY_NAME -ErrorAction SilentlyContinue

if ($p2) {
    Write-MainLog "Procesos lanzados: Cuenta1 PID=$($p1.Id), Cuenta2 PID=$($p2.Id)"
} else {
    Write-MainLog "Proceso lanzado: Cuenta1 PID=$($p1.Id)"
}

$p1 | Wait-Process
if ($p2) {
    $p2 | Wait-Process
}

$p1.Refresh()
$exit1 = if ($null -eq $p1.ExitCode) { 1 } else { $p1.ExitCode }

if ($p2) {
    $p2.Refresh()
    $exit2 = if ($null -eq $p2.ExitCode) { 1 } else { $p2.ExitCode }
} else {
    $exit2 = 0
}

function Merge-TempLog {
    param(
        [string]$Label,
        [string]$OutPath,
        [string]$ErrPath
    )

    $streams = @(
        @{ Name = "stdout"; Path = $OutPath },
        @{ Name = "stderr"; Path = $ErrPath }
    )

    foreach ($stream in $streams) {
        $streamPath = [string]$stream.Path
        if (-not (Test-Path $streamPath)) {
            continue
        }

        try {
            $content = Get-Content -Path $streamPath -Raw -ErrorAction Stop
            if ($content) {
                Write-MainLog "[$Label][$($stream.Name)]"
                Add-Content -Path $FullMainLogPath -Value $content
            }
        } catch {
            Write-MainLog "No se pudo mezclar $streamPath en ${FullMainLogPath}: $($_.Exception.Message)"
        } finally {
            Remove-Item $streamPath -Force -ErrorAction SilentlyContinue
        }
    }
}

Merge-TempLog -Label "Cuenta1" -OutPath $tmpOut1 -ErrPath $tmpErr1
if ($p2) {
    Merge-TempLog -Label "Cuenta2" -OutPath $tmpOut2 -ErrPath $tmpErr2
}

Remove-Item $ReadyDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item Env:\FB_PARALLEL_READY_DIR -ErrorAction SilentlyContinue
Remove-Item Env:\FB_PARALLEL_EXPECTED_READY -ErrorAction SilentlyContinue
Remove-Item Env:\FB_PARALLEL_READY_TIMEOUT -ErrorAction SilentlyContinue

Write-MainLog "Cuenta1 finalizo con codigo: $exit1"
Write-MainLog "Cuenta2 finalizo con codigo: $exit2"

if ($exit1 -ne 0 -or $exit2 -ne 0) {
    Write-MainLog "Finalizado con errores en modo paralelo"
    exit 1
}

Write-MainLog "Finalizado correctamente en modo paralelo"
exit 0
