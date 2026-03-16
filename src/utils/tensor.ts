import * as ort from 'onnxruntime-web'

// 注意：目前的 MiGAN ONNX 模型期望輸入為 tensor(uint8)，
// 因此這裡直接建立 uint8 NCHW tensor（不做 0~1 正規化）。
export function imageDataToCHWTensor(imageData: ImageData): ort.Tensor {
  const { width, height, data } = imageData
  const size = width * height
  const uint8Data = new Uint8Array(3 * size)

  for (let i = 0; i < size; i++) {
    const r = data[i * 4]
    const g = data[i * 4 + 1]
    const b = data[i * 4 + 2]
    const base = i
    uint8Data[base] = r
    uint8Data[base + size] = g
    uint8Data[base + 2 * size] = b
  }

  return new ort.Tensor('uint8', uint8Data, [1, 3, height, width])
}

export function maskToTensor(mask: ImageData): ort.Tensor {
  const { width, height, data } = mask
  const size = width * height
  const uint8Data = new Uint8Array(size)

  for (let i = 0; i < size; i++) {
    const a = data[i * 4 + 3]
    // 這裡的約定改成：
    // - alpha > 0（有塗遮罩的地方） => 0：讓模型在這裡進行修補 / 抹除
    // - alpha = 0（沒有塗遮罩的地方） => 255：保留原圖
    //
    // 原本的邏輯是 alpha > 0 給 255，導致「有塗的地方被保留、其他地方被抹除」，
    // 與一般 inpainting 工具的直覺相反，因此在這裡反轉。
    uint8Data[i] = a > 0 ? 0 : 255
  }

  return new ort.Tensor('uint8', uint8Data, [1, 1, height, width])
}

export function tensorToImageData(tensor: ort.Tensor): ImageData {
  const [n, c, h, w] = tensor.dims
  if (n !== 1 || (c !== 3 && c !== 4)) {
    throw new Error(`Unsupported tensor shape: [${tensor.dims.join(', ')}]`)
  }

  const data = tensor.data as Float32Array
  const imageData = new ImageData(w, h)
  const size = w * h

   // 檢查模型輸出的數值範圍：
   // - 若在 [0, 1]，視為已正規化
   // - 若在 [0, 255]，先除以 255 再轉成 imageData
   let min = Number.POSITIVE_INFINITY
   let max = Number.NEGATIVE_INFINITY
   const len = data.length
   for (let i = 0; i < len; i++) {
     const v = data[i]
     if (v < min) min = v
     if (v > max) max = v
   }

   // 預設假設模型輸出是 0~1
   let modelScale = 1
   if (max > 1.5) {
     // 偵測到像是 0~255 的範圍，先縮回 0~1
     modelScale = 1 / 255
     console.log('[tensor] tensorToImageData detected 0-255 range, applying /255 normalization', {
       min,
       max,
     })
   }

  for (let i = 0; i < size; i++) {
    const r = data[i] * modelScale
    const g = data[i + size] * modelScale
    const b = data[i + 2 * size] * modelScale
    imageData.data[i * 4] = Math.max(0, Math.min(255, Math.round(r * 255)))
    imageData.data[i * 4 + 1] = Math.max(0, Math.min(255, Math.round(g * 255)))
    imageData.data[i * 4 + 2] = Math.max(0, Math.min(255, Math.round(b * 255)))
    imageData.data[i * 4 + 3] = 255
  }

  return imageData
}

