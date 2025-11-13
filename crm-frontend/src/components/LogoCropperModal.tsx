import { useState, useCallback } from 'react'
import Cropper, { Area } from 'react-easy-crop'

interface LogoCropperModalProps {
  imageSrc: string
  onCancel: () => void
  onConfirm: (croppedBlob: Blob) => void
  aspect?: number
}

const createImage = (url: string): Promise<HTMLImageElement> =>
  new Promise((resolve, reject) => {
    const image = new Image()
    image.addEventListener('load', () => resolve(image))
    image.addEventListener('error', (error) => reject(error))
    image.setAttribute('crossOrigin', 'anonymous')
    image.src = url
  })

const getCroppedImage = async (imageSrc: string, croppedAreaPixels: Area) => {
  const image = await createImage(imageSrc)
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')

  if (!ctx) {
    throw new Error('Не удалось создать canvas контекст для обрезки изображения')
  }

  const { width, height, x, y } = croppedAreaPixels
  canvas.width = width
  canvas.height = height

  ctx.drawImage(image, x, y, width, height, 0, 0, width, height)

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob)
        } else {
          reject(new Error('Не удалось получить Blob после обрезки изображения'))
        }
      },
      'image/png',
      0.95
    )
  })
}

export const LogoCropperModal = ({
  imageSrc,
  onCancel,
  onConfirm,
  aspect = 1,
}: LogoCropperModalProps) => {
  const [crop, setCrop] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const handleCropComplete = useCallback((_: Area, croppedPixels: Area) => {
    setCroppedAreaPixels(croppedPixels)
  }, [])

  const handleConfirm = async () => {
    if (!croppedAreaPixels) return
    try {
      setIsProcessing(true)
      const croppedBlob = await getCroppedImage(imageSrc, croppedAreaPixels)
      onConfirm(croppedBlob)
    } catch (error) {
      console.error('Ошибка обрезки логотипа', error)
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 px-4">
      <div className="relative w-full max-w-3xl rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-900">Обрезка логотипа</h3>
          <button
            onClick={onCancel}
            className="text-gray-500 transition hover:text-gray-700"
            type="button"
          >
            ✕
          </button>
        </div>

        <div className="relative h-[420px] w-full bg-gray-900">
          <Cropper
            image={imageSrc}
            crop={crop}
            zoom={zoom}
            aspect={aspect}
            showGrid={false}
            onCropChange={setCrop}
            onCropComplete={handleCropComplete}
            onZoomChange={setZoom}
            objectFit="contain"
            restrictPosition
          />
        </div>

        <div className="space-y-4 px-6 py-5">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Масштаб
            </label>
            <input
              type="range"
              min={1}
              max={3}
              step={0.1}
              value={zoom}
              onChange={(event) => setZoom(Number(event.target.value))}
              className="w-full"
            />
          </div>

          <p className="text-sm text-gray-500">
            Перемещайте изображение и рамку, чтобы подобрать нужную область. Все, что
            остается вне рамки, будет обрезано. Формат итогового изображения — квадрат,
            идеально подходящий для аватара виджета.
          </p>

          <div className="flex justify-end gap-3 border-t border-gray-200 pt-4">
            <button
              onClick={onCancel}
              type="button"
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100"
              disabled={isProcessing}
            >
              Отменить
            </button>
            <button
              onClick={handleConfirm}
              type="button"
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-primary-700 disabled:opacity-60"
              disabled={isProcessing}
            >
              {isProcessing ? 'Сохранение...' : 'Сохранить обрезку'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LogoCropperModal

