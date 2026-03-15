import io
from pathlib import Path
from typing import Dict, List, Optional, Union

import fitz  # PyMuPDF
from PIL import Image

from app.config import PDF_DPI

# 嵌入 PDF 時用 JPEG 壓縮，避免檔案暴增（PNG 未壓縮點陣會很大）
PDF_IMAGE_JPEG_QUALITY = 90


def _to_jpeg_bytes(img: Union[Image.Image, bytes], quality: int = PDF_IMAGE_JPEG_QUALITY) -> bytes:
    """將圖片轉成 JPEG bytes（RGB），用於嵌入 PDF 以縮小體積。"""
    if isinstance(img, bytes):
        img = Image.open(io.BytesIO(img)).convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)
    return buf.read()


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


# 頁面尺寸 485 × 271 mm，換算成點（72 pt = 1 inch）
PDF_PAGE_WIDTH_PT = 485 / 25.4 * 72
PDF_PAGE_HEIGHT_PT = 271 / 25.4 * 72


def images_to_pdf(images: List[Union[Image.Image, bytes]], output_path: Path) -> None:
    """將多張圖片組合成一個 PDF，每頁 485×271 mm、無邊距。嵌入時轉 JPEG 以控制檔案大小。"""
    doc = fitz.open()
    for img in images:
        jpeg_bytes = _to_jpeg_bytes(img)
        page = doc.new_page(width=PDF_PAGE_WIDTH_PT, height=PDF_PAGE_HEIGHT_PT)
        page.insert_image(page.rect, stream=jpeg_bytes)
    # 註：新版 PyMuPDF/MuPDF 已不支援 linear（Linearisation），僅一般儲存
    doc.save(str(output_path), use_objstms=True)
    doc.close()


def pdf_replace_page_with_image(
    pdf_path: Path, page_index: int, replacement_image: Union[Image.Image, bytes], output_path: Path, dpi: Optional[int] = None
) -> None:
    """將 PDF 中指定頁替換為給定圖片，其餘頁保持原樣（轉圖後組合成新 PDF）。"""
    with fitz.open(pdf_path) as doc:
        total = len(doc)
    images: List[Union[Image.Image, bytes]] = []
    for i in range(total):
        if i == page_index:
            images.append(replacement_image)
        else:
            images.append(pdf_page_to_image(pdf_path, i, dpi=dpi))
    images_to_pdf(images, output_path)


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
