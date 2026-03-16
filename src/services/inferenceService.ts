import * as ort from 'onnxruntime-web'
import { loadImageFromDataUrl, getImageDataFromImage, resizeImageData, imageDataToDataUrl } from '../utils/image'
import { imageDataToCHWTensor, maskToTensor, tensorToImageData } from '../utils/tensor'

const DEFAULT_MODEL_URL = '/models/migan_pipeline_v2.onnx'
const MODEL_SIZE = 512

let session: ort.InferenceSession | null = null
let initializing: Promise<ort.InferenceSession> | null = null

function summarizeMask(mask: ImageData) {
  const { width, height, data } = mask
  const size = width * height
  let nonZeroAlpha = 0

  for (let i = 0; i < size; i++) {
    const a = data[i * 4 + 3]
    if (a > 0) nonZeroAlpha++
  }

  const ratio = nonZeroAlpha / size

  console.log('[inference] mask summary', {
    width,
    height,
    nonZeroPixels: nonZeroAlpha,
    totalPixels: size,
    ratio,
  })
}

function summarizeTensor(tensor: ort.Tensor, label: string) {
  const data = tensor.data as Float32Array | number[]
  let min = Number.POSITIVE_INFINITY
  let max = Number.NEGATIVE_INFINITY
  let sum = 0
  const len = data.length

  for (let i = 0; i < len; i++) {
    const v = data[i] as number
    if (v < min) min = v
    if (v > max) max = v
    sum += v
  }

  const mean = len > 0 ? sum / len : 0

  console.log('[inference] tensor summary', {
    label,
    dims: tensor.dims,
    dtype: tensor.type,
    min,
    max,
    mean,
  })
}

async function createSessionWithProviders(
  modelUrl: string,
  executionProviders: ort.InferenceSession.SessionOptions['executionProviders'],
): Promise<ort.InferenceSession> {
  console.log('[inference] Trying executionProviders', executionProviders)
  const s = await ort.InferenceSession.create(modelUrl, {
    executionProviders,
  })

  console.log('[inference] ONNX session created', {
    requestedExecutionProviders: executionProviders,
    sessionHasExecutionProvidersField: 'executionProviders' in s,
    executionProviders: (s as any).executionProviders,
  })

  return s
}

export async function initSession(modelUrl: string = DEFAULT_MODEL_URL): Promise<ort.InferenceSession> {
  if (session) return session
  if (initializing) return initializing

  const hasWebGPU = typeof navigator !== 'undefined' && 'gpu' in navigator
  const tryExecutionProviders: ort.InferenceSession.SessionOptions['executionProviders'][] = []

  if (hasWebGPU) {
    tryExecutionProviders.push(['webgpu'])
  }
  tryExecutionProviders.push(['wasm'])

  console.log('[inference] Initializing ONNX session', {
    modelUrl,
    navigatorHasWebGPU: hasWebGPU,
    tryExecutionProviders,
  })
  initializing = (async () => {
    let lastError: unknown = null

    for (const eps of tryExecutionProviders) {
      try {
        const s = await createSessionWithProviders(modelUrl, eps)
        session = s
        return s
      } catch (e) {
        console.error('[inference] Failed to create session with providers', eps, e)
        lastError = e
      }
    }

    throw lastError ?? new Error('Failed to create ONNX session with all providers')
  })()

  return initializing
}

export interface InpaintingOptions {
  modelUrl?: string
}

export async function runInpainting(
  originalImageDataUrl: string,
  maskImageData: ImageData,
  options: InpaintingOptions = {},
): Promise<string> {
  console.log('[inference] runInpainting received inputs', {
    originalImageDataUrlLength: originalImageDataUrl.length,
    maskSize: {
      width: maskImageData.width,
      height: maskImageData.height,
    },
  })

  summarizeMask(maskImageData)

  let s = await initSession(options.modelUrl)

  const start = performance.now()
  console.log('[inference] runInpainting start', {
    executionProviders: (s as any).executionProviders,
  })

  const img = await loadImageFromDataUrl(originalImageDataUrl)
  const imageData = getImageDataFromImage(img, MODEL_SIZE, MODEL_SIZE)
  const resizedMask = resizeImageData(maskImageData, MODEL_SIZE, MODEL_SIZE)

  console.log('[inference] resized inputs', {
    imageData: { width: imageData.width, height: imageData.height },
    resizedMask: { width: resizedMask.width, height: resizedMask.height },
  })

  const imageTensor = imageDataToCHWTensor(imageData)
  const maskTensor = maskToTensor(resizedMask)

  summarizeTensor(imageTensor, 'image')
  summarizeTensor(maskTensor, 'mask')

  const feeds: Record<string, ort.Tensor> = {}
  const [firstInput, secondInput] = s.inputNames

  if (!firstInput || !secondInput) {
    throw new Error('Unexpected model inputs')
  }

  feeds[firstInput] = imageTensor
  feeds[secondInput] = maskTensor

  let results: Record<string, ort.Tensor>
  try {
    results = await s.run(feeds)
  } catch (e) {
    console.error('[inference] runInpainting failed on current providers, will try fallback', {
      executionProviders: (s as any).executionProviders,
      error: e,
    })

    // 如果目前是 WebGPU，嘗試改建 WASM session 再跑一次
    const currentProviders = (s as any).executionProviders as string[] | undefined
    const isWebGPU =
      currentProviders?.includes('webgpu') ||
      (!currentProviders && typeof navigator !== 'undefined' && 'gpu' in navigator)

    if (isWebGPU) {
      console.log('[inference] Recreating session with WASM for fallback')
      session = await createSessionWithProviders(options.modelUrl ?? DEFAULT_MODEL_URL, ['wasm'])
      s = session
      results = await s.run(feeds)
    } else {
      throw e
    }
  }
  const end = performance.now()
  console.log('[inference] runInpainting end', {
    executionProviders: (s as any).executionProviders,
    durationMs: end - start,
  })

  const firstOutputName = s.outputNames[0]
  const outputTensor = results[firstOutputName]
  if (!outputTensor) {
    throw new Error('Model did not return output tensor')
  }

  summarizeTensor(outputTensor, 'output')

  const outputImageData = tensorToImageData(outputTensor as ort.Tensor)
  return imageDataToDataUrl(outputImageData)
}

