import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useModal } from '../components/ui/modal/ModalContext'

interface ProgramTemplate {
  id: number
  name: string
  template_type: 'footer' | 'program'
  content: string
  description: string | null
  placeholders: string[] | null
  is_active: boolean
  is_default: boolean
  created_at: string
  updated_at: string
  created_by: number | null
  updated_by: number | null
}

export default function ProgramTemplates() {
  const { showModal } = useModal()
  const queryClient = useQueryClient()
  const [selectedType, setSelectedType] = useState<'footer' | 'program' | 'all'>('all')
  const [editingTemplate, setEditingTemplate] = useState<ProgramTemplate | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    template_type: 'footer' as 'footer' | 'program',
    content: '',
    description: '',
    placeholders: [] as string[],
    is_active: true,
    is_default: false
  })

  // Fetch templates
  const { data: templates, isLoading } = useQuery<ProgramTemplate[]>({
    queryKey: ['program-templates', selectedType],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (selectedType !== 'all') {
        params.append('template_type', selectedType)
      }
      const response = await api.get(`/program-templates/?${params.toString()}`)
      return response.data
    }
  })

  // Create template
  const createMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const response = await api.post('/program-templates/', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['program-templates'] })
      setIsCreating(false)
      resetForm()
      showModal({
        title: 'Шаблон создан',
        message: 'Шаблон успешно создан',
        tone: 'success'
      })
    },
    onError: (error: any) => {
      showModal({
        title: 'Ошибка',
        message: error?.response?.data?.detail || 'Не удалось создать шаблон',
        tone: 'error'
      })
    }
  })

  // Update template
  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: Partial<typeof formData> }) => {
      const response = await api.put(`/program-templates/${id}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['program-templates'] })
      setEditingTemplate(null)
      resetForm()
      showModal({
        title: 'Шаблон обновлён',
        message: 'Шаблон успешно обновлён',
        tone: 'success'
      })
    },
    onError: (error: any) => {
      showModal({
        title: 'Ошибка',
        message: error?.response?.data?.detail || 'Не удалось обновить шаблон',
        tone: 'error'
      })
    }
  })

  // Delete template
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/program-templates/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['program-templates'] })
      showModal({
        title: 'Шаблон удалён',
        message: 'Шаблон успешно удалён',
        tone: 'success'
      })
    },
    onError: (error: any) => {
      showModal({
        title: 'Ошибка',
        message: error?.response?.data?.detail || 'Не удалось удалить шаблон',
        tone: 'error'
      })
    }
  })

  const resetForm = () => {
    setFormData({
      name: '',
      template_type: 'footer',
      content: '',
      description: '',
      placeholders: [],
      is_active: true,
      is_default: false
    })
  }

  const handleEdit = (template: ProgramTemplate) => {
    setEditingTemplate(template)
    setFormData({
      name: template.name,
      template_type: template.template_type,
      content: template.content,
      description: template.description || '',
      placeholders: template.placeholders || [],
      is_active: template.is_active,
      is_default: template.is_default
    })
    setIsCreating(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingTemplate) {
      updateMutation.mutate({ id: editingTemplate.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleDelete = (template: ProgramTemplate) => {
    showModal({
      title: 'Подтверждение удаления',
      message: `Вы уверены, что хотите удалить шаблон "${template.name}"?`,
      tone: 'warning',
      actions: [
        {
          label: 'Отмена',
          variant: 'secondary',
        },
        {
          label: 'Удалить',
          variant: 'primary',
          onClick: () => {
            deleteMutation.mutate(template.id)
          },
        },
      ],
    })
  }

  const filteredTemplates = templates?.filter(t => 
    selectedType === 'all' || t.template_type === selectedType
  ) || []

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Шаблоны программ</h1>
        <button
          onClick={() => {
            resetForm()
            setEditingTemplate(null)
            setIsCreating(true)
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Создать шаблон
        </button>
      </div>

      {/* Filter tabs */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="flex -mb-px">
          <button
            onClick={() => setSelectedType('all')}
            className={`px-4 py-2 border-b-2 font-medium text-sm ${
              selectedType === 'all'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Все
          </button>
          <button
            onClick={() => setSelectedType('footer')}
            className={`px-4 py-2 border-b-2 font-medium text-sm ${
              selectedType === 'footer'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Разъяснения (Footer)
          </button>
          <button
            onClick={() => setSelectedType('program')}
            className={`px-4 py-2 border-b-2 font-medium text-sm ${
              selectedType === 'program'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Шаблоны программ
          </button>
        </nav>
      </div>

      {/* Create/Edit Form */}
      {isCreating && (
        <div className="mb-6 bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">
            {editingTemplate ? 'Редактировать шаблон' : 'Создать шаблон'}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Название
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Тип шаблона
              </label>
              <select
                value={formData.template_type}
                onChange={(e) => setFormData({ ...formData, template_type: e.target.value as 'footer' | 'program' })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                required
              >
                <option value="footer">Разъяснения (Footer)</option>
                <option value="program">Шаблон программы</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Описание
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                rows={2}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Содержимое шаблона
                <span className="text-xs text-gray-500 ml-2">
                  (используйте плейсхолдеры: {'{client_name}'}, {'{trainer_name}'}, {'{trainer_phone}'}, {'{trainer_telegram}'}, {'{date}'})
                </span>
              </label>
              <textarea
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
                rows={10}
                required
              />
            </div>

            <div className="flex items-center space-x-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Активен</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">По умолчанию</span>
              </label>
            </div>

            <div className="flex space-x-2">
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {editingTemplate ? 'Сохранить' : 'Создать'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false)
                  setEditingTemplate(null)
                  resetForm()
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Templates List */}
      {isLoading ? (
        <div className="text-center py-8">Загрузка...</div>
      ) : filteredTemplates.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          Шаблоны не найдены
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTemplates.map((template) => (
            <div
              key={template.id}
              className="bg-white rounded-lg shadow p-4 border border-gray-200"
            >
              <div className="flex justify-between items-start mb-2">
                <div>
                  <h3 className="font-semibold text-lg">{template.name}</h3>
                  <span className="text-xs text-gray-500">
                    {template.template_type === 'footer' ? 'Разъяснения' : 'Шаблон программы'}
                  </span>
                </div>
                <div className="flex space-x-1">
                  {template.is_default && (
                    <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                      По умолчанию
                    </span>
                  )}
                  {!template.is_active && (
                    <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded">
                      Неактивен
                    </span>
                  )}
                </div>
              </div>

              {template.description && (
                <p className="text-sm text-gray-600 mb-2">{template.description}</p>
              )}

              <div className="text-xs text-gray-500 mb-3 line-clamp-3">
                {template.content.substring(0, 100)}...
              </div>

              <div className="flex space-x-2">
                <button
                  onClick={() => handleEdit(template)}
                  className="px-3 py-1 bg-blue-100 text-blue-700 rounded text-sm hover:bg-blue-200"
                >
                  Редактировать
                </button>
                <button
                  onClick={() => handleDelete(template)}
                  className="px-3 py-1 bg-red-100 text-red-700 rounded text-sm hover:bg-red-200"
                  disabled={template.is_default}
                >
                  Удалить
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

