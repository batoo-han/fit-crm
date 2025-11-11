import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'

type Campaign = {
  id: number
  name: string
  description?: string | null
  status: string
  channel: string
  schedule_at?: string | null
  params?: Record<string, unknown> | null
}

type Audience = {
  id: number
  name: string
  description?: string | null
  filter_json?: Record<string, unknown> | null
}

type Message = {
  id: number
  campaign_id: number
  title?: string | null
  body_text: string
}

const Marketing = () => {
  const queryClient = useQueryClient()
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null)
  const [campaignForm, setCampaignForm] = useState<Campaign | null>(null as unknown as Campaign)
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | ''>('')
  const [editingAudience, setEditingAudience] = useState<Audience | null>(null)
  const [audienceForm, setAudienceForm] = useState<Audience | null>(null as unknown as Audience)
  const [editingMessage, setEditingMessage] = useState<Message | null>(null)
  const [messageForm, setMessageForm] = useState<Message | null>(null as unknown as Message)
  const [editingPromo, setEditingPromo] = useState<any>(null)
  const initialPromoForm = {
    code: '',
    description: '',
    discount_type: 'percent',
    discount_value: 10,
    max_usage: 0,
    per_client_limit: 0,
    valid_from: '',
    valid_to: '',
    is_active: true,
  }
  const [promoForm, setPromoForm] = useState(initialPromoForm)
  const [checkCode, setCheckCode] = useState({ code: '', amount: 1000, result: '' })
  const resetPromoForm = () => setPromoForm({ ...initialPromoForm })

  const { data: campaigns } = useQuery({
    queryKey: ['mkt-campaigns'],
    queryFn: async () => {
      const res = await api.get('/marketing/campaigns')
      return res.data as Campaign[]
    },
  })

  const { data: runs } = useQuery({
    queryKey: ['mkt-runs', selectedCampaignId],
    queryFn: async () => {
      if (!selectedCampaignId) return []
      const res = await api.get(`/marketing/campaigns/${selectedCampaignId}/runs`)
      return res.data as Array<{ id: number; status: string; total: number; sent: number; errors: number; started_at?: string; completed_at?: string }>
    },
    enabled: !!selectedCampaignId,
  })

  const { data: deliveries } = useQuery({
    queryKey: ['mkt-deliveries', selectedCampaignId],
    queryFn: async () => {
      if (!selectedCampaignId) return []
      const res = await api.get(`/marketing/campaigns/${selectedCampaignId}/deliveries`)
      return res.data as Array<{ id: number; run_id?: number; client_id: number; channel: string; status: string; created_at?: string }>
    },
    enabled: !!selectedCampaignId,
  })

  const { data: timeseries } = useQuery({
    queryKey: ['mkt-timeseries', selectedCampaignId],
    queryFn: async () => {
      if (!selectedCampaignId) return { series: [] as Array<{ date: string; total: number; sent: number; failed: number; telegram: number; email: number }> }
      const res = await api.get(`/marketing/campaigns/${selectedCampaignId}/timeseries?days=14`)
      return res.data as { series: Array<{ date: string; total: number; sent: number; failed: number; telegram: number; email: number }> }
    },
    enabled: !!selectedCampaignId,
  })

  const { data: audiences } = useQuery({
    queryKey: ['mkt-audiences'],
    queryFn: async () => {
      const res = await api.get('/marketing/audiences')
      return res.data as Audience[]
    },
  })

  const { data: messages } = useQuery({
    queryKey: ['mkt-messages'],
    queryFn: async () => {
      const res = await api.get('/marketing/messages')
      return res.data as Message[]
    },
  })

  const { data: summary } = useQuery({
    queryKey: ['mkt-summary', selectedCampaignId],
    queryFn: async () => {
      if (!selectedCampaignId) return null
      const res = await api.get(`/marketing/campaigns/${selectedCampaignId}/summary`)
      return res.data as {
        unique_clients: number
        total_runs: number
        last_run_started_at?: string | null
        sent_total: number
        failed_total: number
        by_channel: Record<string, { sent: number; failed: number; total: number }>
      }
    },
    enabled: !!selectedCampaignId,
  })

  const { data: promos } = useQuery({
    queryKey: ['promo-codes'],
    queryFn: async () => {
      const res = await api.get('/promocodes')
      return res.data as Array<{
        id: number
        code: string
        description?: string
        discount_type: string
        discount_value: number
        is_active: boolean
        valid_from?: string | null
        valid_to?: string | null
        max_usage?: number | null
        per_client_limit?: number | null
        used_count: number
      }>
    },
  })

  const createCampaign = useMutation({
    mutationFn: async (payload: Partial<Campaign>) => {
      const res = await api.post('/marketing/campaigns', payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mkt-campaigns'] })
      setEditingCampaign(null)
      setCampaignForm(null as unknown as Campaign)
    },
  })
  const updateCampaign = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Partial<Campaign> }) => {
      const res = await api.put(`/marketing/campaigns/${id}`, payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mkt-campaigns'] })
      setEditingCampaign(null)
      setCampaignForm(null as unknown as Campaign)
    },
  })
  const deleteCampaign = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/marketing/campaigns/${id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mkt-campaigns'] }),
  })

  const createAudience = useMutation({
    mutationFn: async (payload: Partial<Audience>) => {
      const res = await api.post('/marketing/audiences', payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mkt-audiences'] })
      setEditingAudience(null)
      setAudienceForm(null as unknown as Audience)
    },
  })
  const updateAudience = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Partial<Audience> }) => {
      const res = await api.put(`/marketing/audiences/${id}`, payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mkt-audiences'] })
      setEditingAudience(null)
      setAudienceForm(null as unknown as Audience)
    },
  })
  const deleteAudience = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/marketing/audiences/${id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mkt-audiences'] }),
  })

  const createMessage = useMutation({
    mutationFn: async (payload: Partial<Message>) => {
      const res = await api.post('/marketing/messages', payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mkt-messages'] })
      setEditingMessage(null)
      setMessageForm(null as unknown as Message)
    },
  })
  const updateMessage = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Partial<Message> }) => {
      const res = await api.put(`/marketing/messages/${id}`, payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mkt-messages'] })
      setEditingMessage(null)
      setMessageForm(null as unknown as Message)
    },
  })
  const deleteMessage = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/marketing/messages/${id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mkt-messages'] }),
  })

  const createPromo = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post('/promocodes', payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['promo-codes'] })
      resetPromoForm()
      setEditingPromo(null)
    },
  })

  const updatePromo = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: any }) => {
      const res = await api.put(`/promocodes/${id}`, payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['promo-codes'] })
      resetPromoForm()
      setEditingPromo(null)
    },
  })

  const deletePromo = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/promocodes/${id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['promo-codes'] }),
  })

  const checkPromo = useMutation({
    mutationFn: async ({ code, amount }: { code: string; amount: number }) => {
      const res = await api.post('/promocodes/check', { code, amount })
      return res.data as { discount: number; final_amount: number }
    },
  })

  const startRun = useMutation({
    mutationFn: async ({ campaignId, audienceId, limit }: { campaignId: number; audienceId?: number; limit?: number }) => {
      const res = await api.post(`/marketing/campaigns/${campaignId}/start`, {
        audience_id: audienceId || null,
        limit: limit || 100,
      })
      return res.data
    },
  })

  const beginCreateCampaign = () => {
    setEditingCampaign({ id: 0, name: '', description: '', status: 'draft', channel: 'both', schedule_at: null, params: {} })
    setCampaignForm({ id: 0, name: '', description: '', status: 'draft', channel: 'both', schedule_at: null, params: {} })
  }
  const beginEditCampaign = (c: Campaign) => {
    setEditingCampaign(c)
    setCampaignForm({ ...c, params: c.params || {} })
  }
  const submitCampaign = () => {
    if (!campaignForm?.name || campaignForm.name.trim().length === 0) {
      alert('Название кампании обязательно')
      return
    }
    const payload = {
      name: campaignForm.name.trim(),
      description: campaignForm.description || '',
      status: campaignForm.status || 'draft',
      channel: campaignForm.channel || 'both',
      schedule_at: campaignForm.schedule_at || null,
      params: campaignForm.params || {},
    }
    if (editingCampaign && editingCampaign.id > 0) {
      updateCampaign.mutate({ id: editingCampaign.id, payload })
    } else {
      createCampaign.mutate(payload)
    }
  }

  const beginCreateAudience = () => {
    setEditingAudience({ id: 0, name: '', description: '', filter_json: {} })
    setAudienceForm({ id: 0, name: '', description: '', filter_json: {} })
  }
  const beginEditAudience = (a: Audience) => {
    setEditingAudience(a)
    setAudienceForm({ ...a, filter_json: a.filter_json || {} })
  }
  const submitAudience = () => {
    if (!audienceForm?.name || audienceForm.name.trim().length === 0) {
      alert('Название сегмента обязательно')
      return
    }
    const payload = {
      name: audienceForm.name.trim(),
      description: audienceForm.description || '',
      filter_json: audienceForm.filter_json || {},
    }
    if (editingAudience && editingAudience.id > 0) {
      updateAudience.mutate({ id: editingAudience.id, payload })
    } else {
      createAudience.mutate(payload)
    }
  }

  const beginCreateMessage = () => {
    if (!campaigns || campaigns.length === 0) {
      alert('Сначала создайте кампанию')
      return
    }
    setEditingMessage({ id: 0, campaign_id: campaigns[0].id, title: '', body_text: '' })
    setMessageForm({ id: 0, campaign_id: campaigns[0].id, title: '', body_text: '' })
  }
  const beginEditMessage = (m: Message) => {
    setEditingMessage(m)
    setMessageForm({ ...m })
  }
  const submitMessage = () => {
    if (!messageForm?.campaign_id || !messageForm.body_text || messageForm.body_text.trim().length === 0) {
      alert('Выберите кампанию и заполните текст сообщения')
      return
    }
    const payload = {
      campaign_id: messageForm.campaign_id,
      title: messageForm.title || '',
      body_text: messageForm.body_text,
    }
    if (editingMessage && editingMessage.id > 0) {
      updateMessage.mutate({ id: editingMessage.id, payload })
    } else {
      createMessage.mutate(payload)
    }
  }

  const parseJson = (s: string) => {
    try {
      if (s.trim() === '') return {}
      return JSON.parse(s)
    } catch {
      alert('Неверный JSON')
      return {}
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Маркетинг</h1>
        <p className="text-gray-500 mt-2">Кампании, сегменты и сообщения. Здесь можно запускать рассылки по выбранной аудитории.</p>
        <div className="mt-3">
          <button
            onClick={async () => {
              try {
                await api.post('/marketing/process-scheduled', { limit_per_run: 200, max_runs: 5 })
                alert('Запланированные кампании поставлены в обработку (если были условия).')
              } catch {
                alert('Не удалось запустить обработку расписанных кампаний')
              }
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
          >
            Запустить обработку расписанных кампаний
          </button>
        </div>
      </div>

      {/* Campaigns */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Кампании</h2>
          <button onClick={beginCreateCampaign} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
            + Новая кампания
          </button>
        </div>
        <div className="divide-y border border-gray-200 rounded-lg">
          {(campaigns || []).map((c) => (
            <div key={c.id} className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedCampaignId(c.id)}
                    className={`font-semibold ${selectedCampaignId === c.id ? 'text-primary-700 underline' : 'text-gray-900'}`}
                    title="Показать метрики"
                  >
                    {c.name}
                  </button>
                  <span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full">{c.status}</span>
                  <span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full">{c.channel}</span>
                </div>
                {c.description && <p className="text-gray-600 text-sm mt-1">{c.description}</p>}
              </div>
              <div className="flex items-center gap-2">
                <select
                  className="px-2 py-1 border border-gray-300 rounded-lg text-sm"
                  onChange={(e) => {
                    setSelectedCampaignId(c.id)
                    ;(e.currentTarget as any).dataset.audienceId = e.target.value
                  }}
                >
                  <option value="">Все клиенты</option>
                  {(audiences || []).map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min={1}
                  defaultValue={100}
                  className="w-20 px-2 py-1 border border-gray-300 rounded-lg text-sm"
                  placeholder="Лимит"
                  onChange={() => {}}
                  data-limit-input
                />
                <button
                  onClick={(ev) => {
                    const container = (ev.currentTarget.parentElement as HTMLElement)
                    const select = container.querySelector('select') as HTMLSelectElement
                    const limitInput = container.querySelector('input[data-limit-input]') as HTMLInputElement
                    let audienceId = select?.value ? parseInt(select.value) : undefined
                    let limit = limitInput?.value ? parseInt(limitInput.value) : 100
                    // Apply campaign defaults if not specified
                    const defaults = (c.params || {}) as any
                    if (!audienceId && defaults.default_audience_id) {
                      audienceId = parseInt(String(defaults.default_audience_id))
                    }
                    if ((!limit || Number.isNaN(limit)) && defaults.default_limit) {
                      limit = parseInt(String(defaults.default_limit))
                    }
                    startRun.mutate({ campaignId: c.id, audienceId, limit })
                  }}
                  className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
                >
                  Запустить
                </button>
                <button onClick={() => beginEditCampaign(c)} className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm">
                  Редактировать
                </button>
                <button
                  onClick={() => {
                    if (confirm('Удалить кампанию?')) deleteCampaign.mutate(c.id)
                  }}
                  className="px-3 py-1 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 text-sm"
                >
                  Удалить
                </button>
              </div>
            </div>
          ))}
          {campaigns && campaigns.length === 0 && <div className="p-4 text-gray-500">Кампаний пока нет</div>}
        </div>
      </div>

      {!!selectedCampaignId && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Итоги кампании</h3>
              <button
                onClick={() => {
                  queryClient.invalidateQueries({ queryKey: ['mkt-summary', selectedCampaignId] })
                }}
                className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
              >
                Обновить
              </button>
            </div>
            {summary ? (
              <div className="space-y-2 text-sm text-gray-800">
                <div>Запусков: {summary.total_runs}</div>
                <div>Уникальных клиентов: {summary.unique_clients}</div>
                <div>Доставлено: {summary.sent_total} • Ошибок: {summary.failed_total}</div>
                <div>Конверсии (оплата): {summary.conversions} • Конверсия: {(summary.conversion_rate * 100).toFixed(1)}%</div>
                <div className="text-gray-600">
                  По каналам:
                  <ul className="list-disc ml-6">
                    {Object.entries(summary.by_channel || {}).map(([ch, m]: any) => (
                      <li key={ch}>
                        {ch}: total {m.total}, sent {m.sent}, failed {m.failed}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="text-gray-600">
                  Последний запуск: {summary.last_run_started_at ? new Date(summary.last_run_started_at).toLocaleString('ru-RU') : '—'}
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-sm">Нет данных</div>
            )}
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Запуски (runs)</h3>
              <button
                onClick={() => queryClient.invalidateQueries({ queryKey: ['mkt-runs', selectedCampaignId] })}
                className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
              >
                Обновить
              </button>
            </div>
            <div className="divide-y border border-gray-200 rounded-lg">
              {(runs || []).map((r) => (
                <div key={r.id} className="p-3 text-sm flex items-center justify-between">
                  <div className="text-gray-800">
                    <span className="font-medium">#{r.id}</span> • {r.status} • {r.started_at ? new Date(r.started_at).toLocaleString('ru-RU') : ''}
                  </div>
                  <div className="text-gray-600">
                    total: {r.total} • sent: {r.sent} • errors: {r.errors}
                  </div>
                </div>
              ))}
              {runs && runs.length === 0 && <div className="p-3 text-gray-500 text-sm">Запусков пока нет</div>}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Последние доставки</h3>
              <button
                onClick={() => queryClient.invalidateQueries({ queryKey: ['mkt-deliveries', selectedCampaignId] })}
                className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
              >
                Обновить
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Время</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Run</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Клиент</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Канал</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Статус</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {(deliveries || []).map((d) => (
                    <tr key={d.id} className="text-sm">
                      <td className="px-4 py-2">{d.created_at ? new Date(d.created_at).toLocaleString('ru-RU') : ''}</td>
                      <td className="px-4 py-2">{d.run_id || '—'}</td>
                      <td className="px-4 py-2">#{d.client_id}</td>
                      <td className="px-4 py-2">{d.channel}</td>
                      <td className="px-4 py-2">{d.status}</td>
                    </tr>
                  ))}
                  {deliveries && deliveries.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-3 text-gray-500">
                        Нет доставок
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6 lg:col-span-3">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Динамика доставок (14 дней)</h3>
              <button
                onClick={() => queryClient.invalidateQueries({ queryKey: ['mkt-timeseries', selectedCampaignId] })}
                className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
              >
                Обновить
              </button>
            </div>
            <div className="space-y-2">
              {(timeseries?.series || []).length === 0 && <div className="text-gray-500 text-sm">Нет данных</div>}
              {(timeseries?.series || []).map((row) => {
                const total = row.total || 0
                const maxBar = Math.max(1, total)
                const sentPct = total ? Math.round((row.sent / total) * 100) : 0
                const failedPct = total ? Math.round((row.failed / total) * 100) : 0
                return (
                  <div key={row.date} className="text-sm">
                    <div className="flex items-center gap-3">
                      <div className="w-28 text-gray-700">{row.date}</div>
                      <div className="flex-1 h-3 bg-gray-100 rounded">
                        <div className="h-3 bg-green-500 rounded-l" style={{ width: `${sentPct}%` }} />
                        <div className="h-3 bg-red-400" style={{ width: `${failedPct}%` }} />
                      </div>
                      <div className="w-24 text-right text-gray-600">{total} шт.</div>
                    </div>
                    <div className="ml-28 text-xs text-gray-500">
                      sent: {row.sent}, failed: {row.failed}, tg: {row.telegram}, email: {row.email}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
      {editingCampaign && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{editingCampaign.id > 0 ? 'Редактирование кампании' : 'Новая кампания'}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Название *</label>
              <input
                type="text"
                value={campaignForm?.name || ''}
                onChange={(e) => setCampaignForm({ ...(campaignForm as Campaign), name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Канал</label>
              <select
                value={campaignForm?.channel || 'both'}
                onChange={(e) => setCampaignForm({ ...(campaignForm as Campaign), channel: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="telegram">Telegram</option>
                <option value="email">Email</option>
                <option value="both">Оба</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Статус</label>
              <select
                value={campaignForm?.status || 'draft'}
                onChange={(e) => setCampaignForm({ ...(campaignForm as Campaign), status: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="draft">draft</option>
                <option value="scheduled">scheduled</option>
                <option value="paused">paused</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Время запуска (schedule_at)</label>
              <input
                type="datetime-local"
                value={campaignForm?.schedule_at ? new Date(campaignForm.schedule_at).toISOString().slice(0, 16) : ''}
                onChange={(e) => {
                  const val = e.target.value
                  const iso = val ? new Date(val).toISOString() : null
                  setCampaignForm({ ...(campaignForm as Campaign), schedule_at: iso })
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
              <textarea
                rows={2}
                value={campaignForm?.description || ''}
                onChange={(e) => setCampaignForm({ ...(campaignForm as Campaign), description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Параметры (JSON)</label>
              <textarea
                rows={5}
                value={JSON.stringify(campaignForm?.params || {}, null, 2)}
                onChange={(e) =>
                  setCampaignForm({
                    ...(campaignForm as Campaign),
                    params: parseJson(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Дефолтный сегмент</label>
              <select
                value={String(((campaignForm?.params || {}) as any).default_audience_id || '')}
                onChange={(e) => {
                  const val = e.target.value ? parseInt(e.target.value) : undefined
                  const next = { ...((campaignForm?.params || {}) as any) }
                  if (val) next.default_audience_id = val
                  else delete next.default_audience_id
                  setCampaignForm({ ...(campaignForm as Campaign), params: next })
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">— не задан —</option>
                {(audiences || []).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">Используется в быстром запуске, если сегмент не выбран вручную.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Дефолтный лимит</label>
              <input
                type="number"
                min={1}
                value={Number(((campaignForm?.params || {}) as any).default_limit || 100)}
                onChange={(e) => {
                  const val = e.target.value ? parseInt(e.target.value) : 100
                  const next = { ...((campaignForm?.params || {}) as any) }
                  next.default_limit = val
                  setCampaignForm({ ...(campaignForm as Campaign), params: next })
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
              <p className="mt-1 text-xs text-gray-500">Количество получателей по умолчанию для быстрого запуска.</p>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={submitCampaign} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700" disabled={createCampaign.isPending || updateCampaign.isPending}>
              {editingCampaign.id > 0 ? 'Сохранить' : 'Создать'}
            </button>
            <button onClick={() => { setEditingCampaign(null); setCampaignForm(null as unknown as Campaign) }} className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100">
              Отмена
            </button>
          </div>
        </div>
      )}

      {/* Audiences */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Сегменты</h2>
          <button onClick={beginCreateAudience} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
            + Новый сегмент
          </button>
        </div>
        <div className="divide-y border border-gray-200 rounded-lg">
          {(audiences || []).map((a) => (
            <div key={a.id} className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div>
                <div className="font-semibold text-gray-900">{a.name}</div>
                {a.description && <div className="text-gray-600 text-sm">{a.description}</div>}
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => beginEditAudience(a)} className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm">
                  Редактировать
                </button>
                <button
                  onClick={() => {
                    if (confirm('Удалить сегмент?')) deleteAudience.mutate(a.id)
                  }}
                  className="px-3 py-1 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 text-sm"
                >
                  Удалить
                </button>
              </div>
            </div>
          ))}
          {audiences && audiences.length === 0 && <div className="p-4 text-gray-500">Сегментов пока нет</div>}
        </div>
        <div className="mt-4 text-xs text-gray-600">
          Подсказки по фильтрам (JSON): {"{ status: 'client', has_telegram: true, has_email: false }"}.
          Поддерживаются ключи: status, has_telegram, has_email. Доп. фильтры будут расширяться.
        </div>
      </div>

      {editingAudience && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{editingAudience.id > 0 ? 'Редактирование сегмента' : 'Новый сегмент'}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Название *</label>
              <input
                type="text"
                value={audienceForm?.name || ''}
                onChange={(e) => setAudienceForm({ ...(audienceForm as Audience), name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
              <textarea
                rows={2}
                value={audienceForm?.description || ''}
                onChange={(e) => setAudienceForm({ ...(audienceForm as Audience), description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Фильтр (JSON)</label>
              <textarea
                rows={6}
                value={JSON.stringify(audienceForm?.filter_json || {}, null, 2)}
                onChange={(e) =>
                  setAudienceForm({
                    ...(audienceForm as Audience),
                    filter_json: parseJson(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={submitAudience} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700" disabled={createAudience.isPending || updateAudience.isPending}>
              {editingAudience.id > 0 ? 'Сохранить' : 'Создать'}
            </button>
            <button onClick={() => { setEditingAudience(null); setAudienceForm(null as unknown as Audience) }} className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100">
              Отмена
            </button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Сообщения</h2>
          <button onClick={beginCreateMessage} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
            + Новое сообщение
          </button>
        </div>
        <div className="divide-y border border-gray-200 rounded-lg">
          {(messages || []).map((m) => (
            <div key={m.id} className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div>
                <div className="font-semibold text-gray-900">#{m.id} • Кампания {m.campaign_id}</div>
                {m.title && <div className="text-gray-700 text-sm">Тема: {m.title}</div>}
                <div className="text-gray-600 text-sm line-clamp-2">{m.body_text}</div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => beginEditMessage(m)} className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm">
                  Редактировать
                </button>
                <button
                  onClick={() => {
                    if (confirm('Удалить сообщение?')) deleteMessage.mutate(m.id)
                  }}
                  className="px-3 py-1 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 text-sm"
                >
                  Удалить
                </button>
              </div>
            </div>
          ))}
          {messages && messages.length === 0 && <div className="p-4 text-gray-500">Сообщений пока нет</div>}
        </div>
      </div>

      {editingMessage && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{editingMessage.id > 0 ? 'Редактирование сообщения' : 'Новое сообщение'}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Кампания</label>
              <select
                value={messageForm?.campaign_id || ''}
                onChange={(e) => setMessageForm({ ...(messageForm as Message), campaign_id: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                {(campaigns || []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Тема</label>
              <input
                type="text"
                value={messageForm?.title || ''}
                onChange={(e) => setMessageForm({ ...(messageForm as Message), title: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Текст сообщения *</label>
              <textarea
                rows={6}
                value={messageForm?.body_text || ''}
                onChange={(e) => setMessageForm({ ...(messageForm as Message), body_text: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={submitMessage} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700" disabled={createMessage.isPending || updateMessage.isPending}>
              {editingMessage.id > 0 ? 'Сохранить' : 'Создать'}
            </button>
            <button onClick={() => { setEditingMessage(null); setMessageForm(null as unknown as Message) }} className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100">
              Отмена
            </button>
          </div>
        </div>
      )}

    {/* Promo Codes */}
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Промокоды</h2>
        <button
          onClick={() => {
            setEditingPromo(null)
            resetPromoForm()
          }}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          + Новый промокод
        </button>
      </div>
      <div className="divide-y border border-gray-200 rounded-lg">
        {(promos || []).map((p) => (
          <div key={p.id} className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900">{p.code}</span>
                <span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full">
                  {p.discount_type === 'percent' ? `${p.discount_value}%` : `${p.discount_value}₽`}
                </span>
                <span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full">{p.is_active ? 'активен' : 'выключен'}</span>
              </div>
              {p.description && <p className="text-sm text-gray-600">{p.description}</p>}
              <p className="text-xs text-gray-500">
                использовано {p.used_count}
                {p.max_usage ? ` / ${p.max_usage}` : ''}
              </p>
              {p.valid_from && (
                <p className="text-xs text-gray-500">
                  с {new Date(p.valid_from).toLocaleString('ru-RU')}
                </p>
              )}
              {p.valid_to && (
                <p className="text-xs text-gray-500">
                  до {new Date(p.valid_to).toLocaleString('ru-RU')}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setEditingPromo(p)
                  setPromoForm({
                    code: p.code,
                    description: p.description || '',
                    discount_type: p.discount_type,
                    discount_value: p.discount_value,
                    max_usage: p.max_usage || 0,
                    per_client_limit: p.per_client_limit || 0,
                    valid_from: p.valid_from ? new Date(p.valid_from).toISOString().slice(0, 16) : '',
                    valid_to: p.valid_to ? new Date(p.valid_to).toISOString().slice(0, 16) : '',
                    is_active: p.is_active,
                  })
                }}
                className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
              >
                Редактировать
              </button>
              <button
                onClick={() => {
                  if (confirm('Удалить промокод?')) deletePromo.mutate(p.id)
                }}
                className="px-3 py-1 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 text-sm"
              >
                Удалить
              </button>
            </div>
          </div>
        ))}
        {promos && promos.length === 0 && <div className="p-4 text-gray-500">Промокодов пока нет</div>}
      </div>
    </div>

    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">{editingPromo ? 'Редактирование промокода' : 'Новый промокод'}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Код *</label>
          <input
            type="text"
            value={promoForm.code}
            onChange={(e) => setPromoForm({ ...promoForm, code: e.target.value.toUpperCase() })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Скидка</label>
          <div className="flex gap-2">
            <select
              value={promoForm.discount_type}
              onChange={(e) => setPromoForm({ ...promoForm, discount_type: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="percent">% (процент)</option>
              <option value="fixed">₽ (фиксированная)</option>
            </select>
            <input
              type="number"
              value={promoForm.discount_value}
              onChange={(e) => setPromoForm({ ...promoForm, discount_value: parseFloat(e.target.value) })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
          <input
            type="text"
            value={promoForm.description}
            onChange={(e) => setPromoForm({ ...promoForm, description: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Макс. использование (0 = без лимита)</label>
          <input
            type="number"
            value={promoForm.max_usage}
            onChange={(e) => setPromoForm({ ...promoForm, max_usage: parseInt(e.target.value) || 0 })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Лимит на клиента</label>
          <input
            type="number"
            value={promoForm.per_client_limit}
            onChange={(e) => setPromoForm({ ...promoForm, per_client_limit: parseInt(e.target.value) || 0 })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={promoForm.is_active}
            onChange={(e) => setPromoForm({ ...promoForm, is_active: e.target.checked })}
          />
          <span className="text-sm text-gray-700">Активен</span>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Начало действия</label>
          <input
            type="datetime-local"
            value={promoForm.valid_from}
            onChange={(e) => setPromoForm({ ...promoForm, valid_from: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Окончание действия</label>
          <input
            type="datetime-local"
            value={promoForm.valid_to}
            onChange={(e) => setPromoForm({ ...promoForm, valid_to: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
      </div>
      <div className="mt-4 flex gap-2">
        <button
          onClick={() => {
            if (!promoForm.code.trim()) {
              alert('Введите код')
              return
            }
            const payload = {
              ...promoForm,
              discount_value: Number(promoForm.discount_value),
              max_usage: promoForm.max_usage || null,
              per_client_limit: promoForm.per_client_limit || null,
              valid_from: promoForm.valid_from ? new Date(promoForm.valid_from).toISOString() : null,
              valid_to: promoForm.valid_to ? new Date(promoForm.valid_to).toISOString() : null,
            }
            if (editingPromo) {
              updatePromo.mutate({ id: editingPromo.id, payload })
            } else {
              createPromo.mutate(payload)
            }
          }}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          disabled={createPromo.isPending || updatePromo.isPending}
        >
          {editingPromo ? 'Сохранить' : 'Создать'}
        </button>
        {editingPromo && (
          <button
            onClick={() => {
              setEditingPromo(null)
              resetPromoForm()
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
          >
            Отмена
          </button>
        )}
      </div>
    </div>

    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Проверка промокода</h2>
      <div className="flex flex-col md:flex-row gap-3">
        <input
          type="text"
          placeholder="Код"
          value={checkCode.code}
          onChange={(e) => setCheckCode({ ...checkCode, code: e.target.value.toUpperCase() })}
          className="px-3 py-2 border border-gray-300 rounded-lg"
        />
        <input
          type="number"
          placeholder="Сумма"
          value={checkCode.amount}
          onChange={(e) => setCheckCode({ ...checkCode, amount: parseFloat(e.target.value) || 0 })}
          className="px-3 py-2 border border-gray-300 rounded-lg"
        />
        <button
          onClick={async () => {
            try {
              const res = await checkPromo.mutateAsync({ code: checkCode.code, amount: checkCode.amount })
              setCheckCode({
                ...checkCode,
                result: `Скидка ${res.discount.toFixed(2)} ₽. Итог: ${res.final_amount.toFixed(2)} ₽`,
              })
            } catch (error: any) {
              const detail = error?.response?.data?.detail || 'Ошибка проверки'
              setCheckCode({ ...checkCode, result: detail })
            }
          }}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          Проверить
        </button>
      </div>
      {checkCode.result && <p className="mt-2 text-sm text-gray-700">{checkCode.result}</p>}
    </div>
    </div>
  )
}

export default Marketing


