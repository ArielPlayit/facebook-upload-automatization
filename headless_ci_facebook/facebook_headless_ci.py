from __future__ import annotations

import argparse
import base64
import json
import os
import random
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CREATE_POST_SELECTORS = [
    "//div[@role='button' and contains(@aria-label, 'Crear')]",
    "//div[@role='button' and contains(@aria-label, 'Create')]",
    "//span[contains(text(), 'Escribe algo')]/ancestor::div[@role='button'][1]",
    "//span[contains(text(), 'Write something')]/ancestor::div[@role='button'][1]",
    "//span[contains(text(), '¿Que estas pensando')]/ancestor::div[@role='button'][1]",
    "//span[contains(text(), \"What's on your mind\")]/ancestor::div[@role='button'][1]",
]

EDITOR_SELECTORS = [
    "//div[@role='dialog']//div[@role='textbox' and @contenteditable='true']",
    "//div[@role='dialog']//div[@contenteditable='true']",
]

PUBLISH_SELECTORS = [
    "//div[@role='dialog']//div[@aria-label='Publicar' and @role='button']",
    "//div[@role='dialog']//div[@aria-label='Post' and @role='button']",
    "//div[@role='dialog']//span[text()='Publicar']/ancestor::div[@role='button'][1]",
    "//div[@role='dialog']//span[text()='Post']/ancestor::div[@role='button'][1]",
]

DEBUG_ROOT = Path(__file__).resolve().parent / "debug_artifacts"


def random_delay(min_seconds: float, max_seconds: float) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def sanitize_name(value: str, fallback: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", value or "")
    safe = re.sub(r"_+", "_", safe).strip("._-")
    return safe[:80] or fallback


def load_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        parsed = json.load(handle)
    if not isinstance(parsed, dict):
        raise ValueError("El archivo de configuracion debe ser un objeto JSON.")
    return parsed


def select_account(raw_config: dict[str, Any]) -> dict[str, Any]:
    if "accounts" not in raw_config:
        return raw_config

    raw_accounts = raw_config.get("accounts", [])
    if not isinstance(raw_accounts, list):
        raise ValueError("El campo accounts debe ser una lista.")

    active_accounts = [
        account for account in raw_accounts if isinstance(account, dict) and not account.get("suspended", False)
    ]
    if not active_accounts:
        raise ValueError("No hay cuentas activas en la configuracion.")

    if len(active_accounts) > 1:
        print("[warn] Hay multiples cuentas activas. Se usara la primera para CI.")

    return active_accounts[0]


def normalize_groups(raw_groups: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_groups, list):
        raise ValueError("El campo groups debe ser una lista.")

    groups: list[dict[str, Any]] = []
    for item in raw_groups:
        if not isinstance(item, dict):
            continue
        group_id = str(item.get("id", "")).strip()
        if not group_id:
            continue
        groups.append(item)

    if not groups:
        raise ValueError("No hay grupos validos en groups.")
    return groups


def resolve_image_paths(image_paths: list[str], config_dir: Path) -> list[str]:
    resolved: list[str] = []
    script_dir = Path(__file__).resolve().parent
    for raw_path in image_paths:
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            from_config_dir = (config_dir / candidate).resolve()
            from_script_dir = (script_dir / candidate).resolve()
            if from_config_dir.exists():
                candidate = from_config_dir
            elif from_script_dir.exists():
                candidate = from_script_dir
            else:
                candidate = from_config_dir
        resolved.append(str(candidate))
    return resolved


def load_cookies_from_environment() -> list[dict[str, Any]]:
    raw_json = os.getenv("FB_COOKIES_JSON", "").strip()
    raw_b64 = os.getenv("FB_COOKIES_JSON_B64", "").strip()

    if raw_b64:
        try:
            raw_json = base64.b64decode(raw_b64).decode("utf-8")
        except Exception as err:
            raise ValueError(f"FB_COOKIES_JSON_B64 invalido: {err}") from err

    if not raw_json:
        return []

    parsed = json.loads(raw_json)
    if isinstance(parsed, dict) and isinstance(parsed.get("cookies"), list):
        parsed = parsed["cookies"]

    if not isinstance(parsed, list):
        raise ValueError("El JSON de cookies debe ser una lista o un objeto con la clave cookies.")

    normalized: list[dict[str, Any]] = []
    for cookie in parsed:
        if not isinstance(cookie, dict):
            continue

        name = cookie.get("name")
        value = cookie.get("value")
        if not name or value is None:
            continue

        item: dict[str, Any] = {
            "name": str(name),
            "value": str(value),
        }
        for key in ("domain", "path", "secure", "httpOnly", "sameSite"):
            if key in cookie:
                item[key] = cookie[key]

        expiry = cookie.get("expiry")
        if isinstance(expiry, (int, float)):
            item["expiry"] = int(expiry)

        normalized.append(item)

    return normalized


def create_driver(browser: str, headless: bool, locale: str) -> webdriver.Remote:
    if browser == "edge":
        options = EdgeOptions()
    else:
        options = ChromeOptions()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=" + locale)
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.page_load_strategy = "eager"

    if browser == "edge":
        driver = webdriver.Edge(options=options)
    else:
        driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(60)
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"},
        )
    except Exception:
        pass

    return driver


def wait_for_page_load(driver: webdriver.Remote, timeout: int = 30) -> None:
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
        )
    except TimeoutException:
        pass


def navigate_with_retries(driver: webdriver.Remote, url: str, retries: int = 2) -> bool:
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            wait_for_page_load(driver)
            return True
        except Exception as err:
            print(f"[warn] Error navegando a {url} ({attempt}/{retries}): {err}")
            if attempt < retries:
                random_delay(1.5, 3.5)
    return False


def is_logged_in(driver: webdriver.Remote) -> bool:
    current_url = ""
    try:
        current_url = driver.current_url.lower()
    except Exception:
        return False

    if "login" in current_url or "checkpoint" in current_url:
        return False

    selectors = [
        "//div[@aria-label='Tu perfil' or @aria-label='Your profile' or @aria-label='Account']",
        "//a[contains(@href, '/me/')]",
        "//span[contains(text(), 'Menu')]",
        "//span[contains(text(), 'Menú')]",
    ]

    for selector in selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            if elements:
                return True
        except Exception:
            continue

    return "facebook.com" in current_url and "login" not in current_url


def apply_cookies_and_restore_session(driver: webdriver.Remote, cookies: list[dict[str, Any]]) -> bool:
    if not cookies:
        return False

    print(f"[info] Intentando restaurar sesion con {len(cookies)} cookie(s)...")
    if not navigate_with_retries(driver, "https://www.facebook.com/", retries=2):
        return False

    applied = 0
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
            applied += 1
        except Exception:
            continue

    if applied == 0:
        print("[warn] No se pudo aplicar ninguna cookie.")
        return False

    try:
        driver.get("https://www.facebook.com/")
        wait_for_page_load(driver)
        random_delay(1.5, 2.5)
    except Exception:
        pass

    ok = is_logged_in(driver)
    if ok:
        print("[ok] Sesion restaurada con cookies.")
    else:
        print("[warn] Las cookies no restauraron una sesion valida.")
    return ok


def login_with_credentials(driver: webdriver.Remote, email: str, password: str) -> bool:
    print("[info] Intentando login con credenciales...")
    if not navigate_with_retries(driver, "https://www.facebook.com/login", retries=2):
        return False

    try:
        cookie_selectors = [
            "//button[@data-cookiebanner='accept_button']",
            "//button[contains(., 'Allow all cookies')]",
            "//button[contains(., 'Permitir todas las cookies')]",
            "//span[contains(., 'Allow all cookies')]/ancestor::button[1]",
            "//span[contains(., 'Permitir todas las cookies')]/ancestor::button[1]",
        ]
        for selector in cookie_selectors:
            try:
                cookie_btn = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                cookie_btn.click()
                random_delay(0.3, 0.8)
                break
            except Exception:
                continue

        email_field = None
        for by, selector in [
            (By.ID, "email"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[name='email']"),
            (By.CSS_SELECTOR, "input[type='text'][autocomplete='username']"),
        ]:
            try:
                email_field = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((by, selector))
                )
                break
            except TimeoutException:
                continue

        pass_field = None
        for by, selector in [
            (By.ID, "pass"),
            (By.NAME, "pass"),
            (By.CSS_SELECTOR, "input[name='pass']"),
            (By.CSS_SELECTOR, "input[type='password']"),
        ]:
            try:
                pass_field = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((by, selector))
                )
                break
            except TimeoutException:
                continue

        login_button = None
        for by, selector in [
            (By.NAME, "login"),
            (By.CSS_SELECTOR, "button[name='login']"),
            (By.XPATH, "//button[@name='login']"),
            (By.XPATH, "//div[@role='button' and (@aria-label='Iniciar sesión' or @aria-label='Log in')]")
        ]:
            try:
                login_button = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((by, selector))
                )
                break
            except TimeoutException:
                continue

        if not email_field or not pass_field or not login_button:
            print("[warn] No se encontro el formulario de login completo.")
            try:
                print(f"[warn] URL actual: {driver.current_url}")
            except Exception:
                pass
            capture_debug_artifacts(driver, "auth", "login_form_not_found")
            return False

        email_field.clear()
        email_field.send_keys(email)
        random_delay(0.2, 0.6)

        pass_field.clear()
        pass_field.send_keys(password)
        random_delay(0.2, 0.6)

        try:
            login_button.click()
        except Exception:
            driver.execute_script("arguments[0].click();", login_button)
        wait_for_page_load(driver)
        random_delay(2.0, 3.0)

        current_url = ""
        try:
            current_url = driver.current_url.lower()
        except Exception:
            current_url = ""

        if "checkpoint" in current_url:
            print("[warn] Facebook solicito checkpoint/2FA despues del login.")
            capture_debug_artifacts(driver, "auth", "checkpoint_after_login")
            return False

        if is_logged_in(driver):
            print("[ok] Login exitoso con credenciales.")
            return True

        print("[warn] Login no confirmado. Puede haber 2FA o checkpoint.")
        try:
            print(f"[warn] URL actual tras login: {driver.current_url}")
        except Exception:
            pass
        capture_debug_artifacts(driver, "auth", "login_not_confirmed")
        return False
    except Exception as err:
        print(f"[warn] Error durante login: {err}")
        try:
            print(f"[warn] URL en excepcion de login: {driver.current_url}")
        except Exception:
            pass
        capture_debug_artifacts(driver, "auth", "login_exception")
        return False


def capture_debug_artifacts(driver: webdriver.Remote, group_id: str, reason: str) -> None:
    try:
        date_folder = DEBUG_ROOT / time.strftime("%Y%m%d")
        date_folder.mkdir(parents=True, exist_ok=True)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        safe_group = sanitize_name(group_id, "group")
        safe_reason = sanitize_name(reason, "failure")
        base = f"{stamp}_{safe_group}_{safe_reason}"

        screenshot_path = date_folder / f"{base}.png"
        html_path = date_folder / f"{base}.html"
        meta_path = date_folder / f"{base}.txt"

        try:
            driver.save_screenshot(str(screenshot_path))
        except Exception:
            pass

        try:
            html_path.write_text(driver.page_source or "", encoding="utf-8", errors="replace")
        except Exception:
            pass

        meta_lines = [
            "timestamp=" + time.strftime("%Y-%m-%dT%H:%M:%S"),
            "group_id=" + group_id,
            "reason=" + reason,
        ]
        try:
            meta_lines.append("current_url=" + (driver.current_url or ""))
        except Exception:
            meta_lines.append("current_url=<unavailable>")

        meta_path.write_text("\n".join(meta_lines) + "\n", encoding="utf-8", errors="replace")
        print(f"[debug] Artifacts guardados en {date_folder}")
    except Exception as err:
        print(f"[warn] No se pudo guardar debug: {err}")


def click_with_fallback(driver: webdriver.Remote, element: Any) -> None:
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def find_create_post_box(driver: webdriver.Remote) -> tuple[Any | None, str | None]:
    for selector in CREATE_POST_SELECTORS:
        try:
            WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, selector)))
        except TimeoutException:
            continue

        candidates = driver.find_elements(By.XPATH, selector)
        for candidate in candidates:
            try:
                if not candidate.is_displayed() or not candidate.is_enabled():
                    continue

                inside_article = driver.execute_script(
                    "return !!arguments[0].closest('div[role=\"article\"]');",
                    candidate,
                )
                if inside_article:
                    continue

                return candidate, selector
            except Exception:
                continue

    return None, None


def find_editor(driver: webdriver.Remote) -> Any | None:
    for selector in EDITOR_SELECTORS:
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, selector)))
        except TimeoutException:
            continue

        candidates = driver.find_elements(By.XPATH, selector)
        for candidate in candidates:
            try:
                if not candidate.is_displayed() or not candidate.is_enabled():
                    continue

                aria_label = (candidate.get_attribute("aria-label") or "").lower()
                placeholder = (candidate.get_attribute("data-placeholder") or "").lower()
                combined = f"{aria_label} {placeholder}"
                if any(token in combined for token in ["comment", "coment", "reply", "respuesta"]):
                    continue

                has_publish_btn = driver.execute_script(
                    """
                    const dialog = arguments[0].closest('div[role="dialog"]');
                    if (!dialog) return false;
                    return !!dialog.querySelector(
                      'div[role="button"][aria-label="Publicar"], div[role="button"][aria-label="Post"]'
                    );
                    """,
                    candidate,
                )
                if not has_publish_btn:
                    continue

                return candidate
            except Exception:
                continue

    return None


def inject_text(driver: webdriver.Remote, editor: Any, message: str) -> None:
    driver.execute_script(
        """
        arguments[0].textContent = '';
        arguments[0].textContent = arguments[1];
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        arguments[0].dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: ' '}));
        """,
        editor,
        message,
    )


def upload_images(driver: webdriver.Remote, images: list[str]) -> None:
    if not images:
        return

    for index, image_path in enumerate(images, start=1):
        if not os.path.exists(image_path):
            print(f"[warn] Imagen no encontrada: {image_path}")
            continue

        try:
            file_input = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//input[@type='file']"))
            )
            file_input.send_keys(os.path.abspath(image_path))
            print(f"[ok] Imagen {index} enviada: {image_path}")
            random_delay(2.0, 4.0)
        except Exception as err:
            print(f"[warn] Fallo subiendo imagen {image_path}: {err}")


def find_publish_button(driver: webdriver.Remote) -> Any | None:
    for selector in PUBLISH_SELECTORS:
        try:
            button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, selector)))
            if button:
                return button
        except TimeoutException:
            continue
    return None


def post_to_group(
    driver: webdriver.Remote,
    group_id: str,
    message: str,
    images: list[str],
    debug_on_failure: bool,
) -> bool:
    url = f"https://www.facebook.com/groups/{group_id}"
    print(f"[info] Navegando a grupo {group_id}")

    if not navigate_with_retries(driver, url, retries=2):
        if debug_on_failure:
            capture_debug_artifacts(driver, group_id, "navigation_failed")
        return False

    random_delay(2.0, 3.5)

    create_box, _ = find_create_post_box(driver)
    if not create_box:
        print("[warn] No se encontro el area de crear publicacion.")
        if debug_on_failure:
            capture_debug_artifacts(driver, group_id, "create_box_not_found")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", create_box)
        random_delay(0.4, 1.0)
        click_with_fallback(driver, create_box)
        random_delay(1.0, 2.0)
    except Exception as err:
        print(f"[warn] No se pudo abrir el modal de publicacion: {err}")
        if debug_on_failure:
            capture_debug_artifacts(driver, group_id, "open_modal_failed")
        return False

    editor = find_editor(driver)
    if not editor:
        print("[warn] No se encontro el editor de texto.")
        if debug_on_failure:
            capture_debug_artifacts(driver, group_id, "editor_not_found")
        return False

    try:
        click_with_fallback(driver, editor)
        random_delay(0.2, 0.6)
        if message:
            inject_text(driver, editor, message)
        else:
            editor.send_keys(Keys.SPACE)
            editor.send_keys(Keys.BACKSPACE)
        random_delay(0.8, 1.6)
    except Exception as err:
        print(f"[warn] No se pudo escribir el mensaje: {err}")
        if debug_on_failure:
            capture_debug_artifacts(driver, group_id, "message_injection_failed")
        return False

    upload_images(driver, images)

    publish_button = find_publish_button(driver)
    if not publish_button:
        print("[warn] No se encontro el boton Publicar/Post.")
        if debug_on_failure:
            capture_debug_artifacts(driver, group_id, "publish_button_not_found")
        return False

    try:
        click_with_fallback(driver, publish_button)
        print("[ok] Boton Publicar activado.")
        random_delay(4.0, 6.0)
    except Exception as err:
        print(f"[warn] Fallo al publicar: {err}")
        if debug_on_failure:
            capture_debug_artifacts(driver, group_id, "publish_click_failed")
        return False

    try:
        WebDriverWait(driver, 15).until_not(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
    except TimeoutException:
        pass

    print(f"[ok] Grupo {group_id} procesado.")
    return True


def run(args: argparse.Namespace) -> tuple[int, int]:
    config_path = Path(args.config).resolve()
    config_dir = config_path.parent

    raw = load_json_file(config_path)
    account = select_account(raw)

    email = os.getenv("FB_EMAIL", str(account.get("email", "")).strip()).strip()
    password = os.getenv("FB_PASSWORD", str(account.get("password", "")).strip()).strip()
    locale = str(account.get("locale", "es-ES")).strip() or "es-ES"

    groups = normalize_groups(account.get("groups", []))

    default_message = str(account.get("default_message", ""))
    default_images = resolve_image_paths(
        [str(path) for path in account.get("default_images", []) if isinstance(path, str)],
        config_dir,
    )

    cookies = load_cookies_from_environment()

    print("=" * 60)
    print(" Facebook Headless CI Runner")
    print("=" * 60)
    print(f"Browser: {args.browser}")
    print(f"Headless: {args.headless}")
    print(f"Groups: {len(groups)}")

    driver = None
    success_count = 0

    try:
        driver = create_driver(browser=args.browser, headless=args.headless, locale=locale)

        authenticated = apply_cookies_and_restore_session(driver, cookies)
        if not authenticated and email and password:
            authenticated = login_with_credentials(driver, email, password)

        if not authenticated:
            raise RuntimeError(
                "No se pudo autenticar. Define FB_COOKIES_JSON_B64 o email/password en config."
            )

        total_groups = len(groups)
        for idx, group in enumerate(groups, start=1):
            group_id = str(group.get("id")).strip()
            message = str(group.get("message", default_message))

            group_images_raw = group.get("images")
            if isinstance(group_images_raw, list):
                images = resolve_image_paths(
                    [str(path) for path in group_images_raw if isinstance(path, str)],
                    config_dir,
                )
            else:
                images = list(default_images)

            print("-" * 60)
            print(f"[{idx}/{total_groups}] Grupo {group_id}")

            if post_to_group(
                driver=driver,
                group_id=group_id,
                message=message,
                images=images,
                debug_on_failure=args.debug_on_failure,
            ):
                success_count += 1
            else:
                print(f"[warn] Fallo en grupo {group_id}")

            if idx < total_groups:
                random_delay(args.delay, args.delay + 8)

        return success_count, total_groups
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Headless Facebook group posting for CI")
    parser.add_argument("--config", required=True, help="Ruta al JSON de configuracion")
    parser.add_argument("--browser", choices=["chrome", "edge"], default="chrome")
    parser.add_argument("--headless", action="store_true", help="Ejecuta sin ventana")
    parser.add_argument("--delay", type=int, default=20, help="Segundos minimos entre grupos")
    parser.add_argument("--debug-on-failure", action="store_true", help="Guarda screenshot y HTML en fallos")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Devuelve codigo de error si al menos un grupo falla",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not Path(args.config).exists():
        print(f"[error] Config no encontrado: {args.config}")
        sys.exit(1)

    try:
        success_count, total_groups = run(args)
    except Exception as err:
        print(f"[error] Ejecucion interrumpida: {err}")
        traceback.print_exc()
        sys.exit(1)

    print("=" * 60)
    print(f"Resultado: {success_count}/{total_groups} grupos exitosos")
    print("=" * 60)

    if args.strict and success_count < total_groups:
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
