"""
Facebook Group Poster - Selenium Version (Anti-Detection Enhanced)

ADVERTENCIA: Automatizar Facebook mediante Selenium puede violar sus términos de servicio.
Usar bajo tu propia responsabilidad. Riesgo de bloqueo de cuenta.

MEJORAS ANTI-DETECCIÓN v2.0:
- Comportamiento humano simulado (HumanBehavior class)
- User agents rotativos modernos
- CDP scripts avanzados para ocultar automatización
- Movimientos de ratón naturales
- Escritura con velocidad variable y errores de tipeo
- Scroll suave en pasos
"""

import argparse
import os
import sys
import time
import random
import string
import traceback
import threading
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Forzar UTF-8 en stdout/stderr para evitar errores en consola de Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from typing import Dict, Any, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException, NoSuchWindowException, InvalidSessionIdException
from selenium.webdriver import ActionChains
import pyperclip

from app_runner import run_single_account_from_config


# ═══════════════════════════════════════════════════════════════════════════════
# CLASE DE COMPORTAMIENTO HUMANO
# ═══════════════════════════════════════════════════════════════════════════════

class HumanBehavior:
    """Clase para simular comportamiento humano realista en automatización."""
    
    @staticmethod
    def random_delay(min_sec: float = 0.8, max_sec: float = 2.2):
        """
        Delay con distribución gaussiana (más realista que uniform).
        Los humanos tienden a tener tiempos de respuesta con distribución normal.
        """
        mean = (min_sec + max_sec) / 2
        std_dev = (max_sec - min_sec) / 4  # 95% de valores dentro del rango
        delay = random.gauss(mean, std_dev)
        # Asegurar que esté dentro de límites razonables
        delay = max(min_sec * 0.5, min(max_sec * 1.5, delay))
        time.sleep(delay)
    
    @staticmethod
    def human_scroll(driver, pixels: int = 300, smooth: bool = True):
        """
        Scroll en pasos pequeños con variación aleatoria.
        Simula el scroll natural de un humano.
        """
        if not smooth:
            driver.execute_script(f"window.scrollBy(0, {pixels})")
            return
        
        # Dividir en 8-15 pasos aleatorios
        num_steps = random.randint(8, 15)
        base_step = pixels / num_steps
        
        for _ in range(num_steps):
            # Variación de ±20% en cada paso
            variation = random.uniform(0.8, 1.2)
            step = int(base_step * variation)
            driver.execute_script(f"window.scrollBy(0, {step})")
            # Pequeña pausa variable entre cada paso
            time.sleep(random.uniform(0.02, 0.08))
    
    @staticmethod
    def move_mouse_to_element(driver, element):
        """
        Mover ratón con ActionChains simulando una curva natural.
        Los humanos no mueven el ratón en línea recta.
        """
        try:
            action = ActionChains(driver)
            
            # Obtener posición actual (aproximada) y destino
            location = element.location
            size = element.size
            
            # Centro del elemento como destino
            target_x = location['x'] + size['width'] // 2
            target_y = location['y'] + size['height'] // 2
            
            # Número de pasos para el movimiento (10-20)
            num_steps = random.randint(10, 20)
            
            # Movimiento inicial hacia el elemento
            action.move_to_element(element)
            
            # Añadir pequeños movimientos de jitter para parecer más humano
            for i in range(random.randint(2, 4)):
                jitter_x = random.randint(-2, 2)
                jitter_y = random.randint(-2, 2)
                action.move_by_offset(jitter_x, jitter_y)
                action.pause(random.uniform(0.01, 0.03))
            
            action.perform()
        except Exception as e:
            # Si falla el movimiento, al menos mover al elemento
            try:
                ActionChains(driver).move_to_element(element).perform()
            except:
                pass
    
    @staticmethod
    def inject_text_via_dom(driver, element, text: str):
        """
        Inyecta texto directamente en el DOM via JavaScript.
        Útil para caracteres especiales/emojis que msedgedriver no puede manejar.
        Simula un input de usuario limpio sin problemas de BMP.
        """
        try:
            # Limpiar elemento
            driver.execute_script("arguments[0].textContent = '';", element)
            time.sleep(0.2)
            
            # Inyectar texto
            driver.execute_script("arguments[0].textContent = arguments[1];", element, text)
            
            # Trigger input/change events para que Facebook detecte el cambio
            driver.execute_script("""
                const evt = new Event('input', { bubbles: true });
                arguments[0].dispatchEvent(evt);
                const evt2 = new Event('change', { bubbles: true });
                arguments[0].dispatchEvent(evt2);
            """, element)
            
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"      ⚠️ Fallo inyección DOM: {e}")
            return False

    @staticmethod
    def human_type(element, text: str, wpm: int = None):
        """
        Escribir con velocidad variable simulando tipeo humano.
        Incluye pausas en puntuación y probabilidad de errores de tipeo.
        """
        if wpm is None:
            wpm = random.randint(55, 90)
        
        # Calcular delay base por caracter (WPM -> segundos por caracter)
        # Promedio de 5 caracteres por palabra
        chars_per_minute = wpm * 5
        base_delay = 60.0 / chars_per_minute
        
        # Caracteres de puntuación que causan pausas más largas
        punctuation_chars = set('.,;:!?\n')
        # Caracteres que pueden causar errores de tipeo
        error_prone_chars = set('qwpzxbn')
        
        for i, char in enumerate(text):
            # Calcular delay para este caracter
            delay = base_delay * random.uniform(0.5, 1.5)
            
            # Pausas más largas en puntuación (2-4x más tiempo)
            if char in punctuation_chars:
                delay *= random.uniform(2.0, 4.0)
            
            # 2% de probabilidad de error de tipeo + corrección
            if random.random() < 0.02 and char.isalpha():
                # Escribir caracter erróneo
                wrong_char = random.choice(string.ascii_lowercase)
                element.send_keys(wrong_char)
                time.sleep(random.uniform(0.1, 0.3))
                # Borrar y escribir correcto
                element.send_keys(Keys.BACKSPACE)
                time.sleep(random.uniform(0.05, 0.15))
            
            # Escribir el caracter correcto
            if char == '\n':
                element.send_keys(Keys.SHIFT, Keys.RETURN)
            else:
                element.send_keys(char)
            
            time.sleep(delay)
    
    @staticmethod
    def random_mouse_movements(driver, count: int = 3):
        """
        Realizar movimientos aleatorios del ratón.
        Simula exploración visual de la página.
        """
        try:
            action = ActionChains(driver)
            
            for _ in range(count):
                # Movimiento aleatorio en pantalla
                offset_x = random.randint(-100, 100)
                offset_y = random.randint(-50, 50)
                
                action.move_by_offset(offset_x, offset_y)
                action.pause(random.uniform(0.1, 0.3))
            
            action.perform()
        except Exception:
            pass  # Ignorar errores de movimiento de ratón


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE UTILIDAD
# ═══════════════════════════════════════════════════════════════════════════════

def wait_for_page_load(driver, timeout: int = 30):
    """Espera a que la página cargue (acepta 'interactive' o 'complete' para estrategia eager)."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") in ("complete", "interactive")
        )
    except TimeoutException:
        pass  # Con estrategia eager la página puede tardar; continuar de todos modos


def navigate_with_retries(driver: webdriver.Edge, url: str, retries: int = 2) -> bool:
    """Navega a una URL con reintentos ante fallos intermitentes del renderer de Edge."""
    transient_markers = [
        "timed out receiving message from renderer",
        "target frame detached",
        "not connected to devtools",
        "disconnected",
        "invalid session id",
    ]

    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            wait_for_page_load(driver)
            return True
        except (TimeoutException, WebDriverException) as e:
            msg = str(e).lower()
            is_transient = any(marker in msg for marker in transient_markers)
            print(f"   ⚠️ Error navegando ({attempt}/{retries}): {e}")
            if attempt >= retries or not is_transient:
                return False
            HumanBehavior.random_delay(2, 4)

    return False


def is_session_lost_error(error: Exception) -> bool:
    """Detecta errores de Selenium que indican sesión/ventana cerrada."""
    if isinstance(error, (NoSuchWindowException, InvalidSessionIdException)):
        return True
    msg = str(error).lower()
    markers = [
        "no such window",
        "target window already closed",
        "invalid session id",
        "not connected to devtools",
        "session deleted",
        "target frame detached",
    ]
    return any(marker in msg for marker in markers)


def is_driver_alive(driver: webdriver.Edge) -> bool:
    """Valida de forma barata que el driver y la ventana principal siguen activos."""
    try:
        handles = driver.window_handles
        return bool(handles)
    except Exception:
        return False


def cleanup_edge_processes() -> None:
    """Cierra procesos de Edge/EdgeDriver que puedan bloquear el perfil persistente."""
    commands = [
        ["taskkill", "/IM", "msedgedriver.exe", "/F"],
        ["taskkill", "/IM", "msedge.exe", "/F"],
    ]
    for cmd in commands:
        try:
            subprocess.run(cmd, check=False, capture_output=True, text=True)
        except Exception:
            pass


def _sanitize_filename(text: str, fallback: str = "unknown") -> str:
    """Convierte un texto en nombre de archivo seguro para Windows."""
    if not text:
        return fallback
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", text)
    safe = re.sub(r"_+", "_", safe).strip("._-")
    return safe[:80] or fallback


def capture_failure_artifacts(driver: webdriver.Edge, group_id: str, reason: str, account_name: str) -> None:
    """Guarda screenshot, HTML y metadatos para facilitar debug de fallos."""
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        root = Path("debug_failures") / datetime.now().strftime("%Y%m%d")
        root.mkdir(parents=True, exist_ok=True)

        safe_group = _sanitize_filename(group_id, "group")
        safe_reason = _sanitize_filename(reason, "failure")
        base_name = f"{ts}_{safe_group}_{safe_reason}"

        screenshot_path = root / f"{base_name}.png"
        html_path = root / f"{base_name}.html"
        meta_path = root / f"{base_name}.txt"

        screenshot_ok = False
        try:
            screenshot_ok = driver.save_screenshot(str(screenshot_path))
        except Exception:
            screenshot_ok = False

        page_source_ok = False
        try:
            html_path.write_text(driver.page_source or "", encoding="utf-8", errors="replace")
            page_source_ok = True
        except Exception:
            page_source_ok = False

        current_url = ""
        title = ""
        ready_state = ""
        session_id = ""
        try:
            current_url = driver.current_url
        except Exception:
            current_url = "<unavailable>"
        try:
            title = driver.title
        except Exception:
            title = "<unavailable>"
        try:
            ready_state = driver.execute_script("return document.readyState")
        except Exception:
            ready_state = "<unavailable>"
        try:
            session_id = driver.session_id or "<none>"
        except Exception:
            session_id = "<unavailable>"

        meta_lines = [
            f"timestamp={datetime.now().isoformat()}",
            f"account={account_name}",
            f"group_id={group_id}",
            f"reason={reason}",
            f"current_url={current_url}",
            f"title={title}",
            f"document_ready_state={ready_state}",
            f"session_id={session_id}",
            f"screenshot_saved={screenshot_ok}",
            f"html_saved={page_source_ok}",
        ]
        meta_path.write_text("\n".join(meta_lines) + "\n", encoding="utf-8", errors="replace")

        print(f"   🧪 Debug guardado: {meta_path}")
    except Exception as debug_err:
        print(f"   ⚠️ No se pudo guardar evidencia de debug: {debug_err}")


def detect_group_posting_block_reason(driver: webdriver.Edge) -> tuple[str, str]:
    """Detecta causas frecuentes de bloqueo para publicar dentro de un grupo."""
    try:
        page_text = (driver.page_source or "").lower()
    except Exception:
        page_text = ""

    patterns = [
        (
            "no_permission",
            "No tienes permiso para publicar en este grupo.",
            [
                "no tienes permiso para publicar",
                "no puedes publicar",
                "no puedes crear publicaciones",
                "you can't post",
                "you cannot post",
                "only admins can post",
                "only admins and moderators can post",
                "solo los administradores pueden publicar",
                "solo admins",
                "posting is turned off",
                "publicaciones desactivadas",
            ],
        ),
        (
            "pending_approval",
            "Tus publicaciones en este grupo requieren aprobacion.",
            [
                "pendiente de aprobaci",
                "publicaci\u00f3n pendiente",
                "post is pending admin approval",
                "pending admin approval",
                "must be approved by an admin",
                "requiere aprobaci",
            ],
        ),
        (
            "join_required",
            "Debes unirte al grupo antes de publicar.",
            [
                "unirte al grupo",
                "debes unirte",
                "join group",
                "request to join",
                "requested to join",
                "hazte miembro",
            ],
        ),
        (
            "session_inactive",
            "La sesion parece inactiva o redirigida a login.",
            [
                "inicia sesi",
                "iniciar sesi",
                "log in to facebook",
                "create a new account",
            ],
        ),
    ]

    for code, message, needles in patterns:
        if any(needle in page_text for needle in needles):
            return code, message

    return "unknown", "No se pudo determinar la causa exacta del bloqueo."


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE DRIVER CON ANTI-DETECCIÓN
# ═══════════════════════════════════════════════════════════════════════════════

# User Agents rotativos modernos (Edge en Windows)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
]

# Script CDP avanzado para ocultar automatización
CDP_ANTI_DETECTION_SCRIPT = """
    // Ocultar webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    
    // Plugins realistas
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    
    // Idiomas
    Object.defineProperty(navigator, 'languages', {
        get: () => ['es-ES', 'es', 'en-US', 'en']
    });
    
    // Chrome runtime completo
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
    
    // Permisos realistas
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    
    // Dimensiones consistentes
    Object.defineProperty(window, 'outerWidth', {
        get: () => window.innerWidth
    });
    Object.defineProperty(window, 'outerHeight', {
        get: () => window.innerHeight
    });

    // WebGL fingerprinting protection
    const getParameterProxyHandler = {
        apply: function(target, thisArg, args) {
            const param = args[0];
            const result = target.apply(thisArg, args);
            // Devolver valores genéricos para algunos parámetros
            if (param === 37445) return 'Intel Inc.';
            if (param === 37446) return 'Intel Iris OpenGL Engine';
            return result;
        }
    };
"""


# ═══════════════════════════════════════════════════════════════════════════════
# RECURSOS DE SINCRONIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

# Lock para el portapapeles (evita condiciones de carrera si en el futuro se
# reutiliza el script con concurrencia externa).
_clipboard_lock = threading.Lock()


def create_driver(headless: bool = False, profile_path: str = None) -> webdriver.Edge:
    """Crea instancia del navegador Microsoft Edge con anti-detección mejorada."""
    print("🌐 Inicializando navegador Edge con anti-detección...")
    
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")
    
    # Usar SIEMPRE el perfil real para conservar cookies y sesión entre ejecuciones.
    # Nota: si el perfil está abierto en otra instancia de Edge, puede fallar el arranque.
    if profile_path:
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument("--profile-directory=Default")
        print(f"   ✓ Usando perfil persistente: {profile_path}")
    
    # ═══ OPCIONES ANTI-DETECCIÓN ═══
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=es-ES")
    options.add_argument("--window-size=1920,1080")
    
    # Opciones para parecer un navegador normal
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    
    # Opciones adicionales para compatibilidad con Task Scheduler
    options.add_argument("--remote-debugging-port=0")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-software-rasterizer")

    # Estrategia eager: no espera que carguen todas las imágenes/scripts,
    # solo hasta que el DOM esté interactivo (evita timeouts del renderer)
    options.page_load_strategy = 'eager'
    
    # User agent rotativo (seleccionar uno aleatorio)
    selected_ua = random.choice(USER_AGENTS)
    options.add_argument(f"user-agent={selected_ua}")
    print(f"   🔄 User-Agent: ...{selected_ua[-30:]}")
    
    # Opciones experimentales anti-automatización
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Preferencias para comportamiento más humano
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.media_stream": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.managed_default_content_settings.images": 1,
    }
    options.add_experimental_option("prefs", prefs)
    
    # Selenium Manager suele arrancar más rápido/estable en ejecuciones repetidas.
    try:
        service = EdgeService()
        driver = webdriver.Edge(service=service, options=options)
        print(f"   ✓ Usando EdgeDriver via selenium-manager")
    except Exception:
        driver = webdriver.Edge(options=options)
        print(f"   ✓ Usando EdgeDriver del sistema")
    
    # ═══ SCRIPTS CDP ANTI-DETECCIÓN ═══
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": CDP_ANTI_DETECTION_SCRIPT
        })
        print("   ✓ Scripts CDP anti-detección inyectados")
    except Exception as e:
        print(f"   ⚠️ No se pudieron inyectar scripts CDP: {e}")
        # Fallback al método básico
        try:
            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en']});
                window.chrome = {runtime: {}};
            """)
            print("   ✓ Scripts básicos inyectados (fallback)")
        except:
            pass
    
    # Timeout de carga de página: máximo 60 segundos
    driver.set_page_load_timeout(60)

    print("   ✓ Navegador inicializado correctamente")

    return driver


def login_facebook(driver: webdriver.Edge, email: str, password: str) -> bool:
    """Inicia sesión en Facebook con comportamiento humano. Retorna True si tiene éxito."""
    print("🌐 Navegando a Facebook...")
    if not navigate_with_retries(driver, "https://www.facebook.com/", retries=2):
        print("✗ No se pudo abrir Facebook por inestabilidad del navegador.")
        return False
    HumanBehavior.random_delay(2, 4)
    
    # Movimientos iniciales aleatorios del ratón
    print("👀 Simulando exploración inicial...")
    HumanBehavior.random_mouse_movements(driver, 3)
    
    # Verificar si ya está logueado
    if is_logged_in(driver):
        print("✓ Ya hay sesión iniciada.")
        return True
    
    # Detectar checkpoint de verificación
    if "checkpoint" in driver.current_url:
        print("⚠️  Verificación de seguridad requerida. Completa manualmente.")
        input("Presiona Enter después de completar la verificación...")
        return is_logged_in(driver)
    
    try:
        # Aceptar cookies si aparece el diálogo
        try:
            print("🔍 Buscando diálogo de cookies...")
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@data-cookiebanner='accept_button']"))
            )
            HumanBehavior.move_mouse_to_element(driver, cookie_btn)
            HumanBehavior.random_delay(0.5, 1)
            cookie_btn.click()
            print("✓ Cookies aceptadas")
            HumanBehavior.random_delay()
        except TimeoutException:
            pass
        
        # Ingresar email con comportamiento humano
        print("⌨️  Ingresando email...")
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        HumanBehavior.move_mouse_to_element(driver, email_field)
        HumanBehavior.random_delay(0.3, 0.8)
        email_field.click()
        email_field.clear()
        HumanBehavior.human_type(email_field, email, wpm=random.randint(50, 70))
        
        HumanBehavior.random_delay(0.5, 1.2)
        
        # Ingresar password con comportamiento humano
        print("⌨️  Ingresando contraseña...")
        pass_field = driver.find_element(By.ID, "pass")
        HumanBehavior.move_mouse_to_element(driver, pass_field)
        HumanBehavior.random_delay(0.3, 0.8)
        pass_field.click()
        pass_field.clear()
        HumanBehavior.human_type(pass_field, password, wpm=random.randint(45, 65))
        
        HumanBehavior.random_delay(0.8, 1.5)
        
        # Click en login con comportamiento humano
        print("🔍 Buscando botón de login...")
        login_btn = driver.find_element(By.NAME, "login")
        HumanBehavior.move_mouse_to_element(driver, login_btn)
        HumanBehavior.random_delay(0.5, 1.2)
        login_btn.click()
        
        print("⏳ Esperando respuesta del servidor...")
        HumanBehavior.random_delay(3, 5)
        wait_for_page_load(driver)
        
        # Detectar checkpoint después del login
        if "checkpoint" in driver.current_url:
            print("⚠️  Verificación de seguridad requerida. Completa manualmente.")
            input("Presiona Enter después de completar la verificación...")
            return is_logged_in(driver)
        
        # Verificar login exitoso
        if is_logged_in(driver):
            print("✓ Login exitoso.")
            return True
        else:
            print("✗ Login fallido. Verifica credenciales o si hay verificación adicional.")
            return False
            
    except Exception as e:
        print(f"✗ Error durante login: {e}")
        return False


def is_logged_in(driver: webdriver.Edge) -> bool:
    """Verifica si hay sesión activa en Facebook."""
    try:
        # Buscar elementos que solo aparecen cuando está logueado
        driver.find_element(By.XPATH, "//div[@aria-label='Tu perfil' or @aria-label='Your profile' or @aria-label='Cuenta' or @aria-label='Account']")
        return True
    except NoSuchElementException:
        pass
    
    # Alternativa: verificar URL
    current_url = driver.current_url
    if "login" in current_url or "checkpoint" in current_url:
        return False
    
    # Buscar el campo de crear publicación como indicador
    try:
        driver.find_element(By.XPATH, "//span[contains(text(), '¿Qué estás pensando')]")
        return True
    except NoSuchElementException:
        pass
    
    return "facebook.com" in current_url and "login" not in current_url


def keep_session_alive_during_pause(driver: webdriver.Edge, total_minutes: int) -> bool:
    """
    Mantiene la sesión activa durante pausas largas entre bloques.
    Hace pings cada 30-60 segundos a Facebook para evitar que se cierre la sesión.
    
    Args:
        driver: WebDriver de Selenium
        total_minutes: Minutos totales a esperar
    
    Returns:
        bool: True si la sesión se mantuvo activa, False si se perdió
    """
    try:
        start_time = time.time()
        total_seconds = total_minutes * 60
        last_ping = 0
        
        # Mostrar cuenta regresiva cada minuto
        for remaining_minutes in range(total_minutes, 0, -1):
            print(f"   ⏲️  {remaining_minutes} minuto(s) restante(s)...")
            
            # Hacer ping a Facebook cada 30-60 segundos dentro del minuto
            for _ in range(2):
                elapsed = time.time() - start_time
                if elapsed >= total_seconds:
                    break
                    
                HumanBehavior.random_delay(30, 30)  # Esperar 30 segundos
                
                # Hacer un ping a Facebook sin perder la sesión
                try:
                    driver.execute_script("fetch('https://www.facebook.com').catch(e => {})")
                    last_ping = time.time()
                except Exception:
                    pass
        
        # Verificar que la sesión sigue siendo válida
        print("   🔄 Verificando que la sesión sigue activa...")
        try:
            driver.get("https://www.facebook.com/")
            wait_for_page_load(driver)
            HumanBehavior.random_delay(2, 3)
            
            if is_logged_in(driver):
                print("   ✓ Sesión mantenida activa")
                return True
            else:
                print("   ⚠️ Sesión perdida, intentando reconectar...")
                # Esperar a que el usuario verifique si es necesario
                HumanBehavior.random_delay(5, 10)
                return False
        except Exception as e:
            print(f"   ✗ Error verificando sesión: {e}")
            return False
            
    except Exception as e:
        print(f"   ✗ Error en keep_session_alive: {e}")
        return False


def post_to_group(
    driver: webdriver.Edge,
    group_id: str,
    message: str,
    images: List[str] = None,
    debug_on_failure: bool = False,
    account_name: str = "Cuenta principal",
) -> bool:
    """Publica en un grupo de Facebook con comportamiento humano mejorado."""
    group_url = f"https://www.facebook.com/groups/{group_id}"
    print(f"\n🌐 Navegando al grupo: {group_url}")

    try:
        driver.get(group_url)
    except Exception as e:
        print(f"✗ Timeout cargando el grupo {group_id}, saltando: {e}")
        if debug_on_failure:
            capture_failure_artifacts(driver, group_id, "navigation_failed", account_name)
        return False

    print("⏳ Esperando a que cargue la página...")
    wait_for_page_load(driver)
    HumanBehavior.random_delay(3, 5)

    # ═══ SIMULACIÓN DE EXPLORACIÓN HUMANA ═══
    print("👀 Simulando exploración del grupo...")
    HumanBehavior.human_scroll(driver, random.randint(200, 400))
    HumanBehavior.random_delay(1, 2)
    HumanBehavior.random_mouse_movements(driver, 3)
    HumanBehavior.human_scroll(driver, random.randint(-150, -50))
    HumanBehavior.random_delay(1, 2)
    

    
    try:
        # Buscar el botón/área para crear publicación con más opciones
        create_post_selectors = [
            "//div[@role='button' and contains(@aria-label, 'Crear')]",
            "//span[contains(text(), 'Escribe algo')]",
            "//span[contains(text(), 'Write something')]",
            "//div[contains(@aria-label, 'Crear publicación')]",
            "//div[contains(@aria-label, 'Create a post')]",
            "//span[contains(text(), 'Escribe una publicación')]",
            "//span[contains(text(), '¿Qué estás pensando')]",
        ]
        
        post_box = None
        selected_create_selector = None
        print("🔍 Buscando el área para crear publicación...")
        for i, selector in enumerate(create_post_selectors):
            try:
                print(f"   Intentando selector {i+1}/{len(create_post_selectors)}...")
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                candidates = driver.find_elements(By.XPATH, selector)
                for candidate in candidates:
                    if not candidate.is_displayed() or not candidate.is_enabled():
                        continue

                    # Evitar botones dentro de publicaciones existentes (comentarios/reacciones).
                    inside_article = driver.execute_script(
                        "return !!arguments[0].closest('div[role=\"article\"]');",
                        candidate,
                    )
                    if inside_article:
                        continue

                    post_box = candidate
                    selected_create_selector = selector
                    print(f"   ✓ Encontrado con selector: {selector}")
                    break

                if post_box:
                    break
            except TimeoutException:
                continue
        
        if not post_box:
            block_code, block_message = detect_group_posting_block_reason(driver)
            print(f"✗ No se encontró el área de publicación en el grupo {group_id}")
            print(f"   ⚠️ Motivo detectado: {block_message}")
            if block_code == "unknown":
                print("   Puede que no tengas permisos, requiera aprobación o la sesión no esté activa.")
            if debug_on_failure:
                capture_failure_artifacts(driver, group_id, f"post_box_not_found_{block_code}", account_name)
            return False
        
        # ═══ CLICK CON COMPORTAMIENTO HUMANO + RETRY ANTI-STALE ═══
        clicked_post_box = False
        for attempt in range(1, 4):
            try:
                # Reubicar el elemento en reintentos para evitar referencias obsoletas.
                if attempt > 1 and selected_create_selector:
                    post_box = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, selected_create_selector))
                    )

                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", post_box)
                HumanBehavior.random_delay(1, 2)
                HumanBehavior.move_mouse_to_element(driver, post_box)
                HumanBehavior.random_delay(0.5, 1.2)
                post_box.click()
                print("✓ Click en área de publicación")
                clicked_post_box = True
                break
            except StaleElementReferenceException:
                print(f"   ⚠️ Elemento stale al abrir publicación (intento {attempt}/3)")
                HumanBehavior.random_delay(0.8, 1.5)

        if not clicked_post_box:
            print("✗ No se pudo hacer click en el área de publicación tras varios intentos")
            if debug_on_failure:
                capture_failure_artifacts(driver, group_id, "post_box_click_failed", account_name)
            return False

        HumanBehavior.random_delay(1.2, 2)
        
        # Simular más comportamiento humano después del click
        driver.execute_script("window.scrollBy(0, 50)")
        HumanBehavior.random_delay(1, 2)
        
        # Esperar a que aparezca el modal/diálogo de crear publicación
        print("⏳ Esperando modal de publicación...")
        modal = None
        try:
            modal = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
            )
            print("✓ Modal de publicación detectado")
        except TimeoutException:
            print("⚠️ No se detectó modal, continuando...")
        

        
        # Esperar a que aparezca el editor de publicación dentro del modal
        editor_selectors = [
            "//div[@role='dialog']//div[@role='textbox' and @contenteditable='true']",
            "//div[@role='dialog']//div[@contenteditable='true' and @role='textbox']",
            "//div[@role='dialog']//div[@contenteditable='true']",
        ]
        
        editor = None
        print("🔍 Buscando el editor de texto...")
        for i, selector in enumerate(editor_selectors):
            try:
                print(f"   Intentando selector {i+1}/{len(editor_selectors)}...")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )

                candidates = driver.find_elements(By.XPATH, selector)
                for candidate in candidates:
                    if not candidate.is_displayed() or not candidate.is_enabled():
                        continue

                    aria_label = (candidate.get_attribute("aria-label") or "").lower()
                    placeholder = (candidate.get_attribute("data-placeholder") or "").lower()
                    combined_text = f"{aria_label} {placeholder}"

                    # Excluir cajas de comentario/respuesta explícitas.
                    if any(token in combined_text for token in ["coment", "comment", "reply", "responde"]):
                        continue

                    # Confirmar que el editor pertenece al modal que contiene el botón Publicar/Post.
                    has_publish_button = driver.execute_script(
                        """
                        const dialog = arguments[0].closest('div[role="dialog"]');
                        if (!dialog) return false;
                        return !!dialog.querySelector('div[role="button"][aria-label="Publicar"], div[role="button"][aria-label="Post"]');
                        """,
                        candidate,
                    )
                    if not has_publish_button:
                        continue

                    editor = candidate
                    print(f"   ✓ Editor encontrado")
                    break

                if editor:
                    break
            except TimeoutException:
                continue
        
        if not editor:
            print("✗ No se encontró el editor de texto")
            if debug_on_failure:
                capture_failure_artifacts(driver, group_id, "editor_not_found", account_name)
            return False
        
        # ═══ ESCRIBIR MENSAJE CON COMPORTAMIENTO HUMANO ═══
        print(f"⌨️  Escribiendo mensaje ({len(message)} caracteres)...")
        
        # Hacer click en el editor con movimiento de ratón
        try:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", editor)
            HumanBehavior.random_delay(1, 2)
            HumanBehavior.move_mouse_to_element(driver, editor)
            HumanBehavior.random_delay(0.5, 1)
            driver.execute_script("arguments[0].click();", editor)
            HumanBehavior.random_delay(1, 2)
        except:
            driver.execute_script("arguments[0].click();", editor)
            HumanBehavior.random_delay(1, 2)
        
        # ═══ MÉTODO HÍBRIDO: PORTAPAPELES + FALLBACK A TIPEO HUMANO ═══
        try:
            print("   📋 Intentando método de portapapeles...")
            with _clipboard_lock:
                pyperclip.copy(message)
                HumanBehavior.random_delay(0.5, 1)

                action = ActionChains(driver)
                action.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()

                HumanBehavior.random_delay(1.2, 2)

            # Verificar que se pegó correctamente
            text_content = driver.execute_script("return arguments[0].textContent || arguments[0].innerText;", editor)
            
            if len(text_content) < len(message) * 0.8:
                print("   ⚠️ Texto incompleto, reintentando via DOM...")
                success = HumanBehavior.inject_text_via_dom(driver, editor, message)
                if not success:
                    print("      ⚠️ DOM falló, intentando escritura manual...")
                    try:
                        HumanBehavior.human_type(editor, message, wpm=random.randint(45, 65))
                    except Exception as fallback_err:
                        print(f"      ⚠️ Escritura manual también falló: {fallback_err}")
                        ascii_message = message.encode('ascii', 'ignore').decode('ascii') or "[Mensaje con caracteres especiales]"
                        try:
                            editor.clear()
                            editor.send_keys(ascii_message)
                        except Exception:
                            pass
            else:
                print(f"   ✓ Texto pegado ({len(text_content)} caracteres)")
            
        except Exception as e:
            print(f"   ⚠️ Error portapapeles: {e}")
            print("   ⌨️  Escribiendo via DOM (caracteres especiales)...")
            # Usar inyección DOM para caracteres especiales (emojis, acentos, etc)
            # que msedgedriver no puede manejar con send_keys()
            success = HumanBehavior.inject_text_via_dom(driver, editor, message)
            if not success:
                # Fallback final: intentar human_type (puede fallar con emojis)
                try:
                    HumanBehavior.human_type(editor, message, wpm=random.randint(45, 65))
                except Exception as fallback_err:
                    print(f"      ⚠️ Escritura manual también falló: {fallback_err}")
                    # Última opción: escribir apenas con ASCII
                    ascii_message = message.encode('ascii', 'ignore').decode('ascii') or "[Mensaje con caracteres especiales]"
                    try:
                        editor.clear()
                        editor.send_keys(ascii_message)
                    except:
                        pass
        
        HumanBehavior.random_delay(1.2, 2)
        
        # ═══ SUBIR IMÁGENES CON VERIFICACIÓN DE PREVIEW ═══
        if images:
            print(f"📷 Subiendo {len(images)} imagen(es)...")
            for idx, img_path in enumerate(images, 1):
                if os.path.exists(img_path):
                    try:
                        print(f"   🔍 Buscando input de archivo para imagen {idx}...")
                        
                        # Esperar a que el input file esté disponible
                        file_input = None
                        try:
                            file_input = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//input[@type='file']"))
                            )
                        except TimeoutException:
                            try:
                                file_input = driver.find_element(By.XPATH, "//input[@type='file']")
                            except:
                                pass
                        
                        if not file_input:
                            print(f"   ✗ No se encontró input de archivo para imagen {idx}")
                            continue
                        
                        # Convertir a ruta absoluta de Windows
                        abs_path = os.path.abspath(img_path)
                        print(f"   📤 Enviando imagen {idx}: {abs_path}")
                        
                        # Enviar la ruta al input
                        file_input.send_keys(abs_path)
                        
                        print(f"   ⏳ Esperando procesamiento de imagen {idx}...")
                        HumanBehavior.random_delay(5, 8)
                        
                        # Verificar que apareció el preview de la imagen
                        try:
                            WebDriverWait(driver, 8).until(
                                EC.presence_of_element_located((By.XPATH, 
                                    "//div[@role='dialog']//img[contains(@src, 'scontent') or contains(@src, 'blob:')]"
                                ))
                            )
                            print(f"   ✓ Imagen {idx} cargada correctamente")
                        except TimeoutException:
                            print(f"   ⚠️ No se detectó preview de imagen {idx}")
                            
                    except Exception as e:
                        print(f"   ✗ Error subiendo imagen {idx}: {e}")
                        if is_session_lost_error(e):
                            print("   ✗ Sesión/ventana del navegador perdida durante la subida de imágenes")
                            return False
                        traceback.print_exc()
                else:
                    print(f"   ✗ Imagen no encontrada: {img_path}")
        
        HumanBehavior.random_delay(2, 3)
        

        
        # ═══ BUSCAR Y HACER CLICK EN BOTÓN PUBLICAR ═══
        publish_selectors = [
            "//div[@role='dialog']//div[@aria-label='Publicar' and @role='button']",
            "//div[@role='dialog']//div[@aria-label='Post' and @role='button']",
            "//div[@role='dialog']//span[text()='Publicar']/ancestor::div[@role='button']",
            "//div[@role='dialog']//span[text()='Post']/ancestor::div[@role='button']",
        ]
        
        publish_btn = None
        selected_publish_selector = None
        print("🔍 Buscando botón de publicar...")
        for i, selector in enumerate(publish_selectors):
            try:
                print(f"   Intentando selector {i+1}/{len(publish_selectors)}...")
                publish_btn = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                selected_publish_selector = selector
                print(f"   ✓ Botón encontrado")
                break
            except TimeoutException:
                continue
        
        if not publish_btn:
            print("✗ No se encontró el botón de publicar")
            if debug_on_failure:
                capture_failure_artifacts(driver, group_id, "publish_button_not_found", account_name)
            return False
        
        # Click con comportamiento humano + retry anti-stale
        clicked_publish_btn = False
        for attempt in range(1, 4):
            try:
                if attempt > 1:
                    publish_btn = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, selected_publish_selector))
                    )
                HumanBehavior.move_mouse_to_element(driver, publish_btn)
                HumanBehavior.random_delay(0.5, 1)
                publish_btn.click()
                print("✓ Click en botón Publicar")
                clicked_publish_btn = True
                break
            except StaleElementReferenceException:
                print(f"   ⚠️ Botón Publicar stale (intento {attempt}/3)")
                HumanBehavior.random_delay(0.8, 1.5)

        if not clicked_publish_btn:
            print("✗ No se pudo hacer click en el botón Publicar tras varios intentos")
            if debug_on_failure:
                capture_failure_artifacts(driver, group_id, "publish_click_failed", account_name)
            return False

        print("⏳ Esperando confirmación de publicación...")
        HumanBehavior.random_delay(5, 7)
        
        # Verificar que el modal se cerró (solo informativo, no determina éxito)
        try:
            WebDriverWait(driver, 20).until_not(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
            )
            print("✓ Modal cerrado - Publicación confirmada")
        except TimeoutException:
            print("⚠️ El modal no se cerró en 20s - continuando (publicación probablemente exitosa)")
        
        # Esperar un poco más para que Facebook procese
        HumanBehavior.random_delay(2, 3)
        
        print(f"✓✓✓ Publicación enviada al grupo {group_id}")
        return True
        
    except Exception as e:
        print(f"✗ Error publicando en grupo {group_id}: {e}")
        if debug_on_failure:
            capture_failure_artifacts(driver, group_id, "exception_during_post", account_name)
        if is_session_lost_error(e):
            print("   ⚠️ Se detectó pérdida de sesión/ventana; se intentará recuperar en el siguiente grupo")
        return False


def run_account(account_cfg: Dict[str, Any], headless: bool, delay: int, cli_debug_on_failure: bool = False) -> tuple[int, int]:
    """Ejecuta la automatización completa para una sola cuenta."""
    account_name = account_cfg.get("name", "Cuenta principal")

    email = account_cfg.get("email")
    password = account_cfg.get("password")
    profile_path = account_cfg.get("edge_profile_path")
    default_message = account_cfg.get("default_message", "")
    default_images = [str(path) for path in account_cfg.get("default_images", [])]
    randomize_images_order = bool(account_cfg.get("randomize_images_order", False))
    groups = account_cfg.get("groups", [])
    debug_on_failure = bool(account_cfg.get("debug_on_failure", False) or cli_debug_on_failure)
    force_close_edge = bool(account_cfg.get("force_close_edge_before_start", True))

    if not groups:
        print("✗ No hay grupos configurados para esta cuenta")
        return (0, 0)

    if not profile_path and (not email or not password):
        print("✗ Debes proporcionar email/password o edge_profile_path en la configuración")
        return (0, 0)

    print(f"\n{'═'*60}")
    print(f"  Iniciando [{account_name}] - {len(groups)} grupo(s)")
    print(f"{'═'*60}\n")
    if debug_on_failure:
        print("🧪 Debug de fallos activado (capturas + HTML + metadatos)")

    driver = None
    try:
        if profile_path and force_close_edge:
            print("🧹 Cerrando procesos Edge previos para liberar el perfil...")
            cleanup_edge_processes()
            HumanBehavior.random_delay(1, 2)

        driver = create_driver(headless=headless, profile_path=profile_path)

        # Login si no hay perfil con sesión
        if not profile_path:
            if not login_facebook(driver, email, password):
                print("✗ No se pudo iniciar sesión. Abortando.")
                return (0, len(groups))
        else:
            print("🌐 Verificando sesión existente...")
            opened = False
            for startup_attempt in range(1, 3):
                if navigate_with_retries(driver, "https://www.facebook.com/", retries=2):
                    opened = True
                    break

                if startup_attempt < 2:
                    print("   🔄 Reiniciando navegador por error de renderer...")
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    HumanBehavior.random_delay(2, 4)
                    driver = create_driver(headless=headless, profile_path=profile_path)

            if not opened:
                if profile_path and force_close_edge:
                    print("   🧹 Reintentando con limpieza adicional de procesos Edge...")
                    cleanup_edge_processes()
                    HumanBehavior.random_delay(1, 2)
                    try:
                        if driver:
                            driver.quit()
                    except Exception:
                        pass
                    driver = create_driver(headless=headless, profile_path=profile_path)
                    if navigate_with_retries(driver, "https://www.facebook.com/", retries=2):
                        opened = True

            if not opened:
                print("✗ No se pudo abrir Facebook tras reintentos. Revisa Edge/driver y procesos abiertos.")
                return (0, len(groups))

            HumanBehavior.random_delay(2, 4)
            if not is_logged_in(driver):
                print("⚠️ El perfil de Edge no tiene sesión activa.")
                if email and password:
                    print("🔐 Intentando login automático con credenciales del config...")
                    if not login_facebook(driver, email, password):
                        print("✗ No se pudo iniciar sesión automáticamente.")
                        return (0, len(groups))
                    print("✓ Login automático exitoso; la sesión quedará guardada en el perfil.")
                else:
                    print("✗ No hay credenciales disponibles en config para recuperar sesión automáticamente.")
                    print("  Ejecuta setup_session.py o agrega email/password en la cuenta.")
                    return (0, len(groups))
            print("✓ Sesión activa detectada")

        def recover_driver_session() -> bool:
            """Recrea navegador y valida sesión para continuar el lote sin abortar toda la cuenta."""
            nonlocal driver
            print("   🔄 Recreando navegador por sesión inválida...")
            try:
                if driver:
                    driver.quit()
            except Exception:
                pass

            HumanBehavior.random_delay(2, 4)
            driver = create_driver(headless=headless, profile_path=profile_path)
            if not navigate_with_retries(driver, "https://www.facebook.com/", retries=2):
                if profile_path and force_close_edge:
                    print("   🧹 Limpieza de procesos y segundo intento de recuperación...")
                    cleanup_edge_processes()
                    HumanBehavior.random_delay(1, 2)
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    driver = create_driver(headless=headless, profile_path=profile_path)
                    if navigate_with_retries(driver, "https://www.facebook.com/", retries=2):
                        pass
                    else:
                        print("   ✗ No se pudo abrir Facebook tras recrear el navegador")
                        return False
                else:
                    print("   ✗ No se pudo abrir Facebook tras recrear el navegador")
                    return False

            HumanBehavior.random_delay(2, 4)
            if is_logged_in(driver):
                print("   ✓ Sesión recuperada con perfil persistente")
                return True

            if email and password:
                print("   🔐 Recuperando sesión con login automático...")
                if login_facebook(driver, email, password):
                    print("   ✓ Sesión recuperada por login")
                    return True

            print("   ✗ No se pudo recuperar la sesión automáticamente")
            return False

        # Publicar en cada grupo
        success_count = 0
        total_groups = len(groups)

        print(f"\n{'─'*60}")
        print(f"  INICIANDO PUBLICACIONES ({total_groups} grupos)")
        print(f"{'─'*60}\n")

        # Verificar si se debe usar batch posting (para cuentas con restricción)
        batch_size = account_cfg.get("batch_size")
        batch_delay_minutes = account_cfg.get("batch_delay_minutes")
        
        if batch_size and batch_delay_minutes:
            # Modo batch posting
            print(f"📦 MODO BATCH POSTING ACTIVADO")
            print(f"   - Bloques de {batch_size} grupos")
            print(f"   - Espera de {batch_delay_minutes} minutos entre bloques\n")
            
            # Dividir grupos en bloques
            batches = [groups[i:i + batch_size] for i in range(0, len(groups), batch_size)]
            total_batches = len(batches)
            
            for batch_num, batch in enumerate(batches, 1):
                print(f"\n{'='*60}")
                print(f"  BLOQUE {batch_num}/{total_batches} ({len(batch)} grupos)")
                print(f"{'='*60}\n")
                
                # Procesar grupos en este bloque
                for i, group in enumerate(batch, 1):
                    group_id = group.get("id")
                    if not group_id:
                        continue

                    if not is_driver_alive(driver):
                        if not recover_driver_session():
                            print("✗ Abortando cuenta: no se pudo recuperar el navegador")
                            return (success_count, total_groups)
                    
                    # Calcular posición global
                    global_pos = (batch_num - 1) * batch_size + i
                    
                    print(f"[{global_pos}/{total_groups}] Procesando grupo: {group_id}")
                    
                    message = group.get("message") or default_message
                    images = group.get("images")
                    if images is None:
                        images = list(default_images)
                    else:
                        images = list(images)
                    if randomize_images_order and images:
                        random.shuffle(images)
                    
                    if post_to_group(
                        driver,
                        group_id,
                        message,
                        images,
                        debug_on_failure=debug_on_failure,
                        account_name=account_name,
                    ):
                        success_count += 1
                        print(f"✓ [{global_pos}/{total_groups}] Publicación exitosa")
                    else:
                        print(f"✗ [{global_pos}/{total_groups}] Publicación fallida")
                    
                    # Espera entre grupos dentro del bloque (excepto después del último)
                    if global_pos < total_groups:
                        wait_time = random.randint(delay, delay + 10)
                        print(f"⏳ Esperando {wait_time}s antes del siguiente grupo...")
                        HumanBehavior.random_delay(delay, delay + 10)
                
                # Espera entre bloques (solo si no es el último bloque)
                if batch_num < total_batches:
                    # Delay aleatorio entre 5 y 10 minutos
                    actual_delay_minutes = random.randint(5, 10)
                    batch_wait_seconds = actual_delay_minutes * 60
                    print(f"\n⏳ PAUSA ENTRE BLOQUES: {actual_delay_minutes} minutos ({batch_wait_seconds}s)")
                    print(f"   Próximo bloque en {actual_delay_minutes} minutos...\n")
                    
                    # Mantener sesión activa durante la pausa
                    if not keep_session_alive_during_pause(driver, actual_delay_minutes):
                        print("   ⚠️ Sesión puede estar comprometida, intentando reconectar...")
                        try:
                            driver.get("https://www.facebook.com/")
                            wait_for_page_load(driver)
                            HumanBehavior.random_delay(3, 5)
                            if not is_logged_in(driver):
                                print("   ✗ No se pudo mantener la sesión activa")
                        except Exception as e:
                            print(f"   ✗ Error reconectando: {e}")
        else:
            # Modo normal (sin batch posting)
            for i, group in enumerate(groups, 1):
                group_id = group.get("id")
                if not group_id:
                    continue                                                    

                if not is_driver_alive(driver):
                    if not recover_driver_session():
                        print("✗ Abortando cuenta: no se pudo recuperar el navegador")
                        return (success_count, total_groups)

                print(f"[{i}/{total_groups}] Procesando grupo: {group_id}")

                message = group.get("message") or default_message
                images = group.get("images")
                if images is None:
                    images = list(default_images)
                else:
                    images = list(images)
                if randomize_images_order and images:
                    random.shuffle(images)

                if post_to_group(
                    driver,
                    group_id,
                    message,
                    images,
                    debug_on_failure=debug_on_failure,
                    account_name=account_name,
                ):
                    success_count += 1
                    print(f"✓ [{i}/{total_groups}] Publicación exitosa")
                else:
                    print(f"✗ [{i}/{total_groups}] Publicación fallida")

                if i < total_groups:
                    wait_time = random.randint(delay, delay + 10)
                    print(f"\n⏳ Esperando {wait_time} segundos antes de la siguiente publicación...")
                    HumanBehavior.random_delay(delay, delay + 10)

        print(f"\n{'═'*60}")
        print(f"  RESUMEN [{account_name}]: {success_count}/{total_groups} publicaciones exitosas")
        print(f"{'═'*60}")

        print("\n⏳ Navegador permanecerá abierto 8 segundos...")
        HumanBehavior.random_delay(8, 10)
        return (success_count, total_groups)

    except Exception as e:
        print(f"\n✗ Error general: {e}")
        traceback.print_exc()
        return (0, len(groups))
    finally:
        if driver:
            print("\n🌐 Cerrando navegador...")
            driver.quit()
            print("✓ Navegador cerrado")


def main():
    parser = argparse.ArgumentParser(
        description="Publicar en grupos de Facebook usando Selenium (automatización de navegador con Microsoft Edge)"
    )
    parser.add_argument("--config", "-c", required=True, help="Ruta al archivo JSON de configuración")
    parser.add_argument("--headless", action="store_true", help="Ejecutar sin ventana visible (puede fallar más)")
    parser.add_argument("--delay", "-d", type=int, default=15,
                       help="Segundos mínimos entre publicaciones (default: 15)")
    parser.add_argument("--debug-on-failure", action="store_true",
                       help="Guardar evidencia de fallos (screenshot, HTML y metadata) en debug_failures/")
    args = parser.parse_args()

    print("\n" + "═"*60)
    print("  FACEBOOK GROUP POSTER - Single Account v3.1")
    print("═"*60 + "\n")

    if not os.path.exists(args.config):
        print(f"✗ Archivo de configuración no encontrado: {args.config}")
        sys.exit(1)

    try:
        result = run_single_account_from_config(
            config_path=args.config,
            headless=args.headless,
            delay=args.delay,
            cli_debug_on_failure=args.debug_on_failure,
            run_account_callable=run_account,
        )
    except ValueError as config_error:
        print(f"✗ Configuración inválida: {config_error}")
        sys.exit(1)

    print(f"✓ Configuración cargada: {args.config}")
    print(f"✓ {result.configured_accounts} cuenta(s) configurada(s)")
    print(f"✓ {result.active_accounts} cuenta(s) activa(s)")

    if result.multiple_accounts_detected:
        print("⚠️ Se detectaron múltiples cuentas activas; en este modo se usará solo la primera.")

    print(f"\n{'═'*60}")
    print("  RESUMEN GLOBAL")
    print(f"{'═'*60}")
    print(f"  [{result.selected_account_name}]: {result.success_count}/{result.total_groups} publicaciones exitosas")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
