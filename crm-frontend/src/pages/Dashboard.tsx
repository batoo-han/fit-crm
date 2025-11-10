import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import { Link } from 'react-router-dom'

const Dashboard = () => {
  const { data: overview, isLoading } = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: async () => {
      const response = await api.get('/analytics/overview')
      return response.data
    },
  })

  if (isLoading) {
    return <div>Загрузка...</div>
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500">Всего клиентов</div>
          <div className="mt-2 text-3xl font-bold text-gray-900">{overview?.total_clients || 0}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500">Активных клиентов</div>
          <div className="mt-2 text-3xl font-bold text-green-600">{overview?.active_clients || 0}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500">Программ</div>
          <div className="mt-2 text-3xl font-bold text-blue-600">{overview?.paid_programs || 0}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500">Выручка</div>
          <div className="mt-2 text-3xl font-bold text-purple-600">
            {overview?.total_revenue?.toLocaleString('ru-RU') || 0}₽
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Быстрые действия</h2>
          <div className="space-y-2">
            <Link
              to="/clients"
              className="block px-4 py-2 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition-colors"
            >
              👥 Просмотр клиентов
            </Link>
            <Link
              to="/pipeline"
              className="block px-4 py-2 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition-colors"
            >
              🔄 Управление воронкой
            </Link>
            <Link
              to="/programs"
              className="block px-4 py-2 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition-colors"
            >
              📋 Программы тренировок
            </Link>
            <Link
              to="/analytics"
              className="block px-4 py-2 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition-colors"
            >
              📈 Аналитика
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard

