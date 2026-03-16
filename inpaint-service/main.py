"""Inpaint service: FastAPI + Stable Diffusion Inpainting, POST /inpaint returns image."""
import io
import logging
import os
import sys

import numpy as np
import torch
import types

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# 一些新版 diffusers 在 utils.torch_utils / loaders.single_file 中
# 會無條件使用 torch.xpu 與 torch.distributed.device_mesh 等新 API。
# 在較舊或精簡版的 PyTorch 中這些可能不存在，會在 import 階段直接噴錯。
# 這裡針對「沒有這些後端」的情況補上最小 stub，讓 diffusers 可以正常載入，
# 而且不會真的啟用 XPU / DeviceMesh 等功能。

# ---- XPU stub ----
if not hasattr(torch, "xpu"):
    class _DummyXPU:
        @staticmethod
        def empty_cache():
            return None

        @staticmethod
        def device_count() -> int:
            return 0

        @staticmethod
        def manual_seed(_seed: int):
            return None

        @staticmethod
        def reset_peak_memory_stats():
            return None

        @staticmethod
        def max_memory_allocated() -> int:
            return 0

        @staticmethod
        def synchronize():
            return None

        @staticmethod
        def is_available() -> bool:
            return False

    torch.xpu = _DummyXPU()  # type: ignore[attr-defined]

# ---- distributed.device_mesh stub ----
if hasattr(torch, "distributed") and not hasattr(torch.distributed, "device_mesh"):
    dm = types.SimpleNamespace(
        DeviceMesh=object,
        init_device_mesh=lambda *args, **kwargs: None,
    )
    torch.distributed.device_mesh = dm  # type: ignore[attr-defined]

from diffusers import StableDiffusionInpaintPipeline
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.responses import Response
from PIL import Image
from simple_lama_inpainting import SimpleLama

app = FastAPI(title="Inpaint Service", version="0.1.0")

# Load pipeline once at startup (GPU when available)
device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {device}")

if device == "cuda":
    logger.info(f"CUDA available. GPU: {torch.cuda.get_device_name(0)}")

pipe = None
lama_model: SimpleLama | None = None

def load_model():
    """Load the inpaint pipeline."""
    global pipe
    try:
        model_id = os.getenv("INPAINT_MODEL_ID", "runwayml/stable-diffusion-inpainting")
        logger.info(f"Loading model: {model_id}")
        
        pipe = StableDiffusionInpaintPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            safety_checker=None,
        )
        logger.info(f"Model loaded successfully")
        
        pipe = pipe.to(device)
        if device == "cuda":
            pipe.enable_attention_slicing()
            logger.info("Attention slicing enabled for GPU")
        else:
            logger.warning("Running on CPU; inpaint will be very slow. Consider using GPU.")
        
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}", exc_info=True)
        return False

def load_lama() -> bool:
    """Lazy-load LaMa inpainting model."""
    global lama_model
    if lama_model is not None:
        return True
    try:
        logger.info("Loading LaMa (simple-lama-inpainting) model...")
        lama_model = SimpleLama()
        logger.info("LaMa model loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to load LaMa model: {e}", exc_info=True)
        lama_model = None
        return False


# Attempt to load SD model on startup (LaMa 採用延遲載入，第一次使用時再載)
if not load_model():
    logger.error("Stable Diffusion model loading failed; SD backend may not function properly.")

# Fixed canvas size for inpaint: scale image/mask to fit, pad with black (multiples of 8 for SD)
_raw_canvas_size = int(os.getenv("INPAINT_CANVAS_SIZE", os.getenv("INPAINT_SIZE", "1024")))
INPAINT_CANVAS_SIZE = max(8, (_raw_canvas_size // 8) * 8)
# LaMa 可單獨使用較大畫布以提升抹除品質（GPU 時建議 1536 或 2048）
_raw_lama_canvas = int(os.getenv("LAMA_CANVAS_SIZE", str(INPAINT_CANVAS_SIZE)))
LAMA_CANVAS_SIZE = max(8, (_raw_lama_canvas // 8) * 8)
# Legacy: INPAINT_SIZE used as canvas size when INPAINT_CANVAS_SIZE not set
INPAINT_SIZE = INPAINT_CANVAS_SIZE


def _binarize_mask(mask_image: Image.Image, threshold: int = 127) -> Image.Image:
    """Ensure mask is strictly 0 or 255 (LaMa expects binary mask)."""
    arr = np.array(mask_image)
    out = np.where(arr > threshold, 255, 0).astype(np.uint8)
    return Image.fromarray(out, mode="L")


def _dilate_mask(mask_image: Image.Image, radius: int = 2) -> Image.Image:
    """Slightly expand mask so LaMa has more context at edges (improves blending)."""
    if radius <= 0:
        return mask_image
    arr = np.array(mask_image)
    h, w = arr.shape
    out = arr.copy()
    ys, xs = np.where(arr > 127)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx == 0 and dy == 0:
                continue
            ny = np.clip(ys + dy, 0, h - 1)
            nx = np.clip(xs + dx, 0, w - 1)
            out[ny, nx] = 255
    return Image.fromarray(out, mode="L")


def _to_fixed_canvas(
    image: Image.Image,
    mask_image: Image.Image,
    size: int,
) -> tuple[Image.Image, Image.Image, tuple[int, int, int, int]]:
    """
    Scale image and mask to fit inside size×size (same scale), paste onto black canvas.
    Returns (padded_image, padded_mask, content_box) with content_box (x1, y1, x2, y2) on canvas.
    """
    w, h = image.size
    if w <= 0 or h <= 0:
        raise ValueError("Image size must be positive")
    scale = min(size / w, size / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    new_w = max(8, min(size, (new_w // 8) * 8))
    new_h = max(8, min(size, (new_h // 8) * 8))
    ox = (size - new_w) // 2
    oy = (size - new_h) // 2
    content_box = (ox, oy, ox + new_w, oy + new_h)
    img_resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    mask_resized = mask_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    padded_image = Image.new("RGB", (size, size), (0, 0, 0))
    padded_image.paste(img_resized, (ox, oy))
    padded_mask = Image.new("L", (size, size), 0)
    padded_mask.paste(mask_resized, (ox, oy))
    return padded_image, padded_mask, content_box


def _resize_to_multiple(img: Image.Image, size: int) -> Image.Image:
    """Resize image so longer side is size (multiple of 8), keep aspect."""
    w, h = img.size
    if max(w, h) <= size:
        return img
    if w >= h:
        nw, nh = size, int(h * size / w)
    else:
        nw, nh = int(w * size / h), size
    nw = max(8, (nw // 8) * 8)
    nh = max(8, (nh // 8) * 8)
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def _compute_mask_bboxes(
    mask_image: Image.Image, padding: int, max_regions: int
) -> list[tuple[int, int, int, int]]:
    """
    將遮罩中非零像素做連通區域分群，回傳多個 bounding box。
    每個 bbox 為 (x1, y1, x2, y2)，並加上 padding。最多回傳 max_regions 個區域。
    """
    try:
        mask_arr = np.array(mask_image)
    except Exception as e:
        logger.error(f"Failed to convert mask to array: {e}")
        return []
    h, w = mask_arr.shape
    visited = np.zeros_like(mask_arr, dtype=bool)
    ys, xs = np.where(mask_arr > 0)
    if xs.size == 0 or ys.size == 0:
        return []

    bboxes: list[tuple[int, int, int, int]] = []
    pad = max(0, padding)

    for sy, sx in zip(ys, xs):
        if visited[sy, sx]:
            continue
        if mask_arr[sy, sx] == 0:
            continue

        # BFS / DFS 尋找一個連通區域
        stack = [(int(sx), int(sy))]
        visited[sy, sx] = True
        min_x = max_x = sx
        min_y = max_y = sy

        while stack:
            x, y = stack.pop()
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y

            # 四鄰接
            for nx, ny in (
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
            ):
                if nx < 0 or nx >= w or ny < 0 or ny >= h:
                    continue
                if visited[ny, nx]:
                    continue
                if mask_arr[ny, nx] == 0:
                    continue
                visited[ny, nx] = True
                stack.append((nx, ny))

        # 取得此連通區域的 bbox，並套用 padding
        x1 = int(min_x)
        x2 = int(max_x) + 1
        y1 = int(min_y)
        y2 = int(max_y) + 1

        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(w, x2 + pad)
        y2 = min(h, y2 + pad)

        if x2 > x1 and y2 > y1:
            bboxes.append((x1, y1, x2, y2))
            if len(bboxes) >= max_regions:
                break

    return bboxes


@app.get("/health")
def health():
    """Health check."""
    status = "ready" if pipe is not None else "initializing"
    return {
        "status": status,
        "device": device,
        "model_loaded": pipe is not None,
    }


def _select_backend(request_backend: str | None) -> str:
    """
    Normalize backend name. 優先使用請求參數，其次讀環境變數 INPAINT_BACKEND，預設 'sd'。
    目前支援：
      - 'sd'   : Stable Diffusion Inpainting（預設）
      - 'lama' : LaMa (simple-lama-inpainting)
    """
    backend = (request_backend or os.getenv("INPAINT_BACKEND", "sd")).strip().lower()
    if backend == "lama":
        return "lama"
    # fallback
    return "sd"


@app.post("/inpaint", response_class=Response)
def inpaint(
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    backend: str | None = Query(
        None,
        description="Inpaint backend: 'sd' (Stable Diffusion, default) or 'lama' (LaMa)",
    ),
):
    """
    Accept image and mask (form fields). Mask: white (255) = region to inpaint, black (0) = keep.
    Returns inpainted image as PNG bytes.
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(400, "image must be an image file")
    if not mask.content_type or not mask.content_type.startswith("image/"):
        raise HTTPException(400, "mask must be an image file")
    try:
        img_data = image.file.read()
        mask_data = mask.file.read()
    except Exception as e:
        logger.error(f"Failed to read files: {e}")
        raise HTTPException(400, f"Failed to read files: {e}") from e
    if not img_data or not mask_data:
        raise HTTPException(400, "Empty file")
    try:
        init_image = Image.open(io.BytesIO(img_data)).convert("RGB")
        mask_image = Image.open(io.BytesIO(mask_data)).convert("L")
    except Exception as e:
        logger.error(f"Invalid image: {e}")
        raise HTTPException(400, f"Invalid image: {e}") from e
    if init_image.size != mask_image.size:
        raise HTTPException(400, "image and mask must have the same size")
    # 1. 找出遮罩的多個連通區域 bounding box，並加上 padding
    padding = int(os.getenv("INPAINT_PADDING", "96"))
    max_regions = int(os.getenv("INPAINT_MAX_REGIONS", "32"))
    logger.info(f"Processing image {init_image.size}; padding={padding}, max_regions={max_regions}")
    bboxes = _compute_mask_bboxes(mask_image, padding=padding, max_regions=max_regions)
    logger.info(f"Found {len(bboxes)} inpaint regions")

    # 若沒有任何需要 inpaint 的區域，直接回傳原圖
    if not bboxes:
        buf = io.BytesIO()
        init_image.save(buf, format="PNG")
        buf.seek(0)
        return Response(content=buf.read(), media_type="image/png")

    # 2. 根據 backend 選擇使用 Stable Diffusion 或 LaMa
    backend_name = _select_backend(backend)
    logger.info(f"Using inpaint backend: {backend_name}")

    if backend_name == "lama":
        # ---- LaMa：固定 1024 畫布、不足填黑，再還原原尺寸 ----
        if not load_lama():
            logger.error("LaMa backend not available (failed to load model)")
            raise HTTPException(503, "LaMa backend not available")
        try:
            padded_img, padded_mask, content_box = _to_fixed_canvas(
                init_image, mask_image, size=LAMA_CANVAS_SIZE
            )
            # 二值化遮罩（LaMa 預期 0/255），並可選輕微膨脹以改善邊緣融合
            padded_mask = _binarize_mask(padded_mask, threshold=127)
            lama_dilate = int(os.getenv("LAMA_MASK_DILATE", "2"))
            if lama_dilate > 0:
                padded_mask = _dilate_mask(padded_mask, radius=lama_dilate)
            logger.info(f"Running LaMa inpaint on {LAMA_CANVAS_SIZE}x{LAMA_CANVAS_SIZE} canvas...")
            out = lama_model(padded_img, padded_mask)  # type: ignore[misc]
            out_crop = out.crop(content_box)
            out_resized = out_crop.resize(init_image.size, Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            out_resized.save(buf, format="PNG")
            buf.seek(0)
            return Response(content=buf.read(), media_type="image/png")
        except Exception as e:
            logger.error(f"LaMa inpaint failed: {e}", exc_info=True)
            raise HTTPException(500, f"LaMa inpaint failed: {e}") from e

    # ---- Stable Diffusion patch-based inpaint（原本邏輯）----
    if pipe is None:
        logger.error("Stable Diffusion model not loaded; cannot process inpaint request")
        raise HTTPException(503, "Stable Diffusion backend not available; service initializing")

    # 預設提示詞：以「避免生成任何文字」為主，
    # 刻意不在 prompt 裡出現 slide/title 等關鍵字，減少模型產生新文字的傾向。
    prompt = (
        "clean background, same color as surrounding area, "
        "flat and smooth surface, preserve original layout, remove text only"
    )

    negative_prompt = (
        "text, letters, words, numbers, watermark, logo, symbols, "
        "patterns, textures, decorations, illustration, drawing, "
        "abstract shapes, graphics, noise, grain, artifacts, blurry, distorted, nsfw"
    )

    result = init_image.copy()

    for idx, (x1, y1, x2, y2) in enumerate(bboxes, start=1):
        try:
            # 2. 裁切局部區域（目前結果圖與原始遮罩）
            image_crop = result.crop((x1, y1, x2, y2))
            mask_crop = mask_image.crop((x1, y1, x2, y2))
            logger.info(f"Region {idx}: crop size {image_crop.size}")

            # 3. 固定畫布 1024×1024、不足填黑
            padded_img, padded_mask, content_box = _to_fixed_canvas(
                image_crop, mask_crop, size=INPAINT_CANVAS_SIZE
            )
            logger.info(f"Region {idx}: canvas {INPAINT_CANVAS_SIZE}x{INPAINT_CANVAS_SIZE}")

            # 4. 在固定畫布上做 SD inpainting
            logger.info(f"Region {idx}: running SD inpaint...")
            with torch.inference_mode():
                out = pipe(
                    prompt=prompt,
                    image=padded_img,
                    mask_image=padded_mask,
                    negative_prompt=negative_prompt,
                    num_inference_steps=int(os.getenv("INPAINT_STEPS", "50")),
                    strength=float(os.getenv("INPAINT_STRENGTH", "1.0")),
                    guidance_scale=float(os.getenv("INPAINT_GUIDANCE", "5.0")),
                ).images[0]
            logger.info(f"Region {idx}: SD inpaint complete")

            # 5. 從畫布裁出內容區，縮放回 bbox 大小，貼回 result
            out_crop = out.crop(content_box)
            out_resized = out_crop.resize((x2 - x1, y2 - y1), Image.Resampling.LANCZOS)
            result.paste(out_resized, (x1, y1))
        except Exception as e:
            logger.error(f"Region {idx}: SD inpaint failed: {e}", exc_info=True)
            # 若单个区域失败，继续处理其他区域而非中断
            continue

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.read(), media_type="image/png")
