import io
from pathlib import Path
from typing import Dict, List, Optional, Union

import fitz  # PyMuPDF
from PIL import Image

from app.config import PDF_DPI

# 嵌入 PDF 時用 JPEG 壓縮，避免檔案暴增（PNG 未壓縮點陣會很大）
PDF_IMAGE_JPEG_QUALITY = 90


def _ensure_pil(img: Union[Image.Image, bytes]) -> Image.Image:
    """將 Image 或 bytes 轉成 PIL Image（RGB）。"""
    if isinstance(img, bytes):
        return Image.open(io.BytesIO(img)).convert("RGB")
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _to_jpeg_bytes(img: Union[Image.Image, bytes], quality: int = PDF_IMAGE_JPEG_QUALITY) -> bytes:
    """將圖片轉成 JPEG bytes（RGB），用於嵌入 PDF 以縮小體積。"""
    pil = _ensure_pil(img)
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)
    return buf.read()


def _image_size_px(img: Union[Image.Image, bytes]) -> tuple[int, int]:
    """取得圖片像素尺寸 (width, height)。"""
    if isinstance(img, Image.Image):
        return img.size
    pil = Image.open(io.BytesIO(img))
    return pil.size


def pdf_page_to_image(pdf_path: Path, page_index: int, dpi: Optional[int] = None) -> Image.Image:
    """將 PDF 指定頁轉為 PIL Image。"""
    if dpi is None:
        dpi = PDF_DPI
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_index]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img
    finally:
        doc.close()


def images_to_pdf(images: List[Union[Image.Image, bytes]], output_path: Path, dpi: Optional[int] = None) -> None:
    """將多張圖片組合成一個 PDF，每頁尺寸依該頁圖片像素與 DPI 換算成點（72 pt = 1 inch），避免頁面過大、檔案膨脹。嵌入時轉 JPEG 以控制檔案大小。"""
    if dpi is None:
        dpi = PDF_DPI
    doc = fitz.open()
    for img in images:
        w_px, h_px = _image_size_px(img)
        # 依 DPI 換算：width_pt = width_px * 72 / dpi，使頁面為合理實體尺寸（與轉圖 DPI 一致）
        w_pt = w_px * 72.0 / dpi
        h_pt = h_px * 72.0 / dpi
        page = doc.new_page(width=w_pt, height=h_pt)
        jpeg_bytes = _to_jpeg_bytes(img)
        page.insert_image(page.rect, stream=jpeg_bytes)
    doc.save(str(output_path), use_objstms=True)
    doc.close()


def pdf_replace_page_with_image(
    pdf_path: Path, page_index: int, replacement_image: Union[Image.Image, bytes], output_path: Path, dpi: Optional[int] = None
) -> None:
    """將 PDF 中指定頁替換為給定圖片，其餘頁保持原樣（轉圖後組合成新 PDF）。"""
    if dpi is None:
        dpi = PDF_DPI
    with fitz.open(pdf_path) as doc:
        total = len(doc)
    images: List[Union[Image.Image, bytes]] = []
    for i in range(total):
        if i == page_index:
            images.append(replacement_image)
        else:
            images.append(pdf_page_to_image(pdf_path, i, dpi=dpi))
    images_to_pdf(images, output_path, dpi=dpi)


def get_full_page_images(
    pdf_path: Path,
    replacements: Dict[int, bytes],
    dpi: Optional[int] = None,
) -> List[bytes]:
    """
    取得完整文件的所有頁面圖（JPEG bytes，利於後續組 PDF 時保持小檔）。
    有替換的頁面用 replacements[page_index]，其餘從 PDF 轉圖並轉成 JPEG。
    """
    with fitz.open(pdf_path) as doc:
        total = len(doc)
    out: List[bytes] = []
    for i in range(total):
        if i in replacements:
            # 前端傳來的替換圖（多為 PNG）也轉成 JPEG 以一致壓縮
            out.append(_to_jpeg_bytes(replacements[i]))
        else:
            img = pdf_page_to_image(pdf_path, i, dpi=dpi)
            out.append(_to_jpeg_bytes(img))
    return out
