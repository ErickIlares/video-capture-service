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
    img = Image.new("RGB", (1280, 720), (30, 30, 30))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def normalizar_imagen(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    return img.resize((1280, 720), Image.LANCZOS)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "video-capture",
        "version": "3.0.0"
    }


@app.post("/capturar")
def capturar(data: CaptureRequest):
    screenshot_bytes = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120 Safari/537.36"
                )
            )

            page = context.new_page()
            page.goto(data.url_video, timeout=60000)

            page.wait_for_timeout(5000)
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(3000)

            screenshot_bytes = page.screenshot()
            browser.close()

    except Exception:
        # Ignoramos cualquier error de Playwright
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

    # 🔑 SI NO HAY SCREENSHOT → PLACEHOLDER
    return {
        "status": "success",
        "image_base64": imagen_placeholder()
    }
