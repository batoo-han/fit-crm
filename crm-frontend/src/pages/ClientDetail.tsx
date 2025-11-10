import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

interface Client {
  id: number
  first_name: string
  last_name?: string
  telegram_username?: string
  phone_number?: string
  age?: number
  gender?: string
  height?: number
  weight?: number
  bmi?: string
  pipeline_stage_id?: number | null
  status?: string
}

const ClientDetail = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState<Partial<Client>>({})

  const { data: client, isLoading } = useQuery<Client>({
    queryKey: ['client', id],
    queryFn: async () => {
      const response = await api.get(`/clients/${id}`)
      return response.data
    },
  })

  useEffect(() => {
    if (client) {
      setFormData(client)
    }
  }, [client])

  const { data: programs } = useQuery({
    queryKey: ['client-programs', id],
    queryFn: async () => {
      const response = await api.get(`/programs?client_id=${id}`)
      return response.data
    },
  })

  const { data: payments } = useQuery({
    queryKey: ['client-payments', id],
    queryFn: async () => {
      const response = await api.get(`/clients/${id}/payments`)
      return response.data
    },
  })

  const { data: stages } = useQuery({
    queryKey: ['pipeline-stages'],
    queryFn: async () => {
      const response = await api.get('/pipeline/stages')
      return response.data
    },
  })

  // Локальный выбор этапа с явным сохранением
  const [pendingStageId, setPendingStageId] = useState<number | ''>('')
  const [initialStageId, setInitialStageId] = useState<number | ''>('')

  useEffect(() => {
    if (client && client.pipeline_stage_id !== undefined) {
      const stageId = client.pipeline_stage_id || ''
      setInitialStageId(stageId)
      setPendingStageId(stageId)
    }
  }, [client])

  const { data: pipelineHistory } = useQuery({
    queryKey: ['client-pipeline-history', id],
    queryFn: async () => {
      const response = await api.get(`/clients/${id}/pipeline-history`)
      return response.data
    },
  })

  const moveToStageMutation = useMutation({
    mutationFn: async (stageId: number) => {
      const response = await api.post(`/pipeline/clients/${id}/move-stage`, {
        stage_id: stageId,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['client', id] })
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      queryClient.invalidateQueries({ queryKey: ['client-pipeline-history', id] })
      setInitialStageId(pendingStageId || '')
    },
  })

  const updateMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.put(`/clients/${id}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['client', id] })
      setIsEditing(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (clientId: number) => {
      await api.delete(`/clients/${clientId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      navigate('/clients')
    },
  })

  const handleSave = () => {
    updateMutation.mutate(formData)
  }

  if (isLoading) {
    return <div>Загрузка...</div>
  }

  if (!client) {
    return <div>Клиент не найден</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <button
            onClick={() => navigate('/clients')}
            className="text-gray-600 hover:text-gray-900 mb-4"
          >
            ← Назад к списку
          </button>
          <h1 className="text-3xl font-bold text-gray-900">
            {client.first_name} {client.last_name || ''}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            ID клиента: <span className="font-mono">{client.id}</span>
          </p>
        </div>
        <div className="flex gap-2">
          {isEditing ? (
            <>
              <button
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Отмена
              </button>
              <button
                onClick={handleSave}
                disabled={updateMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {updateMutation.isPending ? 'Сохранение...' : 'Сохранить'}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setIsEditing(true)}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                Редактировать
              </button>
              <button
                onClick={() => {
                  if (confirm('Вы уверены, что хотите удалить этого клиента? Это действие нельзя отменить.')) {
                    deleteMutation.mutate(parseInt(id!))
                  }
                }}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Удаление...' : 'Удалить'}
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Основная информация */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Основная информация</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Имя
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    value={formData.first_name || ''}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                ) : (
                  <p className="text-gray-900">{client.first_name || 'Не указано'}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Фамилия
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    value={formData.last_name || ''}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                ) : (
                  <p className="text-gray-900">{client.last_name || 'Не указано'}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Телеграм
                </label>
                <p className="text-gray-900">@{client.telegram_username || 'не указан'}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Телефон
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    value={formData.phone_number || ''}
                    onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                ) : (
                  <p className="text-gray-900">{client.phone_number || 'Не указан'}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Возраст
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    value={formData.age || ''}
                    onChange={(e) => setFormData({ ...formData, age: parseInt(e.target.value) || null })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                ) : (
                  <p className="text-gray-900">{client.age ? `${client.age} лет` : 'Не указан'}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Пол
                </label>
                {isEditing ? (
                  <select
                    value={formData.gender || ''}
                    onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="">Не указан</option>
                    <option value="мужской">Мужской</option>
                    <option value="женский">Женский</option>
                  </select>
                ) : (
                  <p className="text-gray-900">{client.gender || 'Не указан'}</p>
                )}
              </div>
            </div>
          </div>

          {/* Физические параметры */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Физические параметры</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Рост (см)
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    value={formData.height || ''}
                    onChange={(e) => setFormData({ ...formData, height: parseInt(e.target.value) || null })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                ) : (
                  <p className="text-gray-900">{client.height ? `${client.height} см` : 'Не указан'}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Вес (кг)
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    step="0.1"
                    value={formData.weight || ''}
                    onChange={(e) => setFormData({ ...formData, weight: parseFloat(e.target.value) || null })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                ) : (
                  <p className="text-gray-900">{client.weight ? `${client.weight} кг` : 'Не указан'}</p>
                )}
              </div>
              {client.bmi && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    ИМТ
                  </label>
                  <p className="text-gray-900">{client.bmi}</p>
                </div>
              )}
            </div>
          </div>

          {/* Программы */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Программы тренировок</h2>
            {programs && programs.length > 0 ? (
              <div className="space-y-2">
                {programs.map((program: any) => (
                  <div
                    key={program.id}
                    className="flex justify-between items-center p-3 border border-gray-200 rounded-lg"
                  >
                    <div>
                      <p className="font-medium">{program.program_type}</p>
                      <p className="text-sm text-gray-500">
                        {new Date(program.created_at).toLocaleDateString('ru-RU')}
                      </p>
                    </div>
                    <Link
                      to={`/programs/${program.id}`}
                      className="text-primary-600 hover:text-primary-700"
                    >
                      Просмотр →
                    </Link>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">Нет программ</p>
            )}
          </div>

          {/* Дневник параметров */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Дневник параметров</h2>
            <Link
              to={`/progress/${id}`}
              className="text-primary-600 hover:text-primary-700"
            >
              Просмотр дневника →
            </Link>
          </div>
        </div>

        {/* Боковая панель */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Воронка продаж</h2>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Текущий этап
              </label>
              {stages && (initialStageId || client.pipeline_stage_id) ? (
                <div className="flex items-center gap-2 mb-4">
                  {(() => {
                    const currentId = pendingStageId || client.pipeline_stage_id
                    const currentStage = stages.find((s: any) => s.id === currentId)
                    return currentStage ? (
                      <>
                        <div
                          className="w-4 h-4 rounded-full"
                          style={{ backgroundColor: currentStage.color }}
                        />
                        <span className="font-semibold text-gray-900">{currentStage.name}</span>
                      </>
                    ) : (
                      <span className="text-gray-500">Этап не назначен</span>
                    )
                  })()}
                </div>
              ) : (
                <p className="text-gray-500 mb-4">Этап не назначен</p>
              )}
              <select
                value={pendingStageId || ''}
                onChange={(e) => {
                  const stageId = e.target.value ? parseInt(e.target.value) : ''
                  setPendingStageId(stageId)
                }}
                disabled={moveToStageMutation.isPending}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">Выберите этап...</option>
                {stages?.map((stage: any) => (
                  <option key={stage.id} value={stage.id}>
                    {stage.name}
                  </option>
                ))}
              </select>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={() => {
                    setPendingStageId(initialStageId)
                  }}
                  disabled={moveToStageMutation.isPending}
                  className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Отмена
                </button>
                <button
                  onClick={() => {
                    if (typeof pendingStageId === 'number') {
                      moveToStageMutation.mutate(pendingStageId)
                    }
                  }}
                  disabled={moveToStageMutation.isPending || pendingStageId === initialStageId}
                  className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {moveToStageMutation.isPending ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </div>
            
            {/* История перемещений */}
            {pipelineHistory && pipelineHistory.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-medium text-gray-700 mb-3">История перемещений</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {pipelineHistory.map((entry: any) => (
                    <div
                      key={entry.id}
                      className="flex items-start gap-2 text-sm p-2 bg-gray-50 rounded"
                    >
                      <div
                        className="w-3 h-3 rounded-full mt-1 flex-shrink-0"
                        style={{ backgroundColor: entry.stage_color }}
                      />
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{entry.stage_name}</p>
                        {entry.notes && (
                          <p className="text-xs text-gray-500">{entry.notes}</p>
                        )}
                        <p className="text-xs text-gray-400">
                          {new Date(entry.moved_at).toLocaleString('ru-RU')}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Статус</h2>
            <p className="text-sm text-gray-500 mb-2">Статус клиента</p>
            <span className="inline-block px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
              {client.status}
            </span>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Платежи</h2>
            {payments && payments.length > 0 ? (
              <div className="space-y-2">
                {payments.slice(0, 5).map((payment: any) => (
                  <div key={payment.id} className="text-sm">
                    <p className="font-medium">{payment.amount.toLocaleString('ru-RU')}₽</p>
                    <p className="text-gray-500">{payment.payment_type}</p>
                    <p className="text-gray-400 text-xs">
                      {new Date(payment.created_at).toLocaleDateString('ru-RU')}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">Нет платежей</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ClientDetail
