import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const PipelineSettings = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [editingStage, setEditingStage] = useState<number | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    order: 0,
    color: '#3B82F6',
    description: '',
    is_active: true,
  })

  const { data: stages, isLoading } = useQuery({
    queryKey: ['pipeline-stages', 'all'],
    queryFn: async () => {
      const response = await api.get('/pipeline/stages?include_inactive=true')
      return response.data
    },
  })

  const [editingData, setEditingData] = useState<Record<number, any>>({})

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: any }) => {
      const response = await api.put(`/pipeline/stages/${id}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-stages'] })
      queryClient.invalidateQueries({ queryKey: ['pipeline-stages', 'all'] })
      setEditingStage(null)
      setEditingData({})
    },
  })

  const createMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.post('/pipeline/stages', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-stages'] })
      setShowCreateModal(false)
      setFormData({
        name: '',
        order: 0,
        color: '#3B82F6',
        description: '',
        is_active: true,
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/pipeline/stages/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-stages'] })
    },
  })

  const handleSave = (id: number, data: any) => {
    updateMutation.mutate(
      { id, data },
      {
        onSuccess: () => {
          setEditingStage(null)
          const newEditingData = { ...editingData }
          delete newEditingData[id]
          setEditingData(newEditingData)
        },
      }
    )
  }

  const handleEditStart = (stage: any) => {
    setEditingStage(stage.id)
    setEditingData({
      ...editingData,
      [stage.id]: {
        name: stage.name,
        order: stage.order,
        color: stage.color,
        description: stage.description || '',
        is_active: stage.is_active,
      },
    })
  }


  const handleCreate = () => {
    createMutation.mutate(formData)
  }

  const handleDelete = (id: number) => {
    if (confirm('Вы уверены, что хотите удалить этот этап? Клиенты на этом этапе будут перемещены.')) {
      deleteMutation.mutate(id)
    }
  }

  if (isLoading) {
    return <div>Загрузка...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Настройки воронки</h1>
          <p className="text-gray-500 mt-2">
            Управление этапами воронки продаж и правилами перемещения клиентов
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/pipeline')}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Вернуться к воронке
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            + Добавить этап
          </button>
        </div>
      </div>

      {/* Список этапов */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Этапы воронки</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {stages?.map((stage: any) => (
            <div
              key={stage.id}
              className="p-6 hover:bg-gray-50 transition-colors"
              style={{ borderLeft: `4px solid ${stage.color}` }}
            >
              {editingStage === stage.id ? (
                <StageEditForm
                  stage={stage}
                  onSave={(data) => handleSave(stage.id, data)}
                  onCancel={() => {
                    setEditingStage(null)
                    const newEditingData = { ...editingData }
                    delete newEditingData[stage.id]
                    setEditingData(newEditingData)
                  }}
                />
              ) : (
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-4">
                      <h3 className="text-lg font-semibold text-gray-900">{stage.name}</h3>
                      <span className="text-sm text-gray-500">Порядок: {stage.order}</span>
                      <div
                        className="w-6 h-6 rounded-full border border-gray-300"
                        style={{ backgroundColor: stage.color }}
                      />
                    </div>
                    {stage.description && (
                      <p className="text-sm text-gray-600 mt-2">{stage.description}</p>
                    )}
                    <div className="mt-2 flex gap-2">
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          stage.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {stage.is_active ? 'Активен' : 'Неактивен'}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleEditStart(stage)}
                      className="px-3 py-1 text-sm text-primary-600 hover:bg-primary-50 rounded"
                    >
                      Редактировать
                    </button>
                    <button
                      onClick={() => handleDelete(stage.id)}
                      className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded"
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Модальное окно создания этапа */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Добавить этап</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Название *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Порядок
                </label>
                <input
                  type="number"
                  value={formData.order}
                  onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Цвет
                </label>
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={formData.color}
                    onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                    className="h-10 w-20 border border-gray-300 rounded"
                  />
                  <input
                    type="text"
                    value={formData.color}
                    onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="#3B82F6"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Описание
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  rows={3}
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="mr-2"
                />
                <label htmlFor="is_active" className="text-sm text-gray-700">
                  Активен
                </label>
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Отмена
              </button>
              <button
                onClick={handleCreate}
                disabled={createMutation.isPending || !formData.name}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {createMutation.isPending ? 'Создание...' : 'Создать'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

interface StageEditFormProps {
  stage: any
  onSave: (data: any) => void
  onCancel: () => void
}

const StageEditForm: React.FC<StageEditFormProps> = ({ stage, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    name: stage.name,
    order: stage.order,
    color: stage.color,
    description: stage.description || '',
    is_active: stage.is_active,
  })

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Название *
        </label>
        <input
          type="text"
          required
          value={formData?.name || ''}
          onChange={(e) => handleChange('name', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Порядок
        </label>
        <input
          type="number"
          value={formData?.order || 0}
          onChange={(e) => handleChange('order', parseInt(e.target.value) || 0)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Цвет
        </label>
        <div className="flex gap-2">
          <input
            type="color"
            value={formData?.color || '#3B82F6'}
            onChange={(e) => handleChange('color', e.target.value)}
            className="h-10 w-20 border border-gray-300 rounded"
          />
          <input
            type="text"
            value={formData?.color || '#3B82F6'}
            onChange={(e) => handleChange('color', e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
            placeholder="#3B82F6"
          />
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Описание
        </label>
        <textarea
          value={formData?.description || ''}
          onChange={(e) => handleChange('description', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          rows={3}
        />
      </div>
      <div className="flex items-center">
        <input
          type="checkbox"
          id={`is_active_${stage.id}`}
          checked={formData?.is_active ?? true}
          onChange={(e) => handleChange('is_active', e.target.checked)}
          className="mr-2"
        />
        <label htmlFor={`is_active_${stage.id}`} className="text-sm text-gray-700">
          Активен
        </label>
      </div>
      <div className="flex gap-2 justify-end">
        <button
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Отмена
        </button>
        <button
          onClick={onSave}
          disabled={!formData?.name}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        >
          Сохранить
        </button>
      </div>
    </div>
  )
}

export default PipelineSettings

