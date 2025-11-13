import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import { Link } from 'react-router-dom'
import { useState } from 'react'

const Programs = () => {
  const [filter, setFilter] = useState<'all' | 'paid' | 'free'>('all')

  const { data: programs, isLoading } = useQuery({
    queryKey: ['programs', filter],
    queryFn: async () => {
      const params = filter === 'paid' ? '?is_paid=true' : filter === 'free' ? '?is_paid=false' : ''
      const response = await api.get(`/programs${params}`)
      return response.data
    },
  })

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => {
      const response = await api.get('/clients')
      return response.data
    },
  })

  const getClientName = (clientId: number) => {
    const client = clients?.find((c: any) => c.id === clientId)
    return client ? `${client.first_name} ${client.last_name || ''}` : `Клиент #${clientId}`
  }

  if (isLoading) {
    return <div>Загрузка...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Программы тренировок</h1>
        <Link
          to="/program-cleanup"
          className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
        >
          Очистка программ
        </Link>
      </div>

      <div className="mb-6 flex gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded-lg ${
            filter === 'all'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Все
        </button>
        <button
          onClick={() => setFilter('paid')}
          className={`px-4 py-2 rounded-lg ${
            filter === 'paid'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Оплаченные
        </button>
        <button
          onClick={() => setFilter('free')}
          className={`px-4 py-2 rounded-lg ${
            filter === 'free'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Бесплатные
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Клиент
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Тип программы
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Статус
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Дата создания
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Действия
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {programs?.map((program: any) => (
              <tr key={program.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  #{program.id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link
                    to={`/clients/${program.client_id}`}
                    className="text-sm font-medium text-primary-600 hover:text-primary-900"
                  >
                    {getClientName(program.client_id)}
                  </Link>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    {program.program_type === 'paid_monthly' && '💼 1 месяц'}
                    {program.program_type === 'paid_3month' && '🏆 3 месяца'}
                    {program.program_type === 'free_demo' && '🎯 Бесплатная демо'}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex gap-2">
                    {program.is_paid && (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        Оплачено
                      </span>
                    )}
                    {program.is_completed && (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                        Завершено
                      </span>
                    )}
                    {!program.is_completed && (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">
                        Активна
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(program.created_at).toLocaleDateString('ru-RU')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <Link
                    to={`/programs/${program.id}`}
                    className="text-primary-600 hover:text-primary-900"
                  >
                    Просмотр →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!programs || programs.length === 0) && (
          <div className="text-center py-12 text-gray-500">
            Нет программ
          </div>
        )}
      </div>
    </div>
  )
}

export default Programs
