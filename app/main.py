from fastapi import FastAPI
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import base64
import io
from PIL import Image

app = FastAPI(title="Video Capture Service")


class CaptureRequest(BaseModel):
    url_video: str


def placeholder_base64() -> str:
    img = Image.new("RGB", (1280, 720), (60, 60, 60))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "video-capture",
        "mode": "og-image"
    }


@app.post("/capturar")
def capturar(data: CaptureRequest):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            )
        }

        response = requests.get(data.url_video, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        og_image = soup.find("meta", property="og:image")

        if not og_image or not og_image.get("content"):
            return {
                "status": "success",
                "image_base64": placeholder_base64()
            }

        image_url = og_image["content"]
        img_response = requests.get(image_url, headers=headers, timeout=15)
        img_response.raise_for_status()

        return {
            "status": "success",
            "image_base64": base64.b64encode(img_response.content).decode("utf-8")
        }

    except Exception:
        return {
            "status": "success",
            "image_base64": placeholder_base64()
        }
