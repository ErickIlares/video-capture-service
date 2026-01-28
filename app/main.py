from fastapi import FastAPI
from pydantic import BaseModel
from playwright.sync_api import sync_playwright, TimeoutError
from PIL import Image
import base64
import io

app = FastAPI(title="Video Capture Service")

# -------------------------
# MODELOS
# -------------------------
class CaptureRequest(BaseModel):
    url_video: str


# -------------------------
# UTILIDADES
# -------------------------
def detectar_plataforma(url: str) -> str:
    url = url.lower()
    if "instagram.com" in url:
        return "instagram"
    if "tiktok.com" in url:
        return "tiktok"
    if "facebook.com" in url or "fb.watch" in url:
        return "facebook"
    return "unknown"


def detectar_error_contenido(texto: str, plataforma: str) -> str:
    texto = texto.lower()

    if plataforma == "instagram":
        if "login" in texto:
            return "El contenido requiere iniciar sesión"
        if "no disponible" in texto or "page isn't available" in texto:
            return "El video fue eliminado o no existe"
        if "privado" in texto:
            return "El video es privado"

    if plataforma == "tiktok":
        if "no longer available" in texto or "video unavailable" in texto:
            return "El video fue eliminado"
        if "private" in texto:
            return "El contenido es privado"

    if plataforma == "facebook":
        if "content not available" in texto:
            return "El video fue eliminado"
        if "privacy" in texto or "not public" in texto:
            return "El contenido no es público"
        if "login" in texto:
            return "El contenido requiere iniciar sesión"

    if "video_not_found" in texto or "video_not_visible" in texto:
        return "No se pudo detectar el video"

    return "No se pudo generar la captura"


def esperar_frame_estable(page):
    page.evaluate("""
        () => {
            const video = document.querySelector('video');
            if (video) {
                video.muted = true;
                video.play().catch(() => {});
            }
        }
    """)


def screenshot_video(page):
    video = page.query_selector("video")
    if not video:
        raise Exception("video_not_found")

    box = video.bounding_box()
    if not box:
        raise Exception("video_not_visible")

    return page.screenshot(
        clip={
            "x": box["x"],
            "y": box["y"],
            "width": box["width"],
            "height": box["height"]
        }
    )


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


# -------------------------
# ENDPOINTS
# -------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "video-capture",
        "version": "1.0.0"
    }


@app.post("/capturar")
def capturar(data: CaptureRequest):
    plataforma = detectar_plataforma(data.url_video)

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

            page.wait_for_selector("video", timeout=10000)
            esperar_frame_estable(page)
            page.wait_for_timeout(2000)

            try:
                screenshot_bytes = screenshot_video(page)
            except Exception:
                page.wait_for_timeout(2000)
                screenshot_bytes = screenshot_video(page)

            browser.close()

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
        return {
            "status": "error",
            "reason": "La página no respondió a tiempo"
        }

    except Exception as e:
        reason = detectar_error_contenido(str(e), plataforma)
        return {
            "status": "error",
            "reason": reason
        }
