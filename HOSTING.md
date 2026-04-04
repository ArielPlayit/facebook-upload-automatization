# Hosting sin tener la PC encendida

## Resumen corto

Este proyecto usa Selenium + Edge con sesion de navegador persistente. Para este caso, la opcion mas estable es un VPS Windows 24/7 (por ejemplo Azure VM, AWS EC2 Windows o Contabo Windows VPS).

## Opcion recomendada: VPS Windows

1. Crear una VM Windows (2 vCPU, 4-8 GB RAM)
2. Instalar Edge y Python 3.11+
3. Clonar este repositorio
4. Instalar dependencias:
   - `pip install -r requirements.txt`
5. Ejecutar una vez la configuracion de sesion:
   - `python setup_session.py`
6. Subir/ajustar `config.json`
7. Crear tarea programada:
   - usar `create_scheduled_task.ps1` o `run_post.bat`
8. Dejar la VM encendida siempre

## Costos orientativos

- Basico: USD 15-40/mes segun proveedor y region
- Ventaja: no depende de tu PC local y mantiene sesion estable

## Otras opciones (menos recomendadas)

- GitHub Actions / CI: no ideal para este proyecto por sesion persistente, 2FA y entornos efimeros.
- Docker Linux headless: posible tecnicamente, pero mas fragil para Facebook y mas complejo de operar.
- Serverless (Azure Functions, Lambda): no recomendado para Selenium con navegador real y perfil persistente.

## Seguridad minima recomendada

- No guardar `config.json` en repositorios publicos.
- Usar usuario dedicado en la VM para automatizaciones.
- Restringir RDP por IP.
- Hacer snapshot de la VM despues de dejar todo estable.

## Observacion importante

Automatizar Facebook puede infringir sus terminos. Ejecutar en la nube no elimina ese riesgo; solo resuelve la disponibilidad 24/7.
