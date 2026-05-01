<#
.SYNOPSIS
    Ejecuta una prueba solo en los grupos que fallaron recientemente.

.DESCRIPTION
    Lee los fallos de la ultima ejecucion normal, genera un config temporal
    con solo esos grupos fallidos y lanza post_to_groups_selenium.py con
    --debug-on-failure.

    Soporta:
    - ejecuciones de una sola cuenta
    - ejecuciones paralelas consolidadas en task_log.txt
    - varias cuentas activas en config.json
#>

[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$ConfigPath = "config.json",
    [string]$PythonExe = "C:\Users\ArielPlayit\AppData\Local\Programs\Python\Python312\python.exe",
    [int]$Delay = 15,
    [switch]$Headless,
    [switch]$NoDebugArtifacts,
    [switch]$DetectOnly,
    [string]$LogPath = "task_log_failed_groups_test.txt",
    [string]$TaskLogPath = "task_log.txt",
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$GroupIds
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$FullConfigPath = Join-Path $ScriptDir $ConfigPath
$FullLogPath = Join-Path $ScriptDir $LogPath
$FullTaskLogPath = Join-Path $ScriptDir $TaskLogPath
$TempLogDir = Join-Path ([System.IO.Path]::GetTempPath()) "facebook-upload-automatization"
$TempConfigPath = Join-Path $TempLogDir "config.failed-groups.test.json"

function Normalize-GroupId {
    param([object]$Value)

    if ($null -eq $Value) {
        return ""
    }
    return ([string]$Value).Trim()
}

function Add-UniqueString {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$Value
    )

    $normalized = Normalize-GroupId $Value
    if ($normalized -and -not $List.Contains($normalized)) {
        $List.Add($normalized)
    }
}

function New-RunBlock {
    param(
        [string]$Source,
        [string]$AccountName,
        [int]$TotalGroups,
        [int]$StartIndex
    )

    [PSCustomObject]@{
        Source = $Source
        AccountName = $AccountName
        TotalGroups = $TotalGroups
        StartIndex = $StartIndex
        Failures = New-Object System.Collections.Generic.List[string]
    }
}

function Get-RunBlocksFromLines {
    param(
        [string[]]$Lines,
        [string]$Source
    )

    $blocks = New-Object System.Collections.Generic.List[object]
    $current = $null
    $currentGroup = ""

    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $line = [string]$Lines[$i]

        if ($line -match 'Iniciando \[(?<account>.+?)\] - (?<total>\d+) grupo\(s\)') {
            if ($null -ne $current) {
                $blocks.Add($current)
            }

            $current = New-RunBlock `
                -Source $Source `
                -AccountName $Matches.account.Trim() `
                -TotalGroups ([int]$Matches.total) `
                -StartIndex $i
            $currentGroup = ""
            continue
        }

        if ($null -eq $current) {
            continue
        }

        $total = [string]$current.TotalGroups
        $processingRegex = '^\s*(?:\[[^\]]+\]\s*)?\[(?<pos>\d+)/' + $total + '\]\s+Procesando grupo:\s+(?<group>.+?)\s*$'
        $failedRegex = '^\s*(?:\[[^\]]+\]\s*)?[^\[]*\[(?<pos>\d+)/' + $total + '\].*fallida'

        if ($line -match $processingRegex) {
            $currentGroup = Normalize-GroupId $Matches.group
            continue
        }

        if ($line -match $failedRegex) {
            if ($currentGroup) {
                Add-UniqueString -List $current.Failures -Value $currentGroup
            }
            continue
        }
    }

    if ($null -ne $current) {
        $blocks.Add($current)
    }

    return $blocks.ToArray()
}

function Get-LastParallelMarkerIndex {
    param([string[]]$Lines)

    for ($i = $Lines.Count - 1; $i -ge 0; $i--) {
        if ([string]$Lines[$i] -match 'Iniciando modo paralelo:') {
            return $i
        }
    }
    return -1
}

function Get-BlocksFromTempLogs {
    $tempBlocks = New-Object System.Collections.Generic.List[object]
    $tempFiles = @(Get-ChildItem -Path $TempLogDir -Filter "__tmp_account*.out.log" -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -gt 0 } |
        Sort-Object Name)

    foreach ($tempFile in $tempFiles) {
        $lines = @(Get-Content -Path $tempFile.FullName -ErrorAction SilentlyContinue)
        $blocks = @(Get-RunBlocksFromLines -Lines $lines -Source $tempFile.Name)

        if ($blocks.Count -gt 0) {
            # Cada temp log corresponde a una cuenta; usar el ultimo bloque del archivo.
            $tempBlocks.Add($blocks[-1])
        }
    }

    return $tempBlocks.ToArray()
}

function Get-NewestTempLogWriteTime {
    $tempFiles = @(Get-ChildItem -Path $TempLogDir -Filter "__tmp_account*.out.log" -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -gt 0 })

    if ($tempFiles.Count -eq 0) {
        return $null
    }

    return ($tempFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
}

function Get-BlocksFromTaskLog {
    param([string]$TaskLogFile)

    if (-not (Test-Path $TaskLogFile)) {
        return @()
    }

    $lines = @(Get-Content -Path $TaskLogFile)
    if (-not $lines -or $lines.Count -eq 0) {
        return @()
    }

    $blocks = @(Get-RunBlocksFromLines -Lines $lines -Source (Split-Path -Leaf $TaskLogFile))
    if ($blocks.Count -eq 0) {
        return @()
    }

    $lastParallelMarker = Get-LastParallelMarkerIndex -Lines $lines
    if ($lastParallelMarker -ge 0) {
        $latestParallelBlocks = @($blocks | Where-Object { $_.StartIndex -gt $lastParallelMarker })
        if ($latestParallelBlocks.Count -gt 0) {
            return $latestParallelBlocks
        }

        # Hubo una ejecucion paralela nueva, pero no se consolidaron sus bloques.
        # No volver a fallos viejos; permitir fallback a temporales.
        if ($blocks[-1].StartIndex -lt $lastParallelMarker) {
            return @()
        }
    }

    # Fallback para ejecuciones no paralelas: usar el ultimo bloque con detalle.
    return @($blocks[-1])
}

function Get-FailedGroupsFromLastRun {
    param([string]$TaskLogFile)

    $taskLogBlocks = @(Get-BlocksFromTaskLog -TaskLogFile $TaskLogFile)
    $taskLogFailures = @($taskLogBlocks | Where-Object { $_.Failures.Count -gt 0 })
    if ($taskLogFailures.Count -gt 0) {
        return $taskLogFailures
    }

    # Fallback transitorio: si el runner paralelo murio antes de mezclar stdout,
    # rescatar los fallos desde los archivos temporales de esa misma ejecucion.
    $tempBlocks = @(Get-BlocksFromTempLogs)
    $newestTempLogWriteTime = Get-NewestTempLogWriteTime
    $taskLogWriteTime = $null
    if (Test-Path $TaskLogFile) {
        $taskLogWriteTime = (Get-Item -Path $TaskLogFile).LastWriteTime
    }

    if (
        $tempBlocks.Count -gt 0 -and
        (
            $null -eq $taskLogWriteTime -or
            $null -eq $newestTempLogWriteTime -or
            $newestTempLogWriteTime -ge $taskLogWriteTime.AddMinutes(-10)
        )
    ) {
        return @($tempBlocks | Where-Object { $_.Failures.Count -gt 0 })
    }

    return @()
}

function Get-ConfigAccounts {
    param([object]$Config)

    if ($null -ne $Config.accounts) {
        return @($Config.accounts)
    }
    return @($Config)
}

function Get-GroupIdsFromAccount {
    param([object]$Account)

    $ids = New-Object System.Collections.Generic.List[string]

    foreach ($group in @($Account.groups)) {
        Add-UniqueString -List $ids -Value $group.id
    }

    return $ids.ToArray()
}

function New-TestAccountForFailedGroups {
    param(
        [object]$Account,
        [string[]]$TargetGroupIds
    )

    $targetLookup = @{}
    foreach ($targetGroupId in @($TargetGroupIds)) {
        $normalized = Normalize-GroupId $targetGroupId
        if ($normalized) {
            $targetLookup[$normalized] = $true
        }
    }

    $selectedGroupsById = [ordered]@{}

    foreach ($group in @($Account.groups)) {
        $groupId = Normalize-GroupId $group.id
        if ($groupId -and $targetLookup.ContainsKey($groupId)) {
            $selectedGroupsById[$groupId] = $group
        }
    }

    if ($selectedGroupsById.Count -eq 0) {
        return $null
    }

    $testAccount = [ordered]@{}
    $Account.PSObject.Properties | ForEach-Object {
        $testAccount[$_.Name] = $_.Value
    }

    $testAccount["groups"] = @($selectedGroupsById.Values)
    $testAccount["batch_size"] = $null
    $testAccount["batch_delay_minutes"] = $null

    if (-not $NoDebugArtifacts) {
        $testAccount["debug_on_failure"] = $true
    }

    return [PSCustomObject]@{
        Account = $testAccount
        GroupIds = @($selectedGroupsById.Keys)
    }
}

if (-not (Test-Path $FullConfigPath)) {
    throw "No se encontro el config: $FullConfigPath"
}

if (-not $DetectOnly -and -not (Test-Path $PythonExe)) {
    throw "No se encontro Python en: $PythonExe"
}

$raw = Get-Content -Path $FullConfigPath -Raw -Encoding UTF8
$config = $raw | ConvertFrom-Json
$accounts = @(Get-ConfigAccounts -Config $config)

if ($accounts.Count -eq 0) {
    throw "El config no contiene cuentas para ejecutar."
}

$activeAccounts = @($accounts | Where-Object { -not $_.suspended })
if ($activeAccounts.Count -eq 0) {
    throw "No hay cuentas activas (suspended=false)."
}

$autoDetected = $false
$failureBlocks = @()
$manualGroupIds = @()

if (-not $GroupIds -or $GroupIds.Count -eq 0) {
    $autoDetected = $true
    $failureBlocks = @(Get-FailedGroupsFromLastRun -TaskLogFile $FullTaskLogPath)
    if ($failureBlocks.Count -eq 0) {
        throw "No se pudieron detectar grupos fallidos desde $FullTaskLogPath ni desde __tmp_account*.out.log. Pasa -GroupIds manualmente."
    }
}
else {
    $manualGroupIds = @(
        $GroupIds |
            ForEach-Object { ([string]$_).Split(",") } |
            ForEach-Object { Normalize-GroupId $_ } |
            Where-Object { $_ } |
            Select-Object -Unique
    )
    if ($manualGroupIds.Count -eq 0) {
        throw "No se recibieron GroupIds validos."
    }
}

$testAccounts = New-Object System.Collections.Generic.List[object]
$retryTargets = New-Object System.Collections.Generic.List[object]
$missingMessages = New-Object System.Collections.Generic.List[string]

if ($autoDetected) {
    foreach ($block in $failureBlocks) {
        $matchingAccounts = @($activeAccounts | Where-Object { ([string]$_.name).Trim().ToLowerInvariant() -eq $block.AccountName.Trim().ToLowerInvariant() })
        if ($matchingAccounts.Count -eq 0) {
            $matchingAccounts = @($activeAccounts | Where-Object {
                $accountIds = @(Get-GroupIdsFromAccount -Account $_)
                @($block.Failures | Where-Object { $accountIds -contains $_ }).Count -gt 0
            })
        }

        foreach ($account in $matchingAccounts) {
            $testAccountInfo = New-TestAccountForFailedGroups -Account $account -TargetGroupIds @($block.Failures)
            if ($null -eq $testAccountInfo) {
                $missingMessages.Add("[$($block.AccountName)] Ningun fallo detectado existe en la cuenta '$($account.name)'.")
                continue
            }

            $testAccounts.Add($testAccountInfo.Account)
            $retryTargets.Add([PSCustomObject]@{
                AccountName = $account.name
                GroupIds = $testAccountInfo.GroupIds
            })
        }
    }
}
else {
    $matchedGlobalIds = New-Object System.Collections.Generic.List[string]

    foreach ($account in $activeAccounts) {
        $testAccountInfo = New-TestAccountForFailedGroups -Account $account -TargetGroupIds $manualGroupIds
        if ($null -eq $testAccountInfo) {
            continue
        }

        $testAccounts.Add($testAccountInfo.Account)
        $retryTargets.Add([PSCustomObject]@{
            AccountName = $account.name
            GroupIds = $testAccountInfo.GroupIds
        })

        foreach ($matchedId in @($testAccountInfo.GroupIds)) {
            Add-UniqueString -List $matchedGlobalIds -Value $matchedId
        }
    }

    foreach ($manualGroupId in $manualGroupIds) {
        if (-not $matchedGlobalIds.Contains($manualGroupId)) {
            $missingMessages.Add("GroupId no encontrado en ninguna cuenta activa: $manualGroupId")
        }
    }
}

if ($testAccounts.Count -eq 0) {
    throw "No se encontro ningun grupo objetivo en las cuentas activas."
}

Write-Host "=== Test de grupos fallidos ===" -ForegroundColor Cyan
Write-Host "Config base: $FullConfigPath"
Write-Host "Log normal: $FullTaskLogPath"
Write-Host "Log de prueba: $FullLogPath"

foreach ($target in $retryTargets) {
    Write-Host ("Cuenta objetivo: {0} ({1} grupo(s)): {2}" -f $target.AccountName, $target.GroupIds.Count, ($target.GroupIds -join ", "))
}

foreach ($message in $missingMessages) {
    Write-Host "Aviso: $message" -ForegroundColor Yellow
}

if ($DetectOnly) {
    Write-Host "DetectOnly activado: no se genera config temporal y no se ejecuta Python." -ForegroundColor Yellow
    exit 0
}

if (-not (Test-Path $TempLogDir)) {
    New-Item -Path $TempLogDir -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $FullLogPath -Value "[$timestamp] Inicio test grupos fallidos"
Add-Content -Path $FullLogPath -Value "[$timestamp] Config base: $FullConfigPath"
foreach ($target in $retryTargets) {
    Add-Content -Path $FullLogPath -Value "[$timestamp] [$($target.AccountName)] GroupIds: $($target.GroupIds -join ', ')"
}

$testConfig = [ordered]@{
    accounts = @($testAccounts)
}

$testConfig | ConvertTo-Json -Depth 30 | Set-Content -Path $TempConfigPath -Encoding UTF8
Write-Host "Config temporal generado: $TempConfigPath"
Write-Host "Total cuentas a probar: $($testAccounts.Count)"
Write-Host "Total grupos a probar: $((@($retryTargets | ForEach-Object { $_.GroupIds.Count }) | Measure-Object -Sum).Sum)"

$argsList = @(
    "-u",
    (Join-Path $ScriptDir "post_to_groups_selenium.py"),
    "--config", $TempConfigPath,
    "--delay", "$Delay",
    "--all-active"
)

if ($Headless) {
    $argsList += "--headless"
}
if (-not $NoDebugArtifacts) {
    $argsList += "--debug-on-failure"
}

Write-Host "`nLanzando prueba..." -ForegroundColor Green
$pythonOutput = & $PythonExe @argsList 2>&1
$pythonOutput | Out-File -FilePath $FullLogPath -Append -Encoding utf8
$pythonOutput
$exitCode = $LASTEXITCODE

Write-Host "`nFinalizado con codigo: $exitCode"
$endTs = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $FullLogPath -Value "[$endTs] Finalizado con codigo: $exitCode"
if ($exitCode -ne 0) {
    exit $exitCode
}
