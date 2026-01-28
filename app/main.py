from fastapi import FastAPI
from pydantic import BaseModel
from PIL import Image
import requests
from bs4 import BeautifulSoup
import base64
import io

app = FastAPI(title="Video Capture Service")


class CaptureRequest(BaseModel):
    url_video: str


def imagen_placeholder() -> str:
    img = Image.new("RGB", (1280, 720), (240, 240, 240))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def descargar_y_normalizar_imagen(url: str) -> str | None:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()

        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        img = img.resize((1280, 720), Image.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)

        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "video-capture",
        "version": "4.1.0"
    }


@app.post("/capturar")
def capturar(data: CaptureRequest):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        html = requests.get(data.url_video, headers=headers, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        # 1️⃣ og:image (principal)
        meta = soup.find("meta", property="og:image")

        # 2️⃣ twitter:image (fallback)
        if not meta:
            meta = soup.find("meta", attrs={"name": "twitter:image"})

        if meta and meta.get("content"):
            image_base64 = descargar_y_normalizar_imagen(meta["content"])
            if image_base64:
                return {
                    "status": "success",
                    "image_base64": image_base64
                }
    except Exception:
        pass

    # 3️⃣ Placeholder final (nunca falla)
    return {
        "status": "success",
        "image_base64": imagen_placeholder()
    }
