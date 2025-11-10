import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const Analytics = () => {
  const { data: overview } = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: async () => {
      const response = await api.get('/analytics/overview')
      return response.data
    },
  })

  const { data: conversion } = useQuery({
    queryKey: ['analytics', 'conversion'],
    queryFn: async () => {
      const response = await api.get('/analytics/conversion')
      return response.data
    },
  })

  const { data: revenue } = useQuery({
    queryKey: ['analytics', 'revenue'],
    queryFn: async () => {
      const response = await api.get('/analytics/revenue?days=30')
      return response.data
    },
  })

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#6B7280', '#94A3B8']

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Аналитика</h1>

      {/* Общая статистика */}
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
          <div className="text-sm font-medium text-gray-500">Оплаченных программ</div>
          <div className="mt-2 text-3xl font-bold text-blue-600">{overview?.paid_programs || 0}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500">Общая выручка</div>
          <div className="mt-2 text-3xl font-bold text-purple-600">
            {overview?.total_revenue?.toLocaleString('ru-RU') || 0}₽
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Воронка конверсии */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Воронка продаж</h2>
          {conversion && conversion.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={conversion}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="stage_name" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#3B82F6" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center py-12 text-gray-500">Нет данных</div>
          )}
        </div>

        {/* Распределение по этапам */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Распределение клиентов</h2>
          {conversion && conversion.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={conversion}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={false}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {conversion.map((_entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value: any, _name: any, props: any) => [
                    `${props.payload.stage_name}: ${value}`,
                    'Количество'
                  ]}
                />
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  formatter={(_value: any, entry: any) => `${entry.payload.stage_name}: ${entry.payload.count}`}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center py-12 text-gray-500">Нет данных</div>
          )}
        </div>
      </div>

      {/* Статистика по выручке */}
      {revenue && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Выручка за последние 30 дней</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="text-sm font-medium text-gray-500">Общая выручка</div>
              <div className="mt-2 text-2xl font-bold text-gray-900">
                {revenue.total_revenue?.toLocaleString('ru-RU') || 0}₽
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500">Количество платежей</div>
              <div className="mt-2 text-2xl font-bold text-gray-900">
                {revenue.payment_count || 0}
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500">Средний чек</div>
              <div className="mt-2 text-2xl font-bold text-gray-900">
                {revenue.average_payment?.toLocaleString('ru-RU') || 0}₽
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Детальная таблица воронки */}
      {conversion && conversion.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mt-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Детализация по этапам</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Этап
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Количество клиентов
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Процент
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {conversion.map((stage: any) => {
                  const total = conversion.reduce((sum: number, s: any) => sum + s.count, 0)
                  const percentage = total > 0 ? ((stage.count / total) * 100).toFixed(1) : 0
                  return (
                    <tr key={stage.stage_id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div
                            className="w-4 h-4 rounded-full mr-2"
                            style={{ backgroundColor: stage.color }}
                          />
                          <span className="text-sm font-medium text-gray-900">
                            {stage.stage_name}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {stage.count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="w-32 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="h-2 rounded-full"
                              style={{
                                width: `${percentage}%`,
                                backgroundColor: stage.color,
                              }}
                            />
                          </div>
                          <span className="text-sm text-gray-500">{percentage}%</span>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export default Analytics
