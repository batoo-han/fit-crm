import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const Progress = () => {
  const { clientId } = useParams<{ clientId: string }>()
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [formData, setFormData] = useState({
    period: 'before',
    weight: '',
    chest: '',
    waist: '',
    lower_abdomen: '',
    glutes: '',
    right_thigh: '',
    left_thigh: '',
    right_calf: '',
    left_calf: '',
    right_arm: '',
    left_arm: '',
    notes: '',
  })

  const { data: progress, isLoading } = useQuery({
    queryKey: ['progress', clientId],
    queryFn: async () => {
      const response = await api.get(`/progress/${clientId}`)
      return response.data
    },
  })

  const { data: chartData } = useQuery({
    queryKey: ['progress-chart', clientId],
    queryFn: async () => {
      const response = await api.get(`/progress/${clientId}/chart`)
      return response.data
    },
  })

  const addMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.post('/progress', {
        client_id: parseInt(clientId!),
        ...data,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['progress', clientId] })
      queryClient.invalidateQueries({ queryKey: ['progress-chart', clientId] })
      setShowAddForm(false)
      setFormData({
        period: 'before',
        weight: '',
        chest: '',
        waist: '',
        lower_abdomen: '',
        glutes: '',
        right_thigh: '',
        left_thigh: '',
        right_calf: '',
        left_calf: '',
        right_arm: '',
        left_arm: '',
        notes: '',
      })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data: any = {
      period: formData.period,
      notes: formData.notes || null,
    }

    // Добавляем только заполненные измерения
    if (formData.weight) data.weight = parseFloat(formData.weight)
    if (formData.chest) data.chest = parseFloat(formData.chest)
    if (formData.waist) data.waist = parseFloat(formData.waist)
    if (formData.lower_abdomen) data.lower_abdomen = parseFloat(formData.lower_abdomen)
    if (formData.glutes) data.glutes = parseFloat(formData.glutes)
    if (formData.right_thigh) data.right_thigh = parseFloat(formData.right_thigh)
    if (formData.left_thigh) data.left_thigh = parseFloat(formData.left_thigh)
    if (formData.right_calf) data.right_calf = parseFloat(formData.right_calf)
    if (formData.left_calf) data.left_calf = parseFloat(formData.left_calf)
    if (formData.right_arm) data.right_arm = parseFloat(formData.right_arm)
    if (formData.left_arm) data.left_arm = parseFloat(formData.left_arm)

    addMutation.mutate(data)
  }

  const periodLabels: Record<string, string> = {
    before: 'До начала',
    week_1: '1 неделя',
    week_2: '2 неделя',
    week_3: '3 неделя',
    week_4: '4 неделя',
    week_5: '5 неделя',
    week_6: '6 неделя',
    week_7: '7 неделя',
    week_8: '8 неделя',
    week_9: '9 неделя',
    week_10: '10 неделя',
    week_11: '11 неделя',
    week_12: '12 неделя',
    after: 'После завершения',
  }

  if (isLoading) {
    return <div>Загрузка...</div>
  }

  // Подготовка данных для графика
  const chartDataFormatted = progress?.map((entry: any) => ({
    period: periodLabels[entry.period] || entry.period,
    weight: entry.weight,
    chest: entry.chest,
    waist: entry.waist,
    glutes: entry.glutes,
  }))

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Дневник параметров</h1>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          {showAddForm ? 'Отмена' : '+ Добавить запись'}
        </button>
      </div>

      {showAddForm && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Новая запись</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Период
              </label>
              <select
                value={formData.period}
                onChange={(e) => setFormData({ ...formData, period: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                {Object.entries(periodLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                  Грудь (см)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.chest}
                  onChange={(e) => setFormData({ ...formData, chest: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Талия (см)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.waist}
                  onChange={(e) => setFormData({ ...formData, waist: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Низ живота (см)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.lower_abdomen}
                  onChange={(e) => setFormData({ ...formData, lower_abdomen: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ягодицы (см)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.glutes}
                  onChange={(e) => setFormData({ ...formData, glutes: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Правое бедро (см)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.right_thigh}
                  onChange={(e) => setFormData({ ...formData, right_thigh: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Левое бедро (см)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.left_thigh}
                  onChange={(e) => setFormData({ ...formData, left_thigh: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Правая голень (см)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.right_calf}
                  onChange={(e) => setFormData({ ...formData, right_calf: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Левая голень (см)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.left_calf}
                  onChange={(e) => setFormData({ ...formData, left_calf: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Правая рука (см)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.right_arm}
                  onChange={(e) => setFormData({ ...formData, right_arm: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Левая рука (см)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.left_arm}
                  onChange={(e) => setFormData({ ...formData, left_arm: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Заметки
              </label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                rows={3}
              />
            </div>

            <button
              type="submit"
              disabled={addMutation.isPending}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {addMutation.isPending ? 'Сохранение...' : 'Сохранить'}
            </button>
          </form>
        </div>
      )}

      {/* График прогресса */}
      {chartDataFormatted && chartDataFormatted.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">График прогресса</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartDataFormatted}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="weight" stroke="#8884d8" name="Вес (кг)" />
              <Line type="monotone" dataKey="chest" stroke="#82ca9d" name="Грудь (см)" />
              <Line type="monotone" dataKey="waist" stroke="#ffc658" name="Талия (см)" />
              <Line type="monotone" dataKey="glutes" stroke="#ff7300" name="Ягодицы (см)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Таблица записей */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Период
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Вес
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Грудь
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Талия
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Ягодицы
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Дата
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {progress?.map((entry: any) => (
              <tr key={entry.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {periodLabels[entry.period] || entry.period}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {entry.weight ? `${entry.weight} кг` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {entry.chest ? `${entry.chest} см` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {entry.waist ? `${entry.waist} см` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {entry.glutes ? `${entry.glutes} см` : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(entry.measurement_date).toLocaleDateString('ru-RU')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!progress || progress.length === 0) && (
          <div className="text-center py-12 text-gray-500">
            Нет записей. Добавьте первую запись для отслеживания прогресса.
          </div>
        )}
      </div>
    </div>
  )
}

export default Progress
