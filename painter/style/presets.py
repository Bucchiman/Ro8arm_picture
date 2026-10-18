"""Style presets for image-to-image style transfer.

strength: how far img2img may move away from the input (0 = unchanged, 1 = ignore input colors/texture).
controlnet_scale: how strictly the Canny edges of the input (composition, contours) are kept.
"""

from __future__ import annotations

from dataclasses import dataclass

COMMON_NEGATIVE = "photo, photorealistic, 3d render, blurry, lowres, jpeg artifacts, text, watermark, signature, frame"


@dataclass(frozen=True)
class StylePreset:
    label: str
    prompt: str
    negative: str = COMMON_NEGATIVE
    strength: float = 0.95  # tuned on a detailed photo: <= 0.8 stays almost photorealistic
    controlnet_scale: float = 0.45


CUSTOM = "custom"

PRESETS: dict[str, StylePreset] = {
    "impasto_oil": StylePreset(
        "油絵（厚塗り）",
        "thick impasto oil painting, visible palette knife and bristle brush strokes, rich textured paint, canvas",
    ),
    "van_gogh": StylePreset(
        "ゴッホ風",
        "oil painting in the style of Vincent van Gogh, swirling expressive brush strokes, vivid complementary colors, "
        "post-impressionism",
    ),
    "monet": StylePreset(
        "モネ風（印象派）",
        "impressionist oil painting in the style of Claude Monet, soft broken color, short dabs of paint, "
        "natural light, en plein air",
    ),
    "ukiyoe": StylePreset(
        "浮世絵",
        "ukiyo-e woodblock print in the style of Hokusai, flat areas of color, bold outlines, prussian blue, "
        "traditional japanese art",
    ),
    "watercolor": StylePreset(
        "水彩",
        "loose watercolor painting, wet-on-wet washes, soft bleeding edges, paper texture, transparent pigments",
        strength=0.9,
        controlnet_scale=0.5,
    ),
    "pointillism": StylePreset(
        "点描",
        "pointillism painting in the style of Georges Seurat, composed of small distinct dots of pure color",
    ),
    "fauvism": StylePreset(
        "フォーヴィスム",
        "fauvist oil painting in the style of Henri Matisse, wild unnatural bold colors, simplified forms, "
        "loose brushwork",
    ),
    CUSTOM: StylePreset("自由入力", ""),
}
