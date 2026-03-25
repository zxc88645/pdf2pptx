// @paddlejs-models/ocr 內嵌的 OpenCV/Emscripten 會執行 `typeof Module`；
// 在 ESM 嚴格模式下，未宣告的全域 `Module` 會拋 ReferenceError。
// 必須在任何載入 OCR 的 import 之前執行。
if (typeof globalThis.Module === 'undefined') {
  globalThis.Module = {}
}
