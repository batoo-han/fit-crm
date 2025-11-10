import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'

const Clients = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState<number | null>(null)
  const [formData, setFormData] = useState({
    telegram_id: '',
    first_name: '',
    last_name: '',
    telegram_username: '',
    phone_number: '',
    age: '',
    gender: '',
    height: '',
    weight: '',
    status: 'new',
    pipeline_stage_id: '',
  })

  const { data: clients, isLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => {
      const response = await api.get('/clients')
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

  const createMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.post('/clients', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setShowCreateModal(false)
      setFormData({
        telegram_id: '',
        first_name: '',
        last_name: '',
        telegram_username: '',
        phone_number: '',
        age: '',
        gender: '',
        height: '',
        weight: '',
        status: 'new',
        pipeline_stage_id: '',
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (clientId: number) => {
      await api.delete(`/clients/${clientId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setShowDeleteModal(null)
    },
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    const data: any = {
      telegram_id: parseInt(formData.telegram_id),
      status: formData.status,
    }

    if (formData.first_name) data.first_name = formData.first_name
    if (formData.last_name) data.last_name = formData.last_name
    if (formData.telegram_username) data.telegram_username = formData.telegram_username
    if (formData.phone_number) data.phone_number = formData.phone_number
    if (formData.age) data.age = parseInt(formData.age)
    if (formData.gender) data.gender = formData.gender
    if (formData.height) data.height = parseInt(formData.height)
    if (formData.weight) data.weight = parseFloat(formData.weight)
    if (formData.pipeline_stage_id) data.pipeline_stage_id = parseInt(formData.pipeline_stage_id)

    createMutation.mutate(data)
  }

  const handleDelete = (clientId: number) => {
    deleteMutation.mutate(clientId)
  }

  if (isLoading) {
    return <div>Загрузка...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Клиенты</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          + Добавить клиента
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Имя
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Телеграм
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Статус
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Дата регистрации
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Действия
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {clients?.map((client: any) => (
              <tr key={client.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    {client.first_name || 'Не указано'} {client.last_name || ''}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-500">@{client.telegram_username || 'нет'}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                    {client.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(client.created_at).toLocaleDateString('ru-RU')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div className="flex gap-2">
                    <Link
                      to={`/clients/${client.id}`}
                      className="text-primary-600 hover:text-primary-900"
                    >
                      Подробнее
                    </Link>
                    <button
                      onClick={() => setShowDeleteModal(client.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Удалить
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Client Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold mb-4">Добавить клиента</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Telegram ID *
                  </label>
                  <input
                    type="number"
                    required
                    value={formData.telegram_id}
                    onChange={(e) => setFormData({ ...formData, telegram_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Имя
                  </label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Фамилия
                  </label>
                  <input
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Telegram Username
                  </label>
                  <input
                    type="text"
                    value={formData.telegram_username}
                    onChange={(e) => setFormData({ ...formData, telegram_username: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="@username"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Телефон
                  </label>
                  <input
                    type="text"
                    value={formData.phone_number}
                    onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Возраст
                  </label>
                  <input
                    type="number"
                    value={formData.age}
                    onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Пол
                  </label>
                  <select
                    value={formData.gender}
                    onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="">Не указан</option>
                    <option value="мужской">Мужской</option>
                    <option value="женский">Женский</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Рост (см)
                  </label>
                  <input
                    type="number"
                    value={formData.height}
                    onChange={(e) => setFormData({ ...formData, height: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Вес (кг)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.weight}
                    onChange={(e) => setFormData({ ...formData, weight: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Статус
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="new">Новый</option>
                    <option value="qualified">Квалифицирован</option>
                    <option value="client">Клиент</option>
                    <option value="inactive">Неактивен</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Этап воронки
                  </label>
                  <select
                    value={formData.pipeline_stage_id}
                    onChange={(e) => setFormData({ ...formData, pipeline_stage_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="">Не выбран</option>
                    {stages?.map((stage: any) => (
                      <option key={stage.id} value={stage.id}>
                        {stage.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex gap-2 justify-end mt-6">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Создание...' : 'Создать'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Удалить клиента?</h2>
            <p className="text-gray-600 mb-6">
              Вы уверены, что хотите удалить этого клиента? Это действие нельзя отменить.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowDeleteModal(null)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Отмена
              </button>
              <button
                onClick={() => handleDelete(showDeleteModal)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Удаление...' : 'Удалить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Clients

