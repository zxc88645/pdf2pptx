import io
from pathlib import Path
from typing import List, Union

from pptx import Presentation
from pptx.util import Mm
from PIL import Image

# 投影片版面：485 × 271 公釐（橫向）
SLIDE_WIDTH_MM = 485
SLIDE_HEIGHT_MM = 271


def images_to_pptx(images: List[Union[Image.Image, bytes]], output_path: Path) -> None:
    """將多張圖片組合成 PPTX，每圖一頁。版面 485×271 mm 橫向、無邊距。"""
    prs = Presentation()
    prs.slide_width = Mm(SLIDE_WIDTH_MM)
    prs.slide_height = Mm(SLIDE_HEIGHT_MM)
    blank = prs.slide_layouts[6]  # blank

    for img in images:
        if isinstance(img, Image.Image):
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            img_bytes = buf.read()
        else:
            img_bytes = img
        slide = prs.slides.add_slide(blank)
        # 無邊距：圖片填滿整張投影片
        slide.shapes.add_picture(
            io.BytesIO(img_bytes),
            Mm(0), Mm(0),
            width=prs.slide_width,
            height=prs.slide_height,
        )
    prs.save(str(output_path))
