# Facebook Upload Automatization

Herramienta para automatizar publicaciones (texto + fotos) en grupos de Facebook usando **Selenium** con **Microsoft Edge**.

---

## ⚠️ ADVERTENCIA IMPORTANTE

**Este proyecto automatiza un navegador para interactuar con Facebook, lo cual puede violar sus términos de servicio.**

Riesgos:
- Bloqueo temporal o permanente de tu cuenta de Facebook
- Captchas frecuentes
- Facebook puede detectar comportamiento automatizado

**Usa bajo tu propia responsabilidad.**

---

## Contenido

| Archivo | Descripción |
|---------|-------------|
| `post_to_groups_selenium.py` | Script principal de publicación |
| `run_post.bat` | Batch para ejecutar desde Task Scheduler |
| `create_scheduled_task.ps1` | Crea tareas programadas (9AM y 8PM) |
| `setup_session.py` | Configura sesión inicial de Facebook |
| `install_edgedriver.py` | Instala EdgeDriver automáticamente |
| `config.example.json` | Ejemplo de configuración |
| `config.json` | Tu configuración (no subir a git) |
| `app_models.py` | Modelos tipados de configuración |
| `app_config.py` | Carga, parseo y validación de configuración |
| `app_runner.py` | Orquestación de ejecución de la aplicación |
| `HOSTING.md` | Guía para ejecutar 24/7 sin tu PC encendida |

---

## Instalación

```powershell
cd "C:\Users\ArielPlayit\Documents\Proyectos\facebook-upload-automatization"
pip install -r requirements.txt
python install_edgedriver.py
```

---

## Arquitectura (versión actual)

El proyecto ahora está separado en capas para facilitar mantenimiento:

- `post_to_groups_selenium.py`: infraestructura Selenium y lógica de interacción con Facebook
- `app_config.py`: lectura/validación de configuración (`config.json`)
- `app_models.py`: estructuras de datos de configuración
- `app_runner.py`: flujo de aplicación (selección de cuenta activa y ejecución)

Este cambio reduce acoplamiento, mejora testeabilidad y hace más sencillo extender funcionalidades sin romper la automatización principal.

---

## Configuración

1. Copia el archivo de ejemplo:

```powershell
Copy-Item config.example.json config.json
```

2. Edita `config.json` con tus datos:

```json
{
  "email": "tu_email@ejemplo.com",
  "password": "tu_contraseña",
  "edge_profile_path": "C:/Users/TuUsuario/.../edge_profile",
  "default_message": "Tu mensaje aquí",
  "default_images": [
    "C:/ruta/a/imagen1.jpg",
    "C:/ruta/a/imagen2.jpg"
  ],
  "randomize_images_order": true,
  "groups": [
    {
      "id": "ID_DEL_GRUPO"
    },
    {
      "id": "OTRO_ID",
      "message": "Mensaje específico (opcional)",
      "images": ["C:/ruta/a/imagen-especifica.jpg"]
    }
  ]
}
```

Notas rápidas:
- `default_message` y `default_images` viven una sola vez por cuenta.
- Cada grupo puede omitir `message/images` y hereda los valores por defecto.
- Si `randomize_images_order` es `true`, el orden de imágenes se mezcla en cada publicación.
- El script sigue validando que cada archivo exista antes de subirlo.

### ¿Cómo obtener el ID del grupo?

1. Ve al grupo en Facebook
2. La URL será algo como: `https://www.facebook.com/groups/123456789`
3. El número `123456789` es el ID del grupo

### Configurar sesión de Edge (recomendado)

Para evitar login cada vez, usa un perfil de Edge con sesión guardada:

```powershell
python setup_session.py
```

Esto abrirá Edge para que inicies sesión manualmente. La sesión se guardará en `edge_profile/`.

---

## Uso

### Ejecución manual:

```powershell
python post_to_groups_selenium.py --config config.json
```

### Con delay personalizado entre grupos (segundos):

```powershell
python post_to_groups_selenium.py --config config.json --delay 30
```

### Debug de fallos (capturas + HTML):

Puedes activar evidencia automática cuando una publicación falle:

```powershell
python post_to_groups_selenium.py --config config.json --debug-on-failure
```

También puedes dejarlo fijo por cuenta en `config.json`:

```json
{
  "accounts": [
    {
      "name": "Cuenta Principal",
      "debug_on_failure": true
    }
  ]
}
```

Cuando falle un grupo, se guardará evidencia en `debug_failures/AAAAmmdd/`:
- screenshot `.png`
- HTML completo `.html`
- metadata `.txt` (URL, título, reason, estado de sesión)

---

## Programar Ejecución Automática

### Opción 1: Usar el script PowerShell (recomendado)

Haz clic derecho en `create_scheduled_task.ps1` → **"Ejecutar con PowerShell"**

Se abrirá el prompt de UAC (escudito) y creará dos tareas:
- `FacebookAutoPost_9AM` - Se ejecuta a las 9:00 AM
- `FacebookAutoPost_8PM` - Se ejecuta a las 8:00 PM

### Opción 2: Ejecutar manualmente la tarea

```powershell
schtasks /Run /TN "FacebookAutoPost_9AM"
```

### Ver tareas programadas:

```powershell
Get-ScheduledTask -TaskName "FacebookAutoPost*"
```

### Eliminar tareas:

```powershell
Unregister-ScheduledTask -TaskName "FacebookAutoPost_9AM" -Confirm:$false
Unregister-ScheduledTask -TaskName "FacebookAutoPost_8PM" -Confirm:$false
```

---

## Ejecutar sin tu PC encendida

Revisa la guía completa en `HOSTING.md`.

Recomendación práctica para este tipo de proyecto:

- usar una **VM Windows 24/7** (Azure, AWS, Contabo, etc.)
- configurar sesión con `setup_session.py`
- programar con Task Scheduler

---

## 🛡️ Tips Anti-Detección

El script incluye medidas anti-detección:
- Comportamiento humano simulado (delays aleatorios, scroll suave)
- User agents rotativos
- Scripts CDP para ocultar automatización
- Movimientos de ratón naturales
- Escritura con velocidad variable

### Recomendaciones adicionales:

1. **No publiques en muchos grupos muy rápido** - el script ya incluye delays aleatorios
2. **Varía los mensajes** - usa mensajes diferentes para cada grupo
3. **No ejecutes 24/7** - programa solo 1-2 veces al día
4. **Mantén tu cuenta activa manualmente** - interactúa con Facebook normalmente

---

## ⚠️ Solución de Problemas

### Si las publicaciones se borran:

1. **Verifica las reglas del grupo** - algunos requieren aprobación del admin
2. **Prueba manualmente primero** - haz una publicación manual con el mismo contenido
3. **Revisa tu cuenta** - verifica si tienes restricciones activas

### Diagnóstico de grupos donde no aparece "Escribe algo":

El script ahora intenta detectar y reportar una causa específica cuando no encuentra
el área de publicación, por ejemplo:
- Sin permisos para publicar
- Publicación pendiente de aprobación
- Debes unirte al grupo
- Sesión inactiva/login

Si además usas `--debug-on-failure`, tendrás screenshot + HTML + metadata para confirmar el motivo.

### Si Edge no abre:

1. Cierra todas las ventanas de Edge abiertas
2. Verifica que `msedgedriver.exe` esté en la carpeta del proyecto
3. Ejecuta `python install_edgedriver.py` para reinstalar el driver

### Si la tarea programada no funciona:

1. Verifica que tengas sesión iniciada en Windows (requerido para que Edge abra)
2. Revisa el log en `task_log.txt`
3. Ejecuta manualmente para ver errores: `schtasks /Run /TN "FacebookAutoPost_9AM"`

---

## 📊 Frecuencia Recomendada

| Riesgo | Frecuencia | Recomendación |
|--------|-----------|---------------|
| 🔴 Alto | Cada 1-6h | Evitar |
| 🟡 Medio | Cada 12h | Solo para testing |
| 🟢 Bajo | Cada 24h | Recomendado |
| ✅ Muy bajo | Cada 2-3 días | Más seguro |

---

## Log de Ejecución

Las ejecuciones automáticas generan un log en `task_log.txt` con:
- Hora de inicio y fin
- Grupos procesados
- Errores encontrados

Con `--debug-on-failure` también se genera evidencia detallada en `debug_failures/`.

---

## Licencia

Uso personal. No me hago responsable del uso que le des a esta herramienta.
