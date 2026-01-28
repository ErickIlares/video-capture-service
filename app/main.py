from fastapi import FastAPI
from pydantic import BaseModel
from playwright.sync_api import sync_playwright, TimeoutError
from PIL import Image
import base64
import io

app = FastAPI(title="Video Capture Service")


class CaptureRequest(BaseModel):
    url_video: str


def placeholder(text: str = "Contenido no disponible") -> str:
    img = Image.new("RGB", (1280, 720), (40, 40, 40))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def normalizar(img: Image.Image) -> str:
    img = img.convert("RGB").resize((1280, 720), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@app.get("/health")
def health():
    return {"status": "ok", "service": "video-capture"}


@app.post("/capturar")
def capturar(data: CaptureRequest):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )

            context = browser.new_context(
                viewport={"width": 390, "height": 844},  # 📱 mobile
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.0 Mobile/15E148 Safari/604.1"
                ),
            )

            page = context.new_page()
            page.goto(data.url_video, wait_until="domcontentloaded", timeout=60000)

            # Espera a que aparezca el contenedor visual del post
            try:
                page.wait_for_selector("article, video, img", timeout=10000)
            except TimeoutError:
                browser.close()
                return {
                    "status": "success",
                    "image_base64": placeholder("Post no visible"),
                }

            page.wait_for_timeout(3000)
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(2000)

            screenshot = page.screenshot(full_page=False)
            browser.close()

        image = Image.open(io.BytesIO(screenshot))
        return {
            "status": "success",
            "image_base64": normalizar(image),
        }

    except Exception:
        return {
            "status": "success",
            "image_base64": placeholder("Error de captura"),
        }
