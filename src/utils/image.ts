export async function loadImageFromDataUrl(dataUrl: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = (e) => reject(e)
    img.src = dataUrl
  })
}

export function getImageDataFromImage(
  image: HTMLImageElement,
  width: number,
  height: number,
): ImageData {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    throw new Error('Cannot get 2D context')
  }
  ctx.drawImage(image, 0, 0, width, height)
  return ctx.getImageData(0, 0, width, height)
}

export function resizeImageData(source: ImageData, width: number, height: number): ImageData {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    throw new Error('Cannot get 2D context')
  }
  // put original then draw scaled
  const tmp = document.createElement('canvas')
  tmp.width = source.width
  tmp.height = source.height
  const tmpCtx = tmp.getContext('2d')
  if (!tmpCtx) {
    throw new Error('Cannot get 2D context')
  }
  tmpCtx.putImageData(source, 0, 0)
  ctx.drawImage(tmp, 0, 0, width, height)
  return ctx.getImageData(0, 0, width, height)
}

export async function imageDataToDataUrl(imageData: ImageData): Promise<string> {
  const canvas = document.createElement('canvas')
  canvas.width = imageData.width
  canvas.height = imageData.height
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    throw new Error('Cannot get 2D context')
  }
  ctx.putImageData(imageData, 0, 0)
  return canvas.toDataURL('image/png')
}

