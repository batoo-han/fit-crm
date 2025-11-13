import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useModal } from '../components/ui/modal/ModalContext'

type Pipeline = {
  id: number
  name: string
  description?: string | null
  is_enabled: boolean
  params?: Record<string, unknown> | null
}

const Pipelines = () => {
  const queryClient = useQueryClient()
  const { showModal } = useModal()
  const [editing, setEditing] = useState<Pipeline | null>(null)
  const [form, setForm] = useState<Pipeline | null>(null as unknown as Pipeline)
  const [assignMode, setAssignMode] = useState(false)
  const [selectedPipelineId, setSelectedPipelineId] = useState<number | ''>('')

  const { data: pipelines, isLoading, isError } = useQuery({
    queryKey: ['pipelines'],
    queryFn: async () => {
      const response = await api.get('/pipelines')
      return response.data as Pipeline[]
    },
  })

  type Stage = {
    id: number
    name: string
    order: number
    color: string
    description?: string
    is_active: boolean
    pipeline_id?: number | null
  }

  const { data: stages } = useQuery({
    queryKey: ['pipeline-stages'],
    queryFn: async () => {
      const res = await api.get('/pipeline/stages?include_inactive=true')
      return res.data as Stage[]
    },
  })

  const updateStageMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Partial<Stage> }) => {
      const res = await api.put(`/pipeline/stages/${id}`, payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-stages'] })
    },
  })

  const createMutation = useMutation({
    mutationFn: async (payload: Partial<Pipeline>) => {
      const response = await api.post('/pipelines', {
        name: payload.name,
        description: payload.description,
        is_enabled: payload.is_enabled ?? true,
        params: payload.params ?? null,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
      setEditing(null)
      setForm(null as unknown as Pipeline)
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Partial<Pipeline> }) => {
      const response = await api.put(`/pipelines/${id}`, {
        name: payload.name,
        description: payload.description,
        is_enabled: payload.is_enabled ?? true,
        params: payload.params ?? null,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
      setEditing(null)
      setForm(null as unknown as Pipeline)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/pipelines/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
    },
  })

  const startCreate = () => {
    setEditing({ id: 0, name: '', description: '', is_enabled: true, params: {} })
    setForm({ id: 0, name: '', description: '', is_enabled: true, params: {} })
  }

  const startEdit = (p: Pipeline) => {
    setEditing(p)
    setForm({
      ...p,
      params: p.params || {},
    })
  }

  const cancelEdit = () => {
    setEditing(null)
    setForm(null as unknown as Pipeline)
  }

  const onSubmit = () => {
    if (!form?.name || form.name.trim().length === 0) {
      showModal({
        title: 'Название воронки',
        message: 'Название воронки обязательно',
        tone: 'error',
      })
      return
    }
    const payload = {
      name: form.name.trim(),
      description: form.description || '',
      is_enabled: !!form.is_enabled,
      params: form.params || {},
    }
    if (editing && editing.id > 0) {
      updateMutation.mutate({ id: editing.id, payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  const toggleEnabled = (p: Pipeline) => {
    updateMutation.mutate({
      id: p.id,
      payload: { ...p, is_enabled: !p.is_enabled },
    })
  }

  const parseParams = (value: string) => {
    try {
      if (value.trim() === '') return {}
      return JSON.parse(value)
    } catch {
      showModal({
        title: 'Некорректный формат',
        message: 'Параметры должны быть корректным JSON',
        tone: 'error',
      })
      return form?.params || {}
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Воронки продаж</h1>
        <p className="text-gray-500 mt-2">
          Управляйте несколькими воронками: название, описание, параметры и включение/выключение.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Список воронок</h2>
          <button
            onClick={startCreate}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            + Новая воронка
          </button>
        </div>

        {isLoading && <p>Загрузка...</p>}
        {isError && <p className="text-red-600">Ошибка загрузки</p>}

        {!isLoading && !isError && (
          <div className="divide-y border border-gray-200 rounded-lg">
            {(pipelines || []).map((p) => (
              <div key={p.id} className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-900">{p.name}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        p.is_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-600'
                      }`}
                    >
                      {p.is_enabled ? 'Включена' : 'Выключена'}
                    </span>
                  </div>
                  {p.description && <p className="text-gray-600 text-sm mt-1">{p.description}</p>}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleEnabled(p)}
                    className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
                  >
                    {p.is_enabled ? 'Отключить' : 'Включить'}
                  </button>
                  <button
                    onClick={() => startEdit(p)}
                    className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
                  >
                    Редактировать
                  </button>
                  <button
                    onClick={() => {
                      if (!confirm('Удалить воронку? Если есть этапы/история, удаление запрещено.')) return
                      deleteMutation.mutate(p.id)
                    }}
                    className="px-3 py-1 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 text-sm"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            ))}
            {pipelines && pipelines.length === 0 && (
              <div className="p-4 text-gray-500">Воронки ещё не созданы</div>
            )}
          </div>
        )}
      </div>

      {/* Привязка этапов к воронкам */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Привязка этапов к воронкам</h2>
          <div className="flex items-center gap-2">
            <select
              value={selectedPipelineId}
              onChange={(e) => setSelectedPipelineId(e.target.value ? parseInt(e.target.value) : '')}
              className="px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="">Default (общая)</option>
              {(pipelines || []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => setAssignMode((v) => !v)}
              className={`px-4 py-2 rounded-lg ${
                assignMode ? 'bg-amber-600 text-white' : 'bg-gray-200 text-gray-800'
              }`}
            >
              {assignMode ? 'Режим назначения включён' : 'Назначить этапы'}
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Порядок</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Этап</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Текущая воронка</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {(stages || []).map((s) => {
                const current = (pipelines || []).find((p) => p.id === s.pipeline_id)
                return (
                  <tr key={s.id}>
                    <td className="px-4 py-2 text-sm text-gray-700">{s.order}</td>
                    <td className="px-4 py-2 text-sm text-gray-900">{s.name}</td>
                    <td className="px-4 py-2 text-sm text-gray-700">{current ? current.name : 'Default'}</td>
                    <td className="px-4 py-2 text-sm text-right">
                      <button
                        disabled={!assignMode}
                        onClick={() =>
                          updateStageMutation.mutate({
                            id: s.id,
                            payload: { pipeline_id: selectedPipelineId === '' ? null : Number(selectedPipelineId) },
                          })
                        }
                        className={`px-3 py-1 rounded-lg border ${
                          assignMode ? 'border-gray-300 hover:bg-gray-100' : 'border-gray-200 text-gray-400'
                        }`}
                      >
                        Назначить выбранную
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {editing && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            {editing.id > 0 ? 'Редактирование воронки' : 'Новая воронка'}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Название *</label>
              <input
                type="text"
                value={form?.name || ''}
                onChange={(e) => setForm({ ...(form as Pipeline), name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Включена</label>
              <input
                type="checkbox"
                checked={!!form?.is_enabled}
                onChange={(e) => setForm({ ...(form as Pipeline), is_enabled: e.target.checked })}
              />{' '}
              <span className="text-sm text-gray-700">Активна</span>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
              <textarea
                rows={2}
                value={form?.description || ''}
                onChange={(e) => setForm({ ...(form as Pipeline), description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Параметры (JSON)</label>
              <textarea
                rows={6}
                value={JSON.stringify(form?.params || {}, null, 2)}
                onChange={(e) =>
                  setForm({
                    ...(form as Pipeline),
                    params: parseParams(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={onSubmit}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {editing.id > 0 ? 'Сохранить' : 'Создать'}
            </button>
            <button onClick={cancelEdit} className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100">
              Отмена
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Pipelines


