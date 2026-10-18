"""Style transfer: input photo -> painting-style image that keeps the composition.

Backends:
  sdxl    SDXL img2img guided by a Canny-edge ControlNet on the local GPU: img2img keeps the input colors/layout, the
          ControlNet keeps the contours, and the prompt sets the painting style. Models are fetched from Hugging Face
          on first use.
  gemini  Google Gemini image generation (painter.style.gemini) for PCs without a large GPU.
The heavy dependencies (torch, diffusers, google-genai) are only imported when a backend is actually created/loaded,
so the rest of the package (and tests) work without them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import cv2
import numpy as np

from painter.analysis.palette import crop_to_aspect
from painter.style.presets import CUSTOM, PRESETS, StylePreset

BASE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
CONTROLNET_MODEL = "diffusers/controlnet-canny-sdxl-1.0"
VAE_MODEL = "madebyollin/sdxl-vae-fp16-fix"  # the stock SDXL VAE overflows in fp16 (black images)
MIN_TOTAL_VRAM_GB = 12.0  # GPUs smaller than this get the cloud backend under --backend auto
REQUIRED_VRAM_GB = 12.0  # resident fp16 pipeline + activations at ~1 MP; below this, fall back to CPU offload
GEN_PIXELS = 1152 * 896  # SDXL native ~1 MP


@dataclass
class StyleRequest:
    prompt: str
    negative: str
    strength: float
    controlnet_scale: float
    steps: int = 30
    guidance: float = 7.0
    seed: int = 0


class Backend(Protocol):
    def __call__(self, image_rgb: np.ndarray, control_rgb: np.ndarray, req: StyleRequest) -> np.ndarray: ...


def make_request(preset_key: str, custom_prompt: str = "", strength: float | None = None,
                 controlnet_scale: float | None = None, steps: int = 30, seed: int = 0) -> StyleRequest:
    preset: StylePreset = PRESETS[preset_key]
    prompt = custom_prompt.strip() if preset_key == CUSTOM else preset.prompt
    if not prompt:
        raise ValueError("custom style needs a prompt")
    if preset_key != CUSTOM and custom_prompt.strip():
        prompt = f"{prompt}, {custom_prompt.strip()}"  # extra words refine a preset
    return StyleRequest(
        prompt=prompt, negative=preset.negative,
        strength=preset.strength if strength is None else strength,
        controlnet_scale=preset.controlnet_scale if controlnet_scale is None else controlnet_scale,
        steps=steps, seed=seed,
    )


def generation_size(aspect: float, pixels: int = GEN_PIXELS) -> tuple[int, int]:
    """(width, height), multiples of 64, close to `pixels` with the given width / height."""
    h = (pixels / aspect) ** 0.5
    w = h * aspect
    return max(int(round(w / 64)) * 64, 64), max(int(round(h / 64)) * 64, 64)


def canny_control(rgb: np.ndarray, low: int = 100, high: int = 200) -> np.ndarray:
    edges = cv2.Canny(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), low, high)
    return np.repeat(edges[:, :, None], 3, axis=2)


class DiffusersBackend:
    """Lazily loaded SDXL + ControlNet(Canny) img2img pipeline."""

    name = "sdxl"

    def __init__(self, offload: bool | None = None, log: Callable[[str], None] = print):
        self.offload = offload  # None = decide from free VRAM at load time
        self.log = log
        self.pipe = None

    def _load(self):
        import torch
        from diffusers import AutoencoderKL, ControlNetModel, StableDiffusionXLControlNetImg2ImgPipeline

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU not available")
        free, total = (v / 2**30 for v in torch.cuda.mem_get_info())
        offload = self.offload
        if offload is None:
            offload = free < REQUIRED_VRAM_GB
        self.log(f"GPU free {free:.1f} / {total:.1f} GiB -> {'CPU offload' if offload else 'resident on GPU'}")
        if offload and free < 4.0:
            raise RuntimeError(f"only {free:.1f} GiB VRAM free (GPU busy with other jobs?)")

        dtype = torch.float16
        controlnet = ControlNetModel.from_pretrained(CONTROLNET_MODEL, torch_dtype=dtype, variant="fp16")
        vae = AutoencoderKL.from_pretrained(VAE_MODEL, torch_dtype=dtype)
        pipe = StableDiffusionXLControlNetImg2ImgPipeline.from_pretrained(
            BASE_MODEL, controlnet=controlnet, vae=vae, torch_dtype=dtype, variant="fp16", use_safetensors=True,
        )
        if offload:
            pipe.enable_model_cpu_offload()
        else:
            pipe.to("cuda")
        pipe.set_progress_bar_config(disable=True)
        self.pipe = pipe

    def __call__(self, image_rgb: np.ndarray, control_rgb: np.ndarray, req: StyleRequest) -> np.ndarray:
        import torch
        from PIL import Image

        if self.pipe is None:
            self._load()
        h, w = image_rgb.shape[:2]
        out = self.pipe(
            prompt=req.prompt, negative_prompt=req.negative,
            image=Image.fromarray(image_rgb), control_image=Image.fromarray(control_rgb),
            strength=req.strength, controlnet_conditioning_scale=req.controlnet_scale,
            num_inference_steps=req.steps, guidance_scale=req.guidance, width=w, height=h,
            generator=torch.Generator("cpu").manual_seed(req.seed),
        ).images[0]
        return np.asarray(out.convert("RGB"))


def local_gpu_status() -> str | None:
    """None if the SDXL backend can run here, else the reason it cannot."""
    try:
        import diffusers  # noqa: F401
        import torch
    except ImportError as e:
        return f"{e.name} is not installed"
    if not torch.cuda.is_available():
        return "no CUDA GPU"
    total = torch.cuda.get_device_properties(0).total_memory / 2**30
    if total < MIN_TOTAL_VRAM_GB:
        return f"GPU has {total:.0f} GiB VRAM (< {MIN_TOTAL_VRAM_GB:.0f} GiB)"
    return None


def make_backend(kind: str = "auto", offload: bool | None = None, gemini_model: str | None = None,
                 log: Callable[[str], None] = print) -> Backend:
    """kind: 'sdxl', 'gemini', or 'auto' (SDXL when the local GPU is big enough, otherwise Gemini)."""
    if kind == "auto":
        reason = local_gpu_status()
        kind = "sdxl" if reason is None else "gemini"
        log(f"backend auto -> {kind}" + (f" ({reason})" if reason else ""))
    if kind == "sdxl":
        return DiffusersBackend(offload=offload, log=log)
    if kind == "gemini":
        from painter.style.gemini import DEFAULT_MODEL, GeminiBackend

        return GeminiBackend(model=gemini_model or DEFAULT_MODEL, log=log)
    raise ValueError(f"unknown backend {kind!r}")


class Stylizer:
    """Crop the input to the canvas aspect ratio, then restyle it with a backend (diffusers by default)."""

    def __init__(self, aspect: float, backend: Backend | None = None):
        self.aspect = aspect
        self.backend = backend if backend is not None else DiffusersBackend()

    def prepare(self, rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(input resized to the generation size, its Canny control image)."""
        cropped = crop_to_aspect(rgb, self.aspect)
        size = generation_size(self.aspect)
        interp = cv2.INTER_AREA if cropped.shape[1] > size[0] else cv2.INTER_CUBIC
        image = cv2.resize(cropped, size, interpolation=interp)
        return image, canny_control(image)

    def stylize(self, rgb: np.ndarray, req: StyleRequest, n_images: int = 1) -> list[np.ndarray]:
        image, control = self.prepare(rgb)
        results = []
        for i in range(n_images):
            r = StyleRequest(**{**req.__dict__, "seed": req.seed + i})
            results.append(self.backend(image, control, r))
        return results
