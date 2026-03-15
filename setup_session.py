"""
Script de configuración inicial - Inicia sesión manualmente una vez
para que las ejecuciones automáticas posteriores no necesiten login.

Uso:
    python setup_session.py                    # Cuenta principal (edge_profile)
    python setup_session.py --profile edge_profile2   # Segunda cuenta

Este script:
1. Abre Edge con un perfil dedicado para la automatización
2. Te lleva a Facebook para que inicies sesión manualmente (incluyendo 2FA)
3. Guarda la sesión en el perfil para uso futuro
"""

import os
import sys
import time
import argparse

from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options

try:
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    USE_WEBDRIVER_MANAGER = True
except ImportError:
    USE_WEBDRIVER_MANAGER = False


def main():
    parser = argparse.ArgumentParser(description="Configurar sesión de Facebook en perfil de Edge")
    parser.add_argument(
        "--profile", "-p",
        default="edge_profile",
        help="Nombre de la carpeta del perfil (default: edge_profile). Ejemplo: edge_profile2"
    )
    args = parser.parse_args()

    # Carpeta donde se guardará el perfil de Edge con la sesión
    PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.profile)

    print("=" * 60)
    print("  CONFIGURACIÓN INICIAL DE SESIÓN DE FACEBOOK")
    print("=" * 60)
    print()
    print(f"Se creará/usará un perfil de Edge en:")
    print(f"  {PROFILE_DIR}")
    print()
    print("INSTRUCCIONES:")
    print("1. Se abrirá una ventana de Microsoft Edge")
    print("2. Inicia sesión en Facebook manualmente")
    print("3. Aprueba la verificación en tu teléfono si te lo pide")
    print("4. Una vez que veas tu feed de Facebook, cierra el navegador")
    print()
    input("Presiona ENTER para continuar...")

    # Crear directorio del perfil si no existe
    os.makedirs(PROFILE_DIR, exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--lang=es-ES")
    options.add_argument("--window-size=1280,900")

    print("Abriendo Microsoft Edge...")

    try:
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        driver_path = EdgeChromiumDriverManager().install()
        service = EdgeService(executable_path=driver_path)
        driver = webdriver.Edge(service=service, options=options)
    except Exception:
        try:
            driver = webdriver.Edge(options=options)
        except Exception as e:
            print(f"Error iniciando Edge: {e}")
            print("\nSolucion: Asegurate de tener Microsoft Edge actualizado.")
            sys.exit(1)

    # Ocultar que es automatizado
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    # Navegar a Facebook
    driver.get("https://www.facebook.com/")

    print()
    print("=" * 60)
    print("  Edge está abierto. Inicia sesión en Facebook.")
    print("  Cuando termines, CIERRA el navegador manualmente.")
    print("=" * 60)

    # Esperar a que el usuario cierre el navegador
    try:
        while True:
            try:
                _ = driver.current_url
                time.sleep(2)
            except:
                break
    except KeyboardInterrupt:
        pass

    profile_path_json = PROFILE_DIR.replace(chr(92), "/")
    print()
    print("Navegador cerrado.")
    print()
    print("=" * 60)
    print("  ¡CONFIGURACIÓN COMPLETADA!")
    print("=" * 60)
    print()
    print("Actualiza tu config.json con esta ruta en la cuenta correspondiente:")
    print()
    print(f'  "edge_profile_path": "{profile_path_json}"')
    print()
    print("Luego ejecuta:")
    print("  python post_to_groups_selenium.py --config config.json")
    print()


if __name__ == "__main__":
    main()
