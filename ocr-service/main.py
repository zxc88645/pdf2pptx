"""OCR service: FastAPI + PaddleOCR, POST /ocr returns bbox + text."""
import io
import os
import tempfile
from typing import Any, List

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from paddleocr import PaddleOCR
from PIL import Image

app = FastAPI(title="OCR Service", version="0.1.0")

# PaddleOCR 3.x: device 取代 use_gpu；use_textline_orientation 對應 2.x 的 use_angle_cls
use_gpu = os.getenv("USE_GPU", "true").lower() == "true"
ocr_engine = PaddleOCR(
    device="gpu" if use_gpu else "cpu",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=True,
)


def _parse_ocr_result_2x(raw: List[Any], min_score: float | None = None) -> List[dict]:
    """2.x 格式: 每項為 [box, (text, conf)]，可選擇依 conf 過濾。"""
    results = []
    for item in raw:
        if not item or len(item) < 2:
            continue
        box, (text, _conf) = item[0], item[1]
        try:
            conf = float(_conf)
        except Exception:
            conf = None
        if min_score is not None and conf is not None and conf < min_score:
            continue
        results.append({"bbox": box, "text": text, "confidence": conf})
    return results


def _parse_ocr_result_3x(res: Any, min_score: float | None = None) -> List[dict]:
    """3.x 格式: 每個 res 為 pipeline 結果物件或 dict，包含 dt_polys / rec_texts / rec_scores."""
    # 先處理 dict 形式
    if isinstance(res, dict):
        dt_polys = res.get("dt_polys")
        rec_texts = res.get("rec_texts")
        rec_scores = res.get("rec_scores")
    else:
        # 3.x 常見屬性：dt_polys（框）、rec_texts（文字）
        dt_polys = getattr(res, "dt_polys", None)
        rec_texts = getattr(res, "rec_texts", None)
        rec_scores = getattr(res, "rec_scores", None)

    if dt_polys is not None and rec_texts is not None:
        n = min(len(dt_polys), len(rec_texts))
        results: List[dict] = []
        for i in range(n):
            # dt_polys 可能是 numpy 陣列（包含 numpy.int16），需轉成純 Python list 才能 JSON 序列化
            bbox = np.asarray(dt_polys[i]).tolist()
            text = rec_texts[i]
            score = None
            if rec_scores is not None and i < len(rec_scores):
                try:
                    score = float(rec_scores[i])
                except Exception:
                    score = None
            if min_score is not None and score is not None and score < min_score:
                continue
            results.append({"bbox": bbox, "text": text, "confidence": score})
        return results
    # 若為可迭代且每項為 [box, (text, conf)]（相容 2.x 單圖結構）
    try:
        raw = list(res) if not isinstance(res, list) else res
        return _parse_ocr_result_2x(raw, min_score=min_score)
    except (TypeError, ValueError):
        pass
    return []


def _run_ocr(img_array, min_score: float | None = None) -> List[dict]:
    """執行 OCR，相容 2.x / 3.x 回傳格式。3.x 的 predict 多接受路徑，故先寫入暫存檔。"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        try:
            Image.fromarray(img_array).save(f.name)
            # 3.x 使用 predict(input=...)
            result = ocr_engine.predict(input=f.name)
        finally:
            try:
                os.unlink(f.name)
            except OSError:
                pass
    if not result:
        return []
    # 單張圖時 result 為一元素列表
    first = result[0]
    # 3.x: first 為結果物件（有 .dt_polys / .rec_texts / .print 等）
    if hasattr(first, "dt_polys") or hasattr(first, "rec_texts") or isinstance(first, dict):
        return _parse_ocr_result_3x(first, min_score=min_score)
    # 2.x 或 3.x 回傳 list of [box, (text, conf)]
    if isinstance(first, list):
        return _parse_ocr_result_2x(first, min_score=min_score)
    return _parse_ocr_result_3x(first, min_score=min_score)


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


@app.post("/ocr")
def ocr(
    image: UploadFile = File(...),
    text_only: bool = False,
    min_score: float | None = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum recognition score [0-1]; lower results will be filtered out.",
    ),
):
    """
    Accept a single image (form field 'image'), run OCR, return JSON:
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
    img_array = np.array(img)
    results = _run_ocr(img_array, min_score=min_score)
    if text_only:
        lines = [str(r.get("text", "")) for r in results if r.get("text")]
        return {"text": "\n".join(lines), "lines": lines}
    return {"results": results, "text": "\n".join([str(r.get("text", "")) for r in results if r.get("text")])}
