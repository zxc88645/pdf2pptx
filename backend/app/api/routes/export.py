import io
import re
import tempfile
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, Response

from app.config import OUTPUT_DIR
from app.services.pdf_service import (
    images_to_pdf,
    pdf_page_to_image,
    pdf_replace_page_with_image,
    get_full_page_images,
)
from app.services.ppt_service import images_to_pptx
from app.services.inpaint import run_inpaint

router = APIRouter(prefix="/api", tags=["export"])


@router.post("/export/pdf")
async def export_pdf(files: list[UploadFile] = File(...)):
    """上傳多張圖片，組合成一個 PDF 並回傳。"""
    if not files:
        raise HTTPException(400, "至少需上傳一張圖片")
    images = []
    for f in files:
        if not f.content_type or not f.content_type.startswith("image/"):
            continue
        raw = await f.read()
        images.append(raw)
    if not images:
        raise HTTPException(400, "未包含有效圖片")
    out_path = OUTPUT_DIR / f"{uuid.uuid4().hex}.pdf"
    try:
        images_to_pdf(images, out_path)
    except Exception as e:
        raise HTTPException(500, f"組裝 PDF 失敗: {str(e)}")
    return FileResponse(str(out_path), media_type="application/pdf", filename="output.pdf")


@router.post("/export/pdf-from-pdf")
async def export_pdf_from_pdf(
    pdf: UploadFile = File(...),
    replace_page_index: int = Form(...),
    mask: UploadFile = File(...),
):
    """上傳原 PDF、要替換的頁碼（0-based）、該頁的 mask；後端轉圖後只對該頁 inpainting，再組合成新 PDF。"""
    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "請上傳 PDF 檔")
    if not mask.content_type or not mask.content_type.startswith("image/"):
        raise HTTPException(400, "mask 必須為圖片檔")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(await pdf.read())
        mask_path = tmp_path / "mask.png"
        mask_path.write_bytes(await mask.read())

        import fitz
        doc = fitz.open(pdf_path)
        total = len(doc)
        doc.close()
        if replace_page_index < 0 or replace_page_index >= total:
            raise HTTPException(400, f"replace_page_index 應在 0..{total - 1}")

        # 該頁轉圖作為 inpainting 的 image
        page_img = pdf_page_to_image(pdf_path, replace_page_index)
        page_img_path = tmp_path / "page.png"
        page_img.save(page_img_path)
        try:
            result_png, _ = run_inpaint(page_img_path, mask_path)
        except Exception as e:
            raise HTTPException(500, f"Inpainting 失敗: {str(e)}")

        out_path = OUTPUT_DIR / f"{uuid.uuid4().hex}.pdf"
        pdf_replace_page_with_image(pdf_path, replace_page_index, result_png, out_path)

    return FileResponse(str(out_path), media_type="application/pdf", filename="output.pdf")


@router.post("/export/ppt")
async def export_ppt(files: list[UploadFile] = File(...)):
    """上傳多張圖片，組合成 PPTX，每圖一頁。"""
    if not files:
        raise HTTPException(400, "至少需上傳一張圖片")
    images = []
    for f in files:
        if not f.content_type or not f.content_type.startswith("image/"):
            continue
        raw = await f.read()
        images.append(raw)
    if not images:
        raise HTTPException(400, "未包含有效圖片")
    out_path = OUTPUT_DIR / f"{uuid.uuid4().hex}.pptx"
    try:
        images_to_pptx(images, out_path)
    except Exception as e:
        raise HTTPException(500, f"組裝 PPT 失敗: {str(e)}")
    return FileResponse(str(out_path), media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename="output.pptx")


async def _get_full_export_form(request: Request):
    """解析完整匯出表單：pdf + 替換頁 (replacement, filename=page_0.png)。回傳 (pdf_bytes, replacements: dict[int, bytes])。"""
    form = await request.form()
    pdf_file = form.get("pdf")
    if not pdf_file or not (getattr(pdf_file, "filename") or "").lower().endswith(".pdf"):
        raise HTTPException(400, "請上傳 PDF 檔")
    pdf_bytes = await pdf_file.read()
    replacements = {}
    for f in form.getlist("replacement") or []:
        if not getattr(f, "filename", None):
            continue
        m = re.match(r"page_(\d+)\.png", (f.filename or "").lower())
        if m:
            idx = int(m.group(1))
            replacements[idx] = await f.read()
    return pdf_bytes, replacements


@router.post("/export/pdf-full")
async def export_pdf_full(request: Request):
    """上傳 PDF + 選填替換頁（replacement, filename=page_0.png），匯出完整頁面為單一 PDF。"""
    pdf_bytes, replacements = await _get_full_export_form(request)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(pdf_bytes)
        images = get_full_page_images(pdf_path, replacements)
    out_path = OUTPUT_DIR / f"{uuid.uuid4().hex}.pdf"
    try:
        images_to_pdf(images, out_path)
    except Exception as e:
        raise HTTPException(500, f"組裝 PDF 失敗: {str(e)}")
    return FileResponse(str(out_path), media_type="application/pdf", filename="output.pdf")


@router.post("/export/ppt-full")
async def export_ppt_full(request: Request):
    """上傳 PDF + 選填替換頁，匯出完整頁面為單一 PPTX。"""
    pdf_bytes, replacements = await _get_full_export_form(request)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(pdf_bytes)
        images = get_full_page_images(pdf_path, replacements)
    out_path = OUTPUT_DIR / f"{uuid.uuid4().hex}.pptx"
    try:
        images_to_pptx(images, out_path)
    except Exception as e:
        raise HTTPException(500, f"組裝 PPT 失敗: {str(e)}")
    return FileResponse(str(out_path), media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename="output.pptx")


@router.post("/export/png-zip-full")
async def export_png_zip_full(request: Request):
    """上傳 PDF + 選填替換頁，匯出完整頁面為 PNG 壓縮檔。"""
    pdf_bytes, replacements = await _get_full_export_form(request)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(pdf_bytes)
        images = get_full_page_images(pdf_path, replacements)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, img_bytes in enumerate(images):
            zf.writestr(f"page_{i + 1}.png", img_bytes)
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=pages.zip"})
