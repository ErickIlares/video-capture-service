from fastapi import FastAPI
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from urllib.parse import urljoin

app = FastAPI(title="Video Capture Service")


class CaptureRequest(BaseModel):
    url_video: str


# ---------- UTILIDADES ----------

def generar_placeholder(texto: str) -> str:
    img = Image.new("RGB", (1280, 720), (45, 45, 45))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
    except:
        font = ImageFont.load_default()

    w, h = draw.textbbox((0, 0), texto, font=font)[2:]
    draw.text(
        ((1280 - w) / 2, (720 - h) / 2),
        texto,
        fill=(230, 230, 230),
        font=font,
    )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def normalizar_imagen(contenido: bytes) -> str:
    img = Image.open(io.BytesIO(contenido)).convert("RGB")
    img = img.resize((1280, 720), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


# ---------- ENDPOINTS ----------

@app.get("/health")
def health():
    return {"status": "ok", "service": "video-capture"}


@app.post("/capturar")
def capturar(data: CaptureRequest):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "es-ES,es;q=0.9",
        }

        r = requests.get(data.url_video, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        candidatos = []

        # OG secure
        tag = soup.find("meta", property="og:image:secure_url")
        if tag and tag.get("content"):
            candidatos.append(tag["content"])

        # OG image
        tag = soup.find("meta", property="og:image")
        if tag and tag.get("content"):
            candidatos.append(tag["content"])

        # Twitter image
        tag = soup.find("meta", attrs={"name": "twitter:image"})
        if tag and tag.get("content"):
            candidatos.append(tag["content"])

        # Primera imagen visible
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and not src.startswith("data:"):
                candidatos.append(urljoin(data.url_video, src))
                break

        for url_img in candidatos:
            try:
                img_resp = requests.get(url_img, headers=headers, timeout=10)
                if img_resp.status_code == 200 and len(img_resp.content) > 5000:
                    return {
                        "status": "success",
                        "image_base64": normalizar_imagen(img_resp.content),
                    }
            except:
                continue

        return {
            "status": "success",
            "image_base64": generar_placeholder("Contenido no disponible"),
        }

    except Exception:
        return {
            "status": "success",
            "image_base64": generar_placeholder("Error al generar imagen"),
        }
