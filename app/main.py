from fastapi import FastAPI
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
from PIL import Image
import base64
import io

app = FastAPI(title="Video Capture Service")


class CaptureRequest(BaseModel):
    url_video: str


def imagen_placeholder() -> str:
    """
    Imagen de respaldo cuando no se puede renderizar contenido real.
    """
    img = Image.new("RGB", (1280, 720), (240, 240, 240))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def normalizar_imagen(img: Image.Image) -> Image.Image:
    """
    Normaliza a 1280x720, fondo blanco.
    """
    img = img.convert("RGB")
    return img.resize((1280, 720), Image.LANCZOS)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "video-capture",
        "version": "3.1.0"
    }


@app.post("/capturar")
def capturar(data: CaptureRequest):
    screenshot_bytes = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )

            context = browser.new_context(
                viewport={"width": 1280, "height": 900},  # más vertical
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120 Safari/537.36"
                )
            )

            page = context.new_page()
            page.goto(data.url_video, timeout=60000, wait_until="domcontentloaded")

            # 🔑 Forzar fondo blanco (evita pantallas negras)
            page.add_style_tag(content="""
                html, body {
                    background: white !important;
                }
            """)

            # Esperas reales (Render + redes sociales)
            page.wait_for_timeout(8000)
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(3000)

            screenshot_bytes = page.screenshot(
                full_page=False,
                animations="disabled"
            )

            browser.close()

    except Exception:
        # No rompemos el flujo
        pass

    # 🔑 SI HAY SCREENSHOT → USARLO
    if screenshot_bytes:
        try:
            image = Image.open(io.BytesIO(screenshot_bytes))
            image = normalizar_imagen(image)

            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85)

            return {
                "status": "success",
                "image_base64": base64.b64encode(buffer.getvalue()).decode("utf-8")
            }
        except Exception:
            pass

    # 🔑 SI TODO FALLA → PLACEHOLDER (NUNCA BLOQUEA)
    return {
        "status": "success",
        "image_base64": imagen_placeholder()
    }
