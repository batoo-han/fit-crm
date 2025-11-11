import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'

type FaqItem = {
  id: number
  question: string
  answer: string
  category?: string | null
  keywords?: string[] | null
  priority: number
  is_active: boolean
  use_count: number
}

type SalesScenario = {
  id: number
  name: string
  description?: string | null
  trigger_type: string
  trigger_conditions?: Record<string, unknown> | null
  message_template: string
  action_type?: string | null
  is_active: boolean
  priority: number
  use_count: number
}

const buildKeywordsString = (keywords?: string[] | null) => (keywords && keywords.length > 0 ? keywords.join(', ') : '')

const parseKeywords = (value: string) =>
  value
    .split(',')
    .map((kw) => kw.trim())
    .filter((kw) => kw.length > 0)

const safeJsonParse = (value: string) => {
  try {
    if (value.trim() === '') {
      return null
    }
    return JSON.parse(value)
  } catch {
    return null
  }
}

const formatJson = (value: Record<string, unknown> | null | undefined) => {
  if (!value) return ''
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return ''
  }
}

const AIAgentSettings = () => {
  const [activeTab, setActiveTab] = useState<'faq' | 'scenarios'>('faq')
  const [faqSearch, setFaqSearch] = useState('')
  const [scenarioSearch, setScenarioSearch] = useState('')
  const [editingFaq, setEditingFaq] = useState<FaqItem | null>(null)
  const [editingScenario, setEditingScenario] = useState<SalesScenario | null>(null)

  const queryClient = useQueryClient()

  const { data: faqList, isLoading: faqLoading, isError: faqError } = useQuery({
    queryKey: ['faq'],
    queryFn: async () => {
      const response = await api.get('/faq')
      return response.data as FaqItem[]
    },
  })

  const { data: scenarioList, isLoading: scenarioLoading, isError: scenarioError } = useQuery({
    queryKey: ['sales-scenarios'],
    queryFn: async () => {
      const response = await api.get('/sales-scenarios')
      return response.data as SalesScenario[]
    },
  })

  const faqForm = editingFaq || {
    id: 0,
    question: '',
    answer: '',
    category: '',
    keywords: [] as string[],
    priority: 0,
    is_active: true,
    use_count: 0,
  }

  const scenarioForm = editingScenario || {
    id: 0,
    name: '',
    description: '',
    trigger_type: 'client_action',
    trigger_conditions: {} as Record<string, unknown> | null,
    message_template: '',
    action_type: '',
    is_active: true,
    priority: 0,
    use_count: 0,
  }

  const createFaqMutation = useMutation({
    mutationFn: async (payload: Partial<FaqItem> & { keywords?: string[] }) => {
      const response = await api.post('/faq', payload)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['faq'] })
      setEditingFaq(null)
    },
  })

  const updateFaqMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Partial<FaqItem> & { keywords?: string[] } }) => {
      const response = await api.put(`/faq/${id}`, payload)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['faq'] })
      setEditingFaq(null)
    },
  })

  const deleteFaqMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await api.delete(`/faq/${id}`)
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['faq'] }),
  })

  const createScenarioMutation = useMutation({
    mutationFn: async (payload: Partial<SalesScenario>) => {
      const response = await api.post('/sales-scenarios', payload)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales-scenarios'] })
      setEditingScenario(null)
    },
  })

  const updateScenarioMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Partial<SalesScenario> }) => {
      const response = await api.put(`/sales-scenarios/${id}`, payload)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales-scenarios'] })
      setEditingScenario(null)
    },
  })

  const deleteScenarioMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await api.delete(`/sales-scenarios/${id}`)
      return response.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sales-scenarios'] }),
  })

  const downloadJson = (filename: string, data: unknown) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleImportFaq = async (file: File) => {
    const text = await file.text()
    const arr = JSON.parse(text) as Array<Partial<FaqItem>>
    for (const item of arr) {
      const payload = {
        question: item.question || '',
        answer: item.answer || '',
        category: item.category || '',
        keywords: item.keywords || [],
        priority: item.priority ?? 0,
        is_active: item.is_active ?? true,
      }
      await createFaqMutation.mutateAsync(payload)
    }
    alert('FAQ импортированы')
  }

  const handleImportScenarios = async (file: File) => {
    const text = await file.text()
    const arr = JSON.parse(text) as Array<Partial<SalesScenario>>
    for (const item of arr) {
      const payload: Partial<SalesScenario> = {
        name: item.name || '',
        description: item.description || '',
        trigger_type: item.trigger_type || 'client_action',
        trigger_conditions: item.trigger_conditions || {},
        message_template: item.message_template || '',
        action_type: item.action_type || '',
        is_active: item.is_active ?? true,
        priority: item.priority ?? 0,
      }
      await createScenarioMutation.mutateAsync(payload)
    }
    alert('Сценарии импортированы')
  }

  const filteredFaqList = useMemo(() => {
    if (!faqList) return []
    if (!faqSearch) return faqList
    const needle = faqSearch.toLowerCase()
    return faqList.filter(
      (item) =>
        item.question.toLowerCase().includes(needle) ||
        item.answer.toLowerCase().includes(needle) ||
        item.category?.toLowerCase().includes(needle) ||
        item.keywords?.some((kw) => kw.toLowerCase().includes(needle))
    )
  }, [faqList, faqSearch])

  const filteredScenarioList = useMemo(() => {
    if (!scenarioList) return []
    if (!scenarioSearch) return scenarioList
    const needle = scenarioSearch.toLowerCase()
    return scenarioList.filter(
      (item) =>
        item.name.toLowerCase().includes(needle) ||
        item.description?.toLowerCase().includes(needle) ||
        item.trigger_type.toLowerCase().includes(needle) ||
        JSON.stringify(item.trigger_conditions || {})
          .toLowerCase()
          .includes(needle)
    )
  }, [scenarioList, scenarioSearch])

  const handleFaqSubmit = () => {
    const payload = {
      question: faqForm.question,
      answer: faqForm.answer,
      category: faqForm.category || undefined,
      keywords: faqForm.keywords || [],
      priority: faqForm.priority ?? 0,
      is_active: faqForm.is_active,
    }
    if (!faqForm.question || !faqForm.answer) {
      alert('Вопрос и ответ обязательны')
      return
    }
    if (faqForm.id) {
      updateFaqMutation.mutate({ id: faqForm.id, payload })
    } else {
      createFaqMutation.mutate(payload)
    }
  }

  const handleScenarioSubmit = () => {
    if (!scenarioForm.name || !scenarioForm.message_template) {
      alert('Название и шаблон сообщения обязательны')
      return
    }
    const payload = {
      name: scenarioForm.name,
      description: scenarioForm.description || undefined,
      trigger_type: scenarioForm.trigger_type,
      trigger_conditions: scenarioForm.trigger_conditions || null,
      message_template: scenarioForm.message_template,
      action_type: scenarioForm.action_type || undefined,
      priority: scenarioForm.priority ?? 0,
      is_active: scenarioForm.is_active,
    }
    if (scenarioForm.id) {
      updateScenarioMutation.mutate({ id: scenarioForm.id, payload })
    } else {
      createScenarioMutation.mutate(payload)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">AI‑агент: FAQ и сценарии</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('faq')}
            className={`px-3 py-1 rounded ${activeTab === 'faq' ? 'bg-primary-600 text-white' : 'bg-gray-200'}`}
          >FAQ</button>
          <button
            onClick={() => setActiveTab('scenarios')}
            className={`px-3 py-1 rounded ${activeTab === 'scenarios' ? 'bg-primary-600 text-white' : 'bg-gray-200'}`}
          >Сценарии</button>
        </div>
      </div>

      {activeTab === 'faq' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">Всего: {faqList?.length || 0}</div>
            <div className="flex items-center gap-2">
              <button onClick={() => downloadJson('faq_export.json', faqList || [])} className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm">Экспорт FAQ</button>
              <label className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm cursor-pointer">
                Импорт FAQ
                <input type="file" accept="application/json" className="hidden" onChange={(e) => e.target.files && handleImportFaq(e.target.files[0])} />
              </label>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow">
            <div className="border-b border-gray-200">
              <nav className="flex -mb-px">
                <button
                  onClick={() => setActiveTab('faq')}
                  className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'faq'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  ❓ FAQ (База знаний)
                </button>
                <button
                  onClick={() => setActiveTab('scenarios')}
                  className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'scenarios'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  🤝 Сценарии продаж
                </button>
              </nav>
            </div>

            <div className="p-6">
              <div className="space-y-6">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">FAQ</h2>
                    <p className="text-gray-500">Ответы, которые использует AI-агент в первую очередь.</p>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Поиск по вопросу, категории, ключевым словам..."
                      value={faqSearch}
                      onChange={(e) => setFaqSearch(e.target.value)}
                      className="px-4 py-2 border border-gray-300 rounded-lg min-w-[250px]"
                    />
                    <button
                      onClick={() =>
                        setEditingFaq({
                          id: 0,
                          question: '',
                          answer: '',
                          category: '',
                          keywords: [],
                          priority: 0,
                          is_active: true,
                          use_count: 0,
                        })
                      }
                      className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                    >
                      + Добавить вопрос
                    </button>
                  </div>
                </div>

                {faqLoading && <p>Загрузка FAQ...</p>}
                {faqError && <p className="text-red-600">Ошибка при загрузке FAQ</p>}

                {!faqLoading && !faqError && (
                  <div className="grid lg:grid-cols-2 gap-6">
                    <div className="border border-gray-200 rounded-lg divide-y max-h-[600px] overflow-y-auto">
                      {filteredFaqList.length === 0 && (
                        <p className="p-4 text-gray-500">
                          {faqList && faqList.length > 0 ? 'По вашему запросу ничего не найдено' : 'FAQ пока пустой'}
                        </p>
                      )}
                      {filteredFaqList.map((faq) => (
                        <div key={faq.id} className="p-4 hover:bg-gray-50 transition-colors">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <p className="font-semibold text-gray-900">{faq.question}</p>
                              <p className="text-sm text-gray-500 mt-1 line-clamp-3">{faq.answer}</p>
                              <div className="flex flex-wrap gap-2 mt-3 text-xs text-gray-500">
                                {faq.category && <span className="px-2 py-1 bg-gray-100 rounded-full">{faq.category}</span>}
                                <span className="px-2 py-1 bg-gray-100 rounded-full">Приоритет: {faq.priority}</span>
                                <span className="px-2 py-1 bg-gray-100 rounded-full">Использований: {faq.use_count}</span>
                                <span
                                  className={`px-2 py-1 rounded-full ${
                                    faq.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-600'
                                  }`}
                                >
                                  {faq.is_active ? 'Активен' : 'Выключен'}
                                </span>
                              </div>
                            </div>
                            <div className="flex flex-col gap-2">
                              <button
                                onClick={() => setEditingFaq(faq)}
                                className="text-primary-600 hover:underline text-sm"
                              >
                                Редактировать
                              </button>
                              <button
                                onClick={() => {
                                  if (confirm('Удалить этот вопрос?')) {
                                    deleteFaqMutation.mutate(faq.id)
                                  }
                                }}
                                className="text-red-600 hover:underline text-sm"
                              >
                                Удалить
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">
                        {faqForm.id ? 'Редактирование FAQ' : 'Новый вопрос FAQ'}
                      </h3>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Вопрос *</label>
                          <textarea
                            value={faqForm.question}
                            onChange={(e) => setEditingFaq({ ...faqForm, question: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                            rows={3}
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Ответ *</label>
                          <textarea
                            value={faqForm.answer}
                            onChange={(e) => setEditingFaq({ ...faqForm, answer: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                            rows={6}
                          />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Категория</label>
                            <input
                              type="text"
                              value={faqForm.category || ''}
                              onChange={(e) => setEditingFaq({ ...faqForm, category: e.target.value })}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                              placeholder="Например: pricing, training..."
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Приоритет</label>
                            <input
                              type="number"
                              value={faqForm.priority ?? 0}
                              onChange={(e) =>
                                setEditingFaq({
                                  ...faqForm,
                                  priority: Number.isNaN(parseInt(e.target.value, 10))
                                    ? 0
                                    : parseInt(e.target.value, 10),
                                })
                              }
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Ключевые слова (через запятую)
                          </label>
                          <input
                            type="text"
                            value={buildKeywordsString(faqForm.keywords)}
                            onChange={(e) =>
                              setEditingFaq({
                                ...faqForm,
                                keywords: parseKeywords(e.target.value),
                              })
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                            placeholder="цена, стоимость, тариф"
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            id="faq_is_active"
                            checked={faqForm.is_active}
                            onChange={(e) => setEditingFaq({ ...faqForm, is_active: e.target.checked })}
                          />
                          <label htmlFor="faq_is_active" className="text-sm text-gray-700">
                            Вопрос активен
                          </label>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={handleFaqSubmit}
                            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                            disabled={createFaqMutation.isPending || updateFaqMutation.isPending}
                          >
                            {faqForm.id ? 'Сохранить' : 'Добавить'}
                          </button>
                          <button
                            onClick={() => setEditingFaq(null)}
                            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
                          >
                            Отмена
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'scenarios' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">Всего: {scenarioList?.length || 0}</div>
            <div className="flex items-center gap-2">
              <button onClick={() => downloadJson('scenarios_export.json', scenarioList || [])} className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm">Экспорт сценариев</button>
              <label className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm cursor-pointer">
                Импорт сценариев
                <input type="file" accept="application/json" className="hidden" onChange={(e) => e.target.files && handleImportScenarios(e.target.files[0])} />
              </label>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow">
            <div className="border-b border-gray-200">
              <nav className="flex -mb-px">
                <button
                  onClick={() => setActiveTab('faq')}
                  className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'faq'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  ❓ FAQ (База знаний)
                </button>
                <button
                  onClick={() => setActiveTab('scenarios')}
                  className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'scenarios'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  🤝 Сценарии продаж
                </button>
              </nav>
            </div>

            <div className="p-6">
              <div className="space-y-6">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">Сценарии продаж</h2>
                    <p className="text-gray-500">Шаблоны предложений, которые AI-агент отправляет клиентам.</p>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Поиск по названию, описанию, условиям..."
                      value={scenarioSearch}
                      onChange={(e) => setScenarioSearch(e.target.value)}
                      className="px-4 py-2 border border-gray-300 rounded-lg min-w-[250px]"
                    />
                    <button
                      onClick={() =>
                        setEditingScenario({
                          id: 0,
                          name: '',
                          description: '',
                          trigger_type: 'client_action',
                          trigger_conditions: {},
                          message_template: '',
                          action_type: '',
                          is_active: true,
                          priority: 0,
                          use_count: 0,
                        })
                      }
                      className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                    >
                      + Новый сценарий
                    </button>
                  </div>
                </div>

                {scenarioLoading && <p>Загрузка сценариев...</p>}
                {scenarioError && <p className="text-red-600">Ошибка при загрузке сценариев</p>}

                {!scenarioLoading && !scenarioError && (
                  <div className="grid lg:grid-cols-2 gap-6">
                    <div className="border border-gray-200 rounded-lg divide-y max-h-[600px] overflow-y-auto">
                      {filteredScenarioList.length === 0 && (
                        <p className="p-4 text-gray-500">
                          {scenarioList && scenarioList.length > 0
                            ? 'По вашему запросу ничего не найдено'
                            : 'Сценарии продаж пока не настроены'}
                        </p>
                      )}
                      {filteredScenarioList.map((scenario) => (
                        <div key={scenario.id} className="p-4 hover:bg-gray-50 transition-colors">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <p className="font-semibold text-gray-900">{scenario.name}</p>
                              {scenario.description && (
                                <p className="text-sm text-gray-500 mt-1">{scenario.description}</p>
                              )}
                              <div className="mt-2 text-xs text-gray-500 space-y-1">
                                <p>
                                  <span className="font-semibold">Триггер:</span> {scenario.trigger_type}
                                </p>
                                {scenario.trigger_conditions && (
                                  <p className="whitespace-pre-wrap">
                                    <span className="font-semibold">Условия:</span>{' '}
                                    {JSON.stringify(scenario.trigger_conditions, null, 2)}
                                  </p>
                                )}
                                <p className="whitespace-pre-wrap text-gray-600 mt-2">
                                  <span className="font-semibold text-gray-700">Сообщение:</span>{' '}
                                  {scenario.message_template}
                                </p>
                                <div className="flex flex-wrap gap-2 mt-2">
                                  {scenario.action_type && (
                                    <span className="px-2 py-1 bg-gray-100 rounded-full text-xs">
                                      Действие: {scenario.action_type}
                                    </span>
                                  )}
                                  <span className="px-2 py-1 bg-gray-100 rounded-full text-xs">
                                    Приоритет: {scenario.priority}
                                  </span>
                                  <span className="px-2 py-1 bg-gray-100 rounded-full text-xs">
                                    Использований: {scenario.use_count}
                                  </span>
                                  <span
                                    className={`px-2 py-1 rounded-full text-xs ${
                                      scenario.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-600'
                                    }`}
                                  >
                                    {scenario.is_active ? 'Активен' : 'Выключен'}
                                  </span>
                                </div>
                              </div>
                            </div>
                            <div className="flex flex-col gap-2">
                              <button
                                onClick={() => setEditingScenario(scenario)}
                                className="text-primary-600 hover:underline text-sm"
                              >
                                Редактировать
                              </button>
                              <button
                                onClick={() => {
                                  if (confirm('Удалить этот сценарий?')) {
                                    deleteScenarioMutation.mutate(scenario.id)
                                  }
                                }}
                                className="text-red-600 hover:underline text-sm"
                              >
                                Удалить
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">
                        {scenarioForm.id ? 'Редактирование сценария' : 'Новый сценарий'}
                      </h3>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Название *</label>
                          <input
                            type="text"
                            value={scenarioForm.name}
                            onChange={(e) => setEditingScenario({ ...scenarioForm, name: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
                          <textarea
                            value={scenarioForm.description || ''}
                            onChange={(e) => setEditingScenario({ ...scenarioForm, description: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                            rows={2}
                          />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Тип триггера *</label>
                            <select
                              value={scenarioForm.trigger_type}
                              onChange={(e) => setEditingScenario({ ...scenarioForm, trigger_type: e.target.value })}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                            >
                              <option value="client_action">Действие клиента</option>
                              <option value="pipeline_stage">Этап воронки</option>
                              <option value="time_based">По времени</option>
                              <option value="custom">Custom</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Приоритет</label>
                            <input
                              type="number"
                              value={scenarioForm.priority ?? 0}
                              onChange={(e) =>
                                setEditingScenario({
                                  ...scenarioForm,
                                  priority: Number.isNaN(parseInt(e.target.value, 10))
                                    ? 0
                                    : parseInt(e.target.value, 10),
                                })
                              }
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Условия триггера (JSON)
                          </label>
                          <textarea
                            value={formatJson(scenarioForm.trigger_conditions)}
                            onChange={(e) =>
                              setEditingScenario({
                                ...scenarioForm,
                                trigger_conditions: safeJsonParse(e.target.value),
                              })
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
                            rows={5}
                            placeholder={`{\n  "pipeline_stage": "Консультация"\n}`}
                          />
                          <p className="text-xs text-gray-500 mt-1">
                            Например: &#123; "pipeline_stage": "Принимают решение", "has_free_program": true &#125;
                          </p>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Шаблон сообщения *
                          </label>
                          <textarea
                            value={scenarioForm.message_template}
                            onChange={(e) =>
                              setEditingScenario({ ...scenarioForm, message_template: e.target.value })
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                            rows={6}
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Тип действия</label>
                          <input
                            type="text"
                            value={scenarioForm.action_type || ''}
                            onChange={(e) => setEditingScenario({ ...scenarioForm, action_type: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                            placeholder="Например: suggest_program"
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            id="scenario_is_active"
                            checked={scenarioForm.is_active}
                            onChange={(e) => setEditingScenario({ ...scenarioForm, is_active: e.target.checked })}
                          />
                          <label htmlFor="scenario_is_active" className="text-sm text-gray-700">
                            Сценарий активен
                          </label>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={handleScenarioSubmit}
                            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                            disabled={createScenarioMutation.isPending || updateScenarioMutation.isPending}
                          >
                            {scenarioForm.id ? 'Сохранить' : 'Добавить'}
                          </button>
                          <button
                            onClick={() => setEditingScenario(null)}
                            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
                          >
                            Отмена
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AIAgentSettings


