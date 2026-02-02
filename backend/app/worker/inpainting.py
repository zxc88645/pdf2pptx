"""Stable Diffusion Inpainting to remove text from page images."""
from pathlib import Path
import torch
from PIL import Image
import numpy as np

# Default inpainting model (Hugging Face)
INPAINT_MODEL = "runwayml/stable-diffusion-inpainting"
# Fallback smaller model if needed: "redstone/diffusers-inpainting"


_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from diffusers import StableDiffusionInpaintingPipeline
        from app.core.config import HF_CACHE_DIR
        cache = str(HF_CACHE_DIR)
        _pipeline = StableDiffusionInpaintingPipeline.from_pretrained(
            INPAINT_MODEL,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            cache_dir=cache,
        )
        _pipeline = _pipeline.to("cuda" if torch.cuda.is_available() else "cpu")
    return _pipeline


def inpaint_page(image_path: Path, mask_path: Path, out_path: Path,
                 height: int = 512, width: int = 512, num_inference_steps: int = 25) -> None:
    """Run inpainting: image + mask -> image with text removed. Resize to height x width for model."""
    pipe = get_pipeline()
    image = Image.open(image_path).convert("RGB")
    mask_img = Image.open(mask_path).convert("L")
    image = image.resize((width, height))
    mask_img = mask_img.resize((width, height))
    # In SD inpainting, mask = 1 (white) is the region to inpaint
    prompt = "background, no text, clean"
    result = pipe(prompt=prompt, image=image, mask_image=mask_img, num_inference_steps=num_inference_steps).images[0]
    result.save(out_path)


def inpaint_all_pages(pages_dir: Path, masks_dir: Path, inpainted_dir: Path,
                      target_size: int = 512) -> list[Path]:
    """Inpaint each page_XXX.png using corresponding mask; save to inpainted_dir."""
    inpainted_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for mask_path in sorted(masks_dir.glob("page_*.png"), key=lambda p: p.name):
        img_path = pages_dir / mask_path.name
        if not img_path.exists():
            continue
        out_path = inpainted_dir / mask_path.name
        inpaint_page(img_path, mask_path, out_path, height=target_size, width=target_size)
        paths.append(out_path)
    return paths
