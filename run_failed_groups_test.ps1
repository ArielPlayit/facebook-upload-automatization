<#
.SYNOPSIS
    Ejecuta una prueba solo en los grupos que fallaron recientemente.

.DESCRIPTION
    Genera un config temporal basado en config.json, dejando solo los grupos
    indicados (por defecto: los 4 que fallaron en el run 9/13), y lanza
    post_to_groups_selenium.py con --debug-on-failure.

    Esto permite validar rápido si el error fue corregido sin publicar en
    todos los grupos.
#>

param(
    [string]$ConfigPath = "config.json",
    [string]$PythonExe = "C:\Users\ArielPlayit\AppData\Local\Programs\Python\Python312\python.exe",
    [int]$Delay = 15,
    [switch]$Headless,
    [switch]$NoDebugArtifacts,
    [string]$LogPath = "task_log_failed_groups_test.txt",
    [string]$TaskLogPath = "task_log.txt",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$GroupIds
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$FullConfigPath = Join-Path $ScriptDir $ConfigPath
$TempConfigPath = Join-Path $ScriptDir "config.failed-groups.test.json"
$FullLogPath = Join-Path $ScriptDir $LogPath
$FullTaskLogPath = Join-Path $ScriptDir $TaskLogPath

function Get-FailedGroupsFromLastRun {
    param([string]$TaskLogFile)

    if (-not (Test-Path $TaskLogFile)) {
        return @()
    }

    # Usar la codificación por defecto para tolerar logs antiguos en ANSI/UTF-16.
    $lines = Get-Content -Path $TaskLogFile
    if (-not $lines -or $lines.Count -eq 0) {
        return @()
    }

    $startIdx = -1
    $totalGroups = 0
    for ($i = $lines.Count - 1; $i -ge 0; $i--) {
        if ($lines[$i] -match 'INICIANDO \[.*\] - (\d+) grupo\(s\)') {
            $startIdx = $i
            $totalGroups = [int]$Matches[1]
            break
        }
    }

    if ($startIdx -lt 0 -or $totalGroups -le 0) {
        return @()
    }

    $processingRegex = '^\s*(?:\[[^\]]+\]\s*)?\[(\d+)/' + $totalGroups + '\]\s+Procesando grupo:\s+(.+)$'
    $failedRegex = '^\s*(?:\[[^\]]+\]\s*)?[^\[]*\[(\d+)/' + $totalGroups + '\].*fallida'
    $summaryRegex = 'RESUMEN \[.*\]: \d+\/' + $totalGroups + ' .*exitosas'

    $currentGroup = ''
    $failed = New-Object System.Collections.Generic.List[string]
    for ($i = $startIdx; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($line -match $summaryRegex) {
            break
        }
        if ($line -match $processingRegex) {
            $currentGroup = $Matches[2].Trim()
            continue
        }
        if ($line -match $failedRegex) {
            if ($currentGroup) {
                $failed.Add($currentGroup)
            }
        }
    }

    return @($failed | Select-Object -Unique)
}

if (-not (Test-Path $FullConfigPath)) {
    throw "No se encontro el config: $FullConfigPath"
}

if (-not (Test-Path $PythonExe)) {
    throw "No se encontro Python en: $PythonExe"
}

if (-not $GroupIds -or $GroupIds.Count -eq 0) {
    $GroupIds = Get-FailedGroupsFromLastRun -TaskLogFile $FullTaskLogPath
    if ($GroupIds.Count -eq 0) {
        throw "No se pudieron detectar grupos fallidos desde $FullTaskLogPath. Pasa -GroupIds manualmente."
    }
}

Write-Host "=== Test de grupos fallidos ===" -ForegroundColor Cyan
Write-Host "Config base: $FullConfigPath"
Write-Host "Grupos objetivo: $($GroupIds -join ', ')"
Write-Host "Log de prueba: $FullLogPath"

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $FullLogPath -Value "[$timestamp] Inicio test grupos fallidos"
Add-Content -Path $FullLogPath -Value "[$timestamp] Config base: $FullConfigPath"
Add-Content -Path $FullLogPath -Value "[$timestamp] GroupIds: $($GroupIds -join ', ')"

# Cargar config preservando UTF-8 (incluye BOM si existe)
$raw = Get-Content -Path $FullConfigPath -Raw -Encoding UTF8
$config = $raw | ConvertFrom-Json

# Normalizar a formato con accounts
$accounts = @()
if ($null -ne $config.accounts) {
    $accounts = @($config.accounts)
} else {
    $accounts = @($config)
}

if ($accounts.Count -eq 0) {
    throw "El config no contiene cuentas para ejecutar."
}

# Seleccionar primera cuenta activa (mismo criterio del script principal)
$selected = $null
foreach ($acc in $accounts) {
    if (-not $acc.suspended) {
        $selected = $acc
        break
    }
}

if ($null -eq $selected) {
    throw "No hay cuentas activas (suspended=false)."
}

# Filtrar grupos por IDs objetivo
$selectedGroups = @()
foreach ($g in $selected.groups) {
    if ($GroupIds -contains [string]$g.id) {
        $selectedGroups += $g
    }
}

if ($selectedGroups.Count -eq 0) {
    throw "No se encontro ninguno de los GroupIds en la cuenta activa."
}

$missing = @()
foreach ($gid in $GroupIds) {
    $found = $false
    foreach ($g in $selectedGroups) {
        if ([string]$g.id -eq [string]$gid) {
            $found = $true
            break
        }
    }
    if (-not $found) {
        $missing += $gid
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Aviso: estos GroupIds no estan en config y se omitiran: $($missing -join ', ')" -ForegroundColor Yellow
}

# Construir config temporal con solo una cuenta y grupos filtrados
$testAccount = [ordered]@{}
$selected.PSObject.Properties | ForEach-Object {
    $testAccount[$_.Name] = $_.Value
}
$testAccount["groups"] = $selectedGroups

# Para pruebas cortas, evitar pausas por bloques
$testAccount["batch_size"] = $null
$testAccount["batch_delay_minutes"] = $null

if (-not $NoDebugArtifacts) {
    $testAccount["debug_on_failure"] = $true
}

$testConfig = [ordered]@{
    accounts = @($testAccount)
}

# Guardar config temporal
$testConfig | ConvertTo-Json -Depth 20 | Set-Content -Path $TempConfigPath -Encoding UTF8
Write-Host "Config temporal generado: $TempConfigPath"
Write-Host "Total grupos a probar: $($selectedGroups.Count)"

# Ejecutar script principal con config temporal
$argsList = @(
    "-u",
    (Join-Path $ScriptDir "post_to_groups_selenium.py"),
    "--config", $TempConfigPath,
    "--delay", "$Delay"
)

if ($Headless) {
    $argsList += "--headless"
}
if (-not $NoDebugArtifacts) {
    $argsList += "--debug-on-failure"
}

Write-Host "\nLanzando prueba..." -ForegroundColor Green
$pythonOutput = & $PythonExe @argsList 2>&1
$pythonOutput | Out-File -FilePath $FullLogPath -Append -Encoding utf8
$pythonOutput
$exitCode = $LASTEXITCODE

Write-Host "\nFinalizado con codigo: $exitCode"
$endTs = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $FullLogPath -Value "[$endTs] Finalizado con codigo: $exitCode"
if ($exitCode -ne 0) {
    exit $exitCode
}
