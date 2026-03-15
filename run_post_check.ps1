<#
.SYNOPSIS
    Ejecuta la tarea de publicacion solo si hay al menos 5 horas antes de la proxima
    ejecucion programada.

.DESCRIPTION
    Cuando la PC se enciende tarde y la tarea perdida se lanza por StartWhenAvailable,
    este script verifica que no se ejecute si la proxima tarea programada esta a menos
    de 5 horas de distancia (para evitar dos publicaciones muy seguidas).

    Ejemplo:
      - 9 AM perdida, PC enciende a las 12 PM  -> proxima tarea 8 PM (8h) -> EJECUTA
      - 9 AM perdida, PC enciende a las 5 PM   -> proxima tarea 8 PM (3h) -> OMITE
#>

$ScriptDir  = $PSScriptRoot
$LogFile    = Join-Path $ScriptDir "task_log.txt"
$RunBat     = Join-Path $ScriptDir "run_post.bat"
$MinHoras   = 5

# ─── Horarios programados diarios (24h) ───────────────────────────────────────
$horariosProgramados = @("09:00", "20:00")

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$ts] $msg"
}

# ─── Calcular la proxima ejecucion programada ──────────────────────────────────
$ahora           = Get-Date
$proximaEjecucion = $null

foreach ($hora in $horariosProgramados) {
    $partes    = $hora.Split(":")
    $candidato = (Get-Date).Date.AddHours([int]$partes[0]).AddMinutes([int]$partes[1])

    # Si ese horario ya paso hoy, usar manana
    if ($candidato -le $ahora) {
        $candidato = $candidato.AddDays(1)
    }

    if ($null -eq $proximaEjecucion -or $candidato -lt $proximaEjecucion) {
        $proximaEjecucion = $candidato
    }
}

$horasRestantes = ($proximaEjecucion - $ahora).TotalHours
$horasRedondeado = [math]::Round($horasRestantes, 1)

Write-Log "--- Verificacion de margen ---"
Write-Log "Hora actual:          $($ahora.ToString('HH:mm'))"
Write-Log "Proxima tarea:        $($proximaEjecucion.ToString('HH:mm dd/MM'))"
Write-Log "Horas restantes:      $horasRedondeado h (minimo requerido: $MinHoras h)"

# ─── Decision ─────────────────────────────────────────────────────────────────
if ($horasRestantes -ge $MinHoras) {
    Write-Log "DECISION: EJECUTAR (margen suficiente: $horasRedondeado h >= $MinHoras h)"
    Write-Log "Lanzando run_post.bat..."
    & cmd.exe /c "`"$RunBat`""
    Write-Log "run_post.bat finalizado con codigo: $LASTEXITCODE"
} else {
    Write-Log "DECISION: OMITIR (margen insuficiente: $horasRedondeado h < $MinHoras h, ejecutar en $($proximaEjecucion.ToString('HH:mm')))"
}
