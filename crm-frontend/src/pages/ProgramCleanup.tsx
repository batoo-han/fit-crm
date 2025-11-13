import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../services/api'
import { useModal } from '../components/ui/modal/ModalContext'

interface CleanupStats {
  archived: number
  deleted: number
  skipped: number
  errors: string[]
}

export default function ProgramCleanup() {
  const { showModal } = useModal()
  const [formData, setFormData] = useState({
    days_old: 30,
    archive_sent: true,
    delete_unsent: true,
    dry_run: true
  })
  const [lastResult, setLastResult] = useState<CleanupStats | null>(null)

  const cleanupMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const response = await api.post('/programs/cleanup', data)
      return response.data as CleanupStats
    },
    onSuccess: (data) => {
      setLastResult(data)
      if (formData.dry_run) {
        showModal({
          title: 'Предварительный просмотр',
          message: `Будет архивировано: ${data.archived}\nБудет удалено: ${data.deleted}\nПропущено: ${data.skipped}${data.errors.length > 0 ? `\n\nОшибки: ${data.errors.join(', ')}` : ''}`,
          tone: 'info'
        })
      } else {
        showModal({
          title: 'Очистка завершена',
          message: `Архивировано: ${data.archived}\nУдалено: ${data.deleted}\nПропущено: ${data.skipped}${data.errors.length > 0 ? `\n\nОшибки: ${data.errors.join(', ')}` : ''}`,
          tone: 'success'
        })
      }
    },
    onError: (error: any) => {
      showModal({
        title: 'Ошибка',
        message: error?.response?.data?.detail || 'Не удалось выполнить очистку',
        tone: 'error'
      })
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    cleanupMutation.mutate(formData)
  }

  const handleExecute = () => {
    showModal({
      title: 'Подтверждение очистки',
      message: 'Вы уверены, что хотите выполнить очистку? Это действие нельзя отменить.',
      tone: 'warning',
      actions: [
        {
          label: 'Отмена',
          variant: 'secondary',
        },
        {
          label: 'Выполнить',
          variant: 'primary',
          onClick: () => {
            cleanupMutation.mutate({ ...formData, dry_run: false })
          },
        },
      ],
    })
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Очистка программ</h1>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
        <h2 className="font-semibold text-yellow-800 mb-2">Как работает очистка:</h2>
        <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
          <li>Программы, которые были отправлены клиентам, архивируются в историю</li>
          <li>Программы, которые никогда не отправлялись и не привязаны к клиентам, удаляются</li>
          <li>Программы, привязанные к активным клиентам, не удаляются, даже если не были отправлены</li>
          <li>Обрабатываются только программы старше указанного количества дней</li>
        </ul>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Программы старше (дней)
            </label>
            <input
              type="number"
              min="1"
              value={formData.days_old}
              onChange={(e) => setFormData({ ...formData, days_old: parseInt(e.target.value) || 30 })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.archive_sent}
                onChange={(e) => setFormData({ ...formData, archive_sent: e.target.checked })}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">Архивировать отправленные программы</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.delete_unsent}
                onChange={(e) => setFormData({ ...formData, delete_unsent: e.target.checked })}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">Удалять неотправленные программы (не привязанные к клиентам)</span>
            </label>
          </div>

          <div className="flex space-x-2">
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              disabled={cleanupMutation.isPending}
            >
              Предварительный просмотр
            </button>
            {lastResult && formData.dry_run && (
              <button
                type="button"
                onClick={handleExecute}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
                disabled={cleanupMutation.isPending}
              >
                Выполнить очистку
              </button>
            )}
          </div>
        </div>
      </form>

      {lastResult && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Результаты {formData.dry_run ? '(предварительный просмотр)' : ''}</h2>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{lastResult.archived}</div>
              <div className="text-sm text-gray-600">Архивировано</div>
            </div>
            <div className="bg-red-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-red-600">{lastResult.deleted}</div>
              <div className="text-sm text-gray-600">Удалено</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-gray-600">{lastResult.skipped}</div>
              <div className="text-sm text-gray-600">Пропущено</div>
            </div>
          </div>
          {lastResult.errors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="font-semibold text-red-800 mb-2">Ошибки:</h3>
              <ul className="list-disc list-inside text-sm text-red-700">
                {lastResult.errors.map((error, idx) => (
                  <li key={idx}>{error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

