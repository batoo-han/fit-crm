import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useState } from 'react'
import { Link } from 'react-router-dom'

const Pipeline = () => {
  const queryClient = useQueryClient()
  const [selectedClient, setSelectedClient] = useState<number | null>(null)
  const [targetStage, setTargetStage] = useState<number | null>(null)

  const { data: stages } = useQuery({
    queryKey: ['pipeline-stages'],
    queryFn: async () => {
      const response = await api.get('/pipeline/stages')
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

  const moveMutation = useMutation({
    mutationFn: async ({ clientId, stageId }: { clientId: number; stageId: number }) => {
      const response = await api.post(`/pipeline/clients/${clientId}/move-stage`, {
        stage_id: stageId,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setSelectedClient(null)
      setTargetStage(null)
    },
  })

  const handleMove = (clientId: number, stageId: number) => {
    moveMutation.mutate({ clientId, stageId })
  }

  if (!stages || !clients) {
    return <div>Загрузка...</div>
  }

  // Группируем клиентов по этапам
  const clientsByStage = stages.reduce((acc: any, stage: any) => {
    acc[stage.id] = clients.filter((client: any) => client.pipeline_stage_id === stage.id)
    return acc
  }, {})

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Воронка продаж</h1>
        <Link
          to="/pipeline/settings"
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          ⚙️ Настройки
        </Link>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4">
        {stages.map((stage: any) => (
          <div
            key={stage.id}
            className="flex-shrink-0 w-80 bg-gray-50 rounded-lg p-4"
            style={{ borderTop: `4px solid ${stage.color}` }}
          >
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-bold text-gray-900">{stage.name}</h2>
              <span className="bg-white px-2 py-1 rounded-full text-sm font-medium">
                {clientsByStage[stage.id]?.length || 0}
              </span>
            </div>
            {stage.description && (
              <p className="text-sm text-gray-500 mb-4">{stage.description}</p>
            )}

            <div className="space-y-2">
              {clientsByStage[stage.id]?.map((client: any) => (
                <div
                  key={client.id}
                  className="bg-white rounded-lg p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => setSelectedClient(client.id)}
                >
                  <Link
                    to={`/clients/${client.id}`}
                    className="block"
                  >
                    <p className="font-medium text-gray-900">
                      {client.first_name} {client.last_name || ''}
                    </p>
                    {client.telegram_username && (
                      <p className="text-sm text-gray-500">@{client.telegram_username}</p>
                    )}
                    <div className="mt-2 flex gap-2">
                      {stages
                        .filter((s: any) => s.id !== stage.id)
                        .slice(0, 2)
                        .map((targetStage: any) => (
                          <button
                            key={targetStage.id}
                            onClick={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                              handleMove(client.id, targetStage.id)
                            }}
                            className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded"
                            style={{ color: targetStage.color }}
                          >
                            → {targetStage.name}
                          </button>
                        ))}
                    </div>
                  </Link>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Модальное окно для перемещения */}
      {selectedClient && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-xl font-bold mb-4">Переместить клиента</h3>
            <div className="space-y-2">
              {stages.map((stage: any) => (
                <button
                  key={stage.id}
                  onClick={() => {
                    handleMove(selectedClient, stage.id)
                  }}
                  className="w-full text-left px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
                  style={{ borderLeft: `4px solid ${stage.color}` }}
                >
                  {stage.name}
                </button>
              ))}
            </div>
            <button
              onClick={() => setSelectedClient(null)}
              className="mt-4 w-full px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
            >
              Отмена
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Pipeline
