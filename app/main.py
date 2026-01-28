from fastapi import FastAPI
from pydantic import BaseModel
from playwright.sync_api import sync_playwright, TimeoutError
from PIL import Image
import base64
import io

app = FastAPI(title="Video Capture Service")


class CaptureRequest(BaseModel):
    url_video: str


def normalizar_imagen(img: Image.Image) -> Image.Image:
    target_width = 1280
    target_height = 720

    img_ratio = img.width / img.height
    target_ratio = target_width / target_height

    if img_ratio > target_ratio:
        new_width = target_width
        new_height = int(target_width / img_ratio)
    else:
        new_height = target_height
        new_width = int(target_height * img_ratio)

    img_resized = img.resize((new_width, new_height), Image.LANCZOS)

    background = Image.new("RGB", (target_width, target_height), (0, 0, 0))
    offset_x = (target_width - new_width) // 2
    offset_y = (target_height - new_height) // 2

    background.paste(img_resized, (offset_x, offset_y))
    return background


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "video-capture",
        "version": "2.1.0"
    }


@app.post("/capturar")
def capturar(data: CaptureRequest):
    screenshot_bytes = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
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

            # Espera y scroll (clave en Render Free)
            page.wait_for_timeout(4000)
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(3000)

            screenshot_bytes = page.screenshot(full_page=False)
            browser.close()

        # Procesar imagen
        image = Image.open(io.BytesIO(screenshot_bytes))
        image = normalizar_imagen(image)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85, optimize=True)

        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {
            "status": "success",
            "image_base64": image_base64
        }

    except TimeoutError:
        # Timeout real (no se pudo cargar nada)
        return {
            "status": "error",
            "reason": "La página no respondió a tiempo"
        }

    except Exception:
        # FALLBACK FINAL: si hubo screenshot, úsalo igual
        if screenshot_bytes:
            try:
                image = Image.open(io.BytesIO(screenshot_bytes))
                image = normalizar_imagen(image)

                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=85, optimize=True)

                image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                return {
                    "status": "success",
                    "image_base64": image_base64
                }
            except Exception:
                pass

        # Si no hubo absolutamente nada
        return {
            "status": "error",
            "reason": "No se pudo generar la captura"
        }

