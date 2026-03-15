<#
.SYNOPSIS
    Crea tareas programadas para publicar en Facebook automaticamente.

.DESCRIPTION
    Configura dos tareas programadas que ejecutan el script a las 9:00 AM y 8:00 PM.
    - Si la PC estaba apagada cuando debio ejecutarse, se lanza al encender
    - Solo se ejecuta si han de pasar al menos 5 horas hasta la proxima tarea programada
      (evita ejecutar la tarea de las 9 AM si faltan menos de 5h para las 8 PM)
    - Requiere que el usuario tenga sesion iniciada (para que Edge pueda abrir)
    - Requiere ejecutar PowerShell como Administrador

.EXAMPLE
    .\create_scheduled_task.ps1
#>

param(
    [string] $CheckScriptPath = (Join-Path $PSScriptRoot "run_post_check.ps1"),
    [string] $TaskNamePrefix  = "FacebookAutoPost"
)

# Auto-elevacion: si no es admin, relanza el script con UAC (muestra el escudito)
$currentIsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $currentIsAdmin) {
    Write-Host "Solicitando permisos de Administrador..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

# Validar archivos
if (-not (Test-Path $CheckScriptPath)) {
    Write-Error "run_post_check.ps1 no encontrado: $CheckScriptPath"
    exit 1
}

Write-Host ""
Write-Host "=============================================================" -ForegroundColor Yellow
Write-Host "  ADVERTENCIA: Este script automatiza Facebook" -ForegroundColor Yellow
Write-Host "  Esto puede violar los terminos de servicio de Facebook" -ForegroundColor Yellow
Write-Host "  Usar bajo tu propia responsabilidad" -ForegroundColor Yellow
Write-Host "=============================================================" -ForegroundColor Yellow
Write-Host ""

# Eliminar tareas existentes si existen
$existingTasks = @(
    "${TaskNamePrefix}_9AM",
    "${TaskNamePrefix}_8PM",
    "${TaskNamePrefix}_1PM"
)

foreach ($taskName in $existingTasks) {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        Write-Host "[DELETE] Eliminando tarea existente: $taskName" -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
}

Write-Host ""
Write-Host "Creando tareas programadas..." -ForegroundColor Cyan

# Crear accion: ejecutar el script de verificacion via PowerShell
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$CheckScriptPath`""

# Configuracion de la tarea
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RunOnlyIfNetworkAvailable

# Principal: Interactive para que Edge pueda abrir ventanas
# Usar DOMAIN\USER evita ambiguedades cuando el script se ejecuta elevado.
$fullUserId = "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal `
    -UserId $fullUserId `
    -LogonType Interactive

function New-LocalDailyTrigger {
    param(
        [int] $Hour,
        [int] $Minute = 0
    )

    $t = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($Hour).AddMinutes($Minute))
    # Guardar StartBoundary sin offset de zona horaria mantiene la hora "de pared"
    # estable en cambios DST (9:00 sigue siendo 9:00 local).
    $t.StartBoundary = (Get-Date -Hour $Hour -Minute $Minute -Second 0).ToString("yyyy-MM-dd'T'HH:mm:ss")
    return $t
}

# === TAREA: 9:00 AM ===
$trigger9AM = New-LocalDailyTrigger -Hour 9 -Minute 0
$task9AM = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger9AM `
    -Settings $settings `
    -Principal $principal `
    -Description "Publica en grupos de Facebook a las 9:00 AM (con verificacion de margen de 5h)"

Register-ScheduledTask -TaskName "${TaskNamePrefix}_9AM" -InputObject $task9AM -Force | Out-Null
Write-Host "  [OK] Tarea creada: ${TaskNamePrefix}_9AM (9:00 AM)" -ForegroundColor Green

# === TAREA: 8:00 PM ===
$trigger8PM = New-LocalDailyTrigger -Hour 20 -Minute 0
$task8PM = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger8PM `
    -Settings $settings `
    -Principal $principal `
    -Description "Publica en grupos de Facebook a las 8:00 PM (con verificacion de margen de 5h)"

Register-ScheduledTask -TaskName "${TaskNamePrefix}_8PM" -InputObject $task8PM -Force | Out-Null
Write-Host "  [OK] Tarea creada: ${TaskNamePrefix}_8PM (8:00 PM)" -ForegroundColor Green

Write-Host ""
Write-Host "=============================================================" -ForegroundColor Green
Write-Host "  Tareas programadas creadas correctamente" -ForegroundColor Green
Write-Host "=============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "TAREAS CREADAS:" -ForegroundColor Cyan
Write-Host "  * FacebookAutoPost_9AM - Se ejecuta a las 9:00 AM" -ForegroundColor White
Write-Host "  * FacebookAutoPost_8PM - Se ejecuta a las 8:00 PM" -ForegroundColor White
Write-Host ""
Write-Host "LOGICA DE EJECUCION TARDIA (PC apagada):" -ForegroundColor Cyan
Write-Host "  * Si la PC enciende despues del horario, la tarea se lanza SOLO si" -ForegroundColor White
Write-Host "    la proxima tarea programada esta a mas de 5 horas de distancia." -ForegroundColor White
Write-Host "  * Ejemplo: PC enciende 12 PM (9AM perdida -> 8PM en 8h)  -> EJECUTA" -ForegroundColor Gray
Write-Host "  * Ejemplo: PC enciende  5 PM (9AM perdida -> 8PM en 3h)  -> OMITE" -ForegroundColor Gray
Write-Host ""
Write-Host "REQUISITOS:" -ForegroundColor Cyan
Write-Host "  * El usuario debe tener sesion iniciada (para que Edge pueda abrir)" -ForegroundColor White
Write-Host "  * Se ejecuta incluso con bateria (laptop)" -ForegroundColor White
Write-Host ""
Write-Host "COMANDOS UTILES:" -ForegroundColor Cyan
Write-Host "  Ver tareas:" -ForegroundColor White
Write-Host "    Get-ScheduledTask -TaskName FacebookAutoPost*" -ForegroundColor Gray
Write-Host ""
Write-Host "  Ejecutar tarea manualmente:" -ForegroundColor White
Write-Host "    Start-ScheduledTask -TaskName FacebookAutoPost_9AM" -ForegroundColor Gray
Write-Host ""
Write-Host "  Ver historial:" -ForegroundColor White
Write-Host "    Get-ScheduledTaskInfo -TaskName FacebookAutoPost_9AM" -ForegroundColor Gray
Write-Host ""
Write-Host "  Eliminar tareas:" -ForegroundColor White
Write-Host "    Unregister-ScheduledTask -TaskName FacebookAutoPost_9AM" -ForegroundColor Gray
Write-Host "    Unregister-ScheduledTask -TaskName FacebookAutoPost_8PM" -ForegroundColor Gray
Write-Host ""
Write-Host "LOG DE EJECUCION:" -ForegroundColor Cyan
Write-Host "  $PSScriptRoot\task_log.txt" -ForegroundColor Gray
Write-Host ""
