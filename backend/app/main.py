"""FastAPI backend: /health, /convert (PDF -> pptx), /inpaint (image inpainting proxy), /pdf-to-images, /images-to-pdf."""
import io
import tempfile
import zipfile
from pathlib import Path

import img2pdf
import requests
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.responses import Response
from PIL import Image

from app.config import MAX_IMAGES_TO_PDF, MAX_PDF_PAGES
from app.services.inpaint_client import run_inpaint
from app.services.mask_utils import draw_mask
from app.services.ocr_client import run_ocr
from app.services.pdf_to_images import pdf_to_images
from app.services.ppt_builder import build_pptx

app = FastAPI(title="PDF to PPT API", version="0.1.0")


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


@app.post("/ocr")
def ocr_endpoint(
    image: UploadFile = File(...),
    min_score: float | None = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum OCR recognition score [0-1]; lower results will be filtered out.",
    ),
):
    """
    Standalone OCR: accept a single image (form field 'image'), return JSON:
    { "results": [ { "bbox": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], "text": "..." } ] }
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    try:
        data = image.file.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read file: {e}") from e
    if not data:
        raise HTTPException(400, "Empty file")
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as e:
        raise HTTPException(400, f"Invalid image: {e}") from e
    try:
        results = run_ocr(img, min_score=min_score)
    except requests.RequestException as e:
        raise HTTPException(503, f"OCR service unavailable: {e}") from e
    return {"results": results}


@app.post("/convert", response_class=Response)
def convert(
    file: UploadFile = File(...),
    backend: str | None = Query(
        None,
        description="Inpaint backend: 'lama' (default) or 'sd' (Stable Diffusion)",
    ),
    debug: bool = Query(
        False,
        description="啟用 debug：轉出的 PPT 會將 OCR 文字區塊框起來",
    ),
    ocr_min_score: float | None = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum OCR recognition score [0-1] used during PDF->PPT conversion.",
    ),
):
    """
    Accept a PDF file (form field 'file'), convert to pptx, return as attachment.
    Pipeline: PDF -> images -> OCR -> mask -> Inpaint -> pptx (background + text boxes).
    """
    inpaint_backend = (backend or "lama").strip().lower() or "lama"
    if inpaint_backend not in ("lama", "sd"):
        inpaint_backend = "lama"
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "File must be a PDF")
    try:
        content = file.file.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read file: {e}") from e
    if not content:
        raise HTTPException(400, "Empty file")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        images = pdf_to_images(tmp_path)
        if len(images) > MAX_PDF_PAGES:
            raise HTTPException(
                400, f"PDF has {len(images)} pages; max {MAX_PDF_PAGES} allowed for POC"
            )
        page_ocr_results = []
        inpainted_images = []
        for idx, img in enumerate(images, start=1):
            try:
                results = run_ocr(img, min_score=ocr_min_score)
            except requests.RequestException as e:
                raise HTTPException(503, f"OCR service unavailable: {e}") from e
            page_ocr_results.append(results)
            mask = draw_mask(img.width, img.height, results)
            # Debug: 將每一頁的遮罩存成 PNG，檔名 mask_debug_page{n}.png
            try:
                mask.save(f"mask_debug_page{idx}.png")
            except Exception:
                # 儲存遮罩失敗不應影響主要轉檔流程，因此忽略錯誤
                pass
            try:
                out = run_inpaint(img, mask, backend=inpaint_backend)
            except requests.RequestException as e:
                raise HTTPException(503, f"Inpaint service unavailable: {e}") from e
            inpainted_images.append(out)
        pptx_bytes = build_pptx(inpainted_images, page_ocr_results, debug=debug)
        return Response(
            content=pptx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": "attachment; filename=output.pptx"},
        )
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/inpaint", response_class=Response)
def inpaint_endpoint(
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    backend: str | None = Query(
        None,
        description="Inpaint backend: 'sd' (Stable Diffusion, default) or 'lama' (LaMa)",
    ),
):
    """
    Proxy endpoint for image inpainting.
    Accepts image and mask (both image/*), forwards to inpaint-service, and returns PNG bytes.
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(400, "image must be an image file")
    if not mask.content_type or not mask.content_type.startswith("image/"):
        raise HTTPException(400, "mask must be an image file")

    try:
        image_bytes = image.file.read()
        mask_bytes = mask.file.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read files: {e}") from e

    if not image_bytes or not mask_bytes:
        raise HTTPException(400, "Empty file")

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L")
    except Exception as e:
        raise HTTPException(400, f"Invalid image: {e}") from e

    if img.size != mask_img.size:
        raise HTTPException(400, "image and mask must have the same size")

    try:
        out = run_inpaint(img, mask_img, backend=backend)
    except requests.RequestException as e:
        raise HTTPException(503, f"Inpaint service unavailable: {e}") from e

    buf = io.BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.read(), media_type="image/png")


@app.post("/pdf-to-images", response_class=Response)
def pdf_to_images_endpoint(
    file: UploadFile = File(...),
    format: str = Query(
        "png",
        description="輸出格式: png 或 jpg",
    ),
    dpi: int = Query(
        150,
        ge=72,
        le=300,
        description="DPI（解析度）",
    ),
):
    """
    將 PDF 每頁轉成圖片（PNG 或 JPG），以 ZIP 壓縮檔回傳。
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "請上傳 PDF 檔案")
    try:
        content = file.file.read()
    except Exception as e:
        raise HTTPException(400, f"讀取檔案失敗: {e}") from e
    if not content:
        raise HTTPException(400, "空檔案")
    fmt = (format or "png").strip().lower()
    if fmt not in ("png", "jpg", "jpeg"):
        fmt = "png"
    if fmt == "jpeg":
        fmt = "jpg"
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        images = pdf_to_images(tmp_path, dpi=dpi)
        if len(images) > MAX_PDF_PAGES:
            raise HTTPException(
                400, f"PDF 頁數 {len(images)} 超過上限 {MAX_PDF_PAGES}"
            )
        buf = io.BytesIO()
        ext = ".png" if fmt == "png" else ".jpg"
        pil_format = "PNG" if fmt == "png" else "JPEG"
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, img in enumerate(images, start=1):
                img_buf = io.BytesIO()
                img.save(img_buf, format=pil_format, quality=95 if fmt == "jpg" else None)
                img_buf.seek(0)
                zf.writestr(f"page_{i:04d}{ext}", img_buf.read())
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=pdf_pages.zip"},
        )
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/images-to-pdf", response_class=Response)
def images_to_pdf_endpoint(
    files: list[UploadFile] = File(...),
):
    """
    將多張圖片（PNG、JPG 等）合併成一個 PDF，依上傳順序排列。
    """
    if not files or len(files) > MAX_IMAGES_TO_PDF:
        raise HTTPException(
            400, f"請上傳 1～{MAX_IMAGES_TO_PDF} 張圖片"
        )
    allowed = ("image/png", "image/jpeg", "image/jpg", "image/webp")
    img_bytes_list = []
    for f in files:
        if not f.content_type or f.content_type.lower() not in allowed:
            raise HTTPException(
                400, f"不支援的檔案類型: {f.filename or 'unknown'} ({f.content_type})"
            )
        try:
            data = f.file.read()
        except Exception as e:
            raise HTTPException(400, f"讀取檔案失敗: {e}") from e
        if not data:
            raise HTTPException(400, f"空檔案: {f.filename}")
        ct = (f.content_type or "").lower()
        if ct in ("image/jpeg", "image/jpg", "image/png"):
            img_bytes_list.append(data)
        else:
            try:
                img = Image.open(io.BytesIO(data)).convert("RGB")
                b = io.BytesIO()
                img.save(b, format="PNG")
                img_bytes_list.append(b.getvalue())
            except Exception as e:
                raise HTTPException(400, f"無法解析圖片: {f.filename} - {e}") from e
    try:
        pdf_bytes = img2pdf.convert(img_bytes_list)
    except Exception as e:
        raise HTTPException(500, f"轉換失敗: {e}") from e
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=output.pdf"},
    )
