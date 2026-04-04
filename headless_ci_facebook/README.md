# Headless CI Facebook Poster

Este subproyecto es independiente del flujo principal del repo.
No modifica tu script actual y esta pensado para pruebas y ejecucion headless en GitHub Actions.

## Estructura

- facebook_headless_ci.py: runner Selenium para CI
- config.example.json: ejemplo de configuracion
- config.local.example.json: plantilla minima para primer run (1 grupo)
- FIRST_RUN_CHECKLIST.md: checklist corta para ejecutar el primer run real
- requirements.txt: dependencias del subproyecto

## Primer run rapido (1 grupo)

1. Copia config.local.example.json a config.local.json.
2. Edita solo un id de grupo y un mensaje corto.
3. Convierte config.local.json a base64 y guarda el valor en FB_CONFIG_JSON_B64.
4. Ejecuta el workflow facebook-headless-ci desde Actions.

Comando PowerShell para base64:

```powershell
$json = Get-Content .\headless_ci_facebook\config.local.json -Raw
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
```

## Como ejecutar localmente

```powershell
pip install -r headless_ci_facebook/requirements.txt
python headless_ci_facebook/facebook_headless_ci.py --config headless_ci_facebook/config.json --headless --debug-on-failure --strict
```

## Configuracion recomendada para Actions

No subas config.json real al repo. Usa un secret en base64.

### 1) Crear el secret FB_CONFIG_JSON_B64

1. Copia config.example.json a un archivo local temporal.
2. Completa email/password o deja esas claves vacias si usaras cookies.
3. Convierte ese JSON a base64 en PowerShell:

```powershell
$json = Get-Content .\headless_ci_facebook\config.local.json -Raw
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
```

4. Guarda la salida en el secret del repo: FB_CONFIG_JSON_B64

Opcional: puedes dejar email/password vacios en el JSON y definirlos como secrets separados:

- FB_EMAIL
- FB_PASSWORD

### 2) Secret opcional para cookies (mejor estabilidad)

Si exportas cookies de Facebook en JSON, puedes pasarlas por secret:

```powershell
$cookies = Get-Content .\cookies.json -Raw
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($cookies))
```

Guarda ese valor como: FB_COOKIES_JSON_B64

## Ejecutar en GitHub Actions

1. Ve a Actions.
2. Elige workflow: facebook-headless-ci.
3. Run workflow.

## Notas importantes

- Facebook puede pedir checkpoint o 2FA y romper la ejecucion CI.
- Las IP de GitHub Actions pueden gatillar controles anti-bot.
- Si una publicacion falla, el script guarda artifacts en headless_ci_facebook/debug_artifacts.
