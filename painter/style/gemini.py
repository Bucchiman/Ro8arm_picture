"""Gemini (cloud) style transfer backend for PCs without a large GPU.

The input image is sent to the Google Gemini API together with the style prompt, so it needs a network connection
and an API key (GEMINI_API_KEY or GOOGLE_API_KEY). strength / ControlNet scale / steps do not apply here: Gemini is
asked in words to keep the composition. Only google-genai is required (no torch).
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable

import cv2
import numpy as np

from painter.analysis.palette import crop_to_aspect
from painter.style.stylizer import StyleRequest

DEFAULT_MODEL = "gemini-2.5-flash-image"
# aspect ratios the image models accept
ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
RETRY_STATUS = {429, 500, 503}

PROMPT_TEMPLATE = (
    "Repaint this image as a {style}. Keep exactly the same composition, subjects, perspective and layout as the "
    "input image; change only the artistic style, brushwork and color treatment. "
    "Do not add any text, frame, border or signature."
)


def api_key_from_env() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def nearest_aspect_ratio(aspect: float) -> str:
    def value(r: str) -> float:
        w, h = r.split(":")
        return int(w) / int(h)

    return min(ASPECT_RATIOS, key=lambda r: abs(np.log(value(r) / aspect)))


class GeminiBackend:
    name = "gemini"

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None, client: Any = None,
                 retries: int = 2, log: Callable[[str], None] = print):
        self.model = model
        self.retries = retries
        self.log = log
        if client is None:
            from google import genai

            api_key = api_key or api_key_from_env()
            if not api_key:
                raise RuntimeError("Gemini を使うには環境変数 GEMINI_API_KEY に API キーを設定してください")
            client = genai.Client(api_key=api_key)
        self.client = client

    def _generate(self, image_rgb: np.ndarray, req: StyleRequest):
        from google.genai import errors, types

        ok, jpg = cv2.imencode(".jpg", cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        assert ok
        h, w = image_rgb.shape[:2]
        contents = [
            types.Part.from_bytes(data=jpg.tobytes(), mime_type="image/jpeg"),
            PROMPT_TEMPLATE.format(style=req.prompt),
        ]
        config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=nearest_aspect_ratio(w / h)),
            seed=req.seed,
        )
        for attempt in range(self.retries + 1):
            try:
                return self.client.models.generate_content(model=self.model, contents=contents, config=config)
            except errors.APIError as e:
                if e.code in RETRY_STATUS and attempt < self.retries:
                    self.log(f"Gemini {e.code}, retrying ({attempt + 1}/{self.retries})")
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"Gemini API エラー {e.code}: {e.message}") from e
        raise AssertionError("unreachable")

    def __call__(self, image_rgb: np.ndarray, control_rgb: np.ndarray, req: StyleRequest) -> np.ndarray:
        resp = self._generate(image_rgb, req)
        texts = []
        for cand in resp.candidates or []:
            for part in (cand.content.parts if cand.content else None) or []:
                if part.inline_data is not None and part.inline_data.data:
                    buf = np.frombuffer(part.inline_data.data, np.uint8)
                    bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
                    if bgr is None:
                        continue
                    out = crop_to_aspect(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), image_rgb.shape[1] / image_rgb.shape[0])
                    return cv2.resize(out, (image_rgb.shape[1], image_rgb.shape[0]), interpolation=cv2.INTER_CUBIC)
                if part.text:
                    texts.append(part.text)
        reason = ""
        if resp.candidates:
            reason = str(resp.candidates[0].finish_reason or "")
        elif getattr(resp, "prompt_feedback", None):
            reason = str(resp.prompt_feedback.block_reason or "")
        detail = " / ".join(t.strip() for t in texts if t.strip())[:300]
        raise RuntimeError(f"Gemini が画像を返しませんでした ({reason or 'no image'}) {detail}".strip())
