import { useState, useEffect, useCallback, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'

const LLM_PROVIDERS = [
  { value: 'yandex', label: 'Yandex GPT' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'proxyapi', label: 'OpenAI через ProxyAPI' },
 ] as const

const YANDEX_MODELS = [
  { value: 'yandexgpt-lite', label: 'Yandex GPT Lite' },
  { value: 'yandexgpt', label: 'Yandex GPT' },
  { value: 'yandexgpt-pro', label: 'Yandex GPT Pro' },
 ] as const

const OPENAI_MODELS = [
  { value: 'gpt-4-turbo-preview', label: 'GPT-4 Turbo' },
  { value: 'gpt-4', label: 'GPT-4' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
 ] as const

const DEFAULT_LLM_MODEL = {
  yandex: 'yandexgpt-lite',
  openai: 'gpt-4-turbo-preview',
  proxyapi: 'gpt-4-turbo-preview',
} as const

type LlmProvider = keyof typeof DEFAULT_LLM_MODEL

const isLlmProvider = (value: string): value is LlmProvider =>
  value in DEFAULT_LLM_MODEL

const WebsiteSettings = () => {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('general')
  const [settings, setSettings] = useState<any>({})
  const [widgetSettings, setWidgetSettings] = useState<any>({})

  // Загрузка настроек
  const { data: allSettings, isLoading } = useQuery({
    queryKey: ['website-settings'],
    queryFn: async () => {
      const response = await api.get('/website/settings')
      return response.data
    },
  })

  useEffect(() => {
    if (allSettings) {
      const newSettings = allSettings.settings || {}
      setSettings(newSettings)
      setWidgetSettings(newSettings.widget || {})
    }
  }, [allSettings])

  // Сохранение настроек
  const updateMutation = useMutation({
    mutationFn: async (updates: any) => {
      const response = await api.post('/website/settings/batch', updates)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['website-settings'] })
      alert('Настройки сохранены!')
    },
  })

  const handleSave = () => {
    const updates: any = {}
    
    // Собираем все настройки для сохранения
    Object.keys(settings).forEach(category => {
      Object.keys(settings[category] || {}).forEach(key => {
        const fullKey = category === 'general' ? key : `${category}_${key}`
        const value = settings[category][key]
        updates[fullKey] = {
          setting_key: fullKey,
          setting_value: typeof value === 'object' ? JSON.stringify(value) : value,
          setting_type: typeof value === 'object' ? 'json' : typeof value === 'number' ? 'number' : typeof value === 'boolean' ? 'boolean' : 'string',
          category: category,
        }
      })
    })

    updateMutation.mutate(updates)
  }

  const updateSetting = useCallback((category: string, key: string, value: any) => {
    setSettings((prev: any) => ({
      ...prev,
      [category]: {
        ...(prev?.[category] || {}),
        [key]: value,
      },
    }))

    if (category === 'widget') {
      setWidgetSettings((prev: any) => ({
        ...(prev || {}),
        [key]: value,
      }))
    }
  }, [])

  const handleWidgetSettingChange = useCallback(
    (key: string, value: any) => updateSetting('widget', key, value),
    [updateSetting]
  )

  const tabs = [
    { id: 'general', name: 'Общие', icon: '⚙️' },
    { id: 'header', name: 'Шапка', icon: '📋' },
    { id: 'footer', name: 'Подвал', icon: '📄' },
    { id: 'colors', name: 'Цвета', icon: '🎨' },
    { id: 'fonts', name: 'Шрифты', icon: '🔤' },
    { id: 'widget', name: 'Виджет чата', icon: '💬' },
  ]

  if (isLoading) {
    return <div className="text-center py-12">Загрузка...</div>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Настройки сайта</h1>
        <button
          onClick={handleSave}
          disabled={updateMutation.isPending}
          className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        >
          {updateMutation.isPending ? 'Сохранение...' : 'Сохранить все'}
        </button>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.name}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-lg shadow p-6">
        {activeTab === 'general' && (
          <GeneralSettings
            settings={settings.general || {}}
            updateSetting={(key: string, value: any) => updateSetting('general', key, value)}
          />
        )}
        {activeTab === 'header' && (
          <HeaderSettings settings={settings.header || {}} updateSetting={(key: string, value: any) => updateSetting('header', key, value)} />
        )}
        {activeTab === 'footer' && (
          <FooterSettings settings={settings.footer || {}} updateSetting={(key: string, value: any) => updateSetting('footer', key, value)} />
        )}
        {activeTab === 'colors' && (
          <ColorsSettings settings={settings.colors || {}} updateSetting={(key: string, value: any) => updateSetting('colors', key, value)} />
        )}
        {activeTab === 'fonts' && (
          <FontsSettings settings={settings.fonts || {}} updateSetting={(key: string, value: any) => updateSetting('fonts', key, value)} />
        )}
        {activeTab === 'widget' && (
          <WidgetSettings settings={widgetSettings || {}} updateSetting={handleWidgetSettingChange} />
        )}
      </div>
    </div>
  )
}

// Компоненты для каждой вкладки
const GeneralSettings = ({ settings, updateSetting }: any) => {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Общие настройки</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Название сайта</label>
          <input
            type="text"
            value={settings.site_name || ''}
            onChange={(e) => updateSetting('site_name', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="D&K FitBody"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Описание сайта</label>
          <input
            type="text"
            value={settings.site_description || ''}
            onChange={(e) => updateSetting('site_description', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="Персональный фитнес-тренер"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
          <input
            type="email"
            value={settings.contact_email || ''}
            onChange={(e) => updateSetting('contact_email', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Телефон</label>
          <input
            type="tel"
            value={settings.contact_phone || ''}
            onChange={(e) => updateSetting('contact_phone', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Telegram</label>
          <input
            type="text"
            value={settings.contact_telegram || ''}
            onChange={(e) => updateSetting('contact_telegram', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="@DandK_FitBody"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">WhatsApp</label>
          <input
            type="text"
            value={settings.contact_whatsapp || ''}
            onChange={(e) => updateSetting('contact_whatsapp', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="+79099202195"
          />
        </div>
      </div>
    </div>
  )
}

const HeaderSettings = ({ settings, updateSetting }: any) => {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Настройки шапки</h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Логотип (URL)</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={settings.logo_url || ''}
              onChange={(e) => updateSetting('logo_url', e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="https://..."
            />
            <label className="px-3 py-2 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
              Загрузить
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0]
                  if (!file) return
                  const formData = new FormData()
                  formData.append('file', file)
                  try {
                    const res = await api.post('/uploads', formData, {
                      headers: { 'Content-Type': 'multipart/form-data' },
                    })
                    const url = res.data?.url
                    if (url) updateSetting('logo_url', url)
                  } catch (err) {
                    alert('Ошибка загрузки файла')
                  } finally {
                    e.currentTarget.value = ''
                  }
                }}
              />
            </label>
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Текст в шапке</label>
          <input
            type="text"
            value={settings.header_text || ''}
            onChange={(e) => updateSetting('header_text', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        
        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={settings.show_menu || false}
              onChange={(e) => updateSetting('show_menu', e.target.checked)}
              className="mr-2"
            />
            <span className="text-sm font-medium text-gray-700">Показывать меню</span>
          </label>
        </div>
      </div>
    </div>
  )
}

const FooterSettings = ({ settings, updateSetting }: any) => {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Настройки подвала</h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Текст копирайта</label>
          <input
            type="text"
            value={settings.copyright_text || ''}
            onChange={(e) => updateSetting('copyright_text', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        
        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={settings.show_social_links || false}
              onChange={(e) => updateSetting('show_social_links', e.target.checked)}
              className="mr-2"
            />
            <span className="text-sm font-medium text-gray-700">Показывать ссылки на соцсети</span>
          </label>
        </div>
      </div>
    </div>
  )
}

const ColorsSettings = ({ settings, updateSetting }: any) => {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Цветовая схема</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Основной цвет</label>
          <input
            type="color"
            value={settings.primary_color || '#3B82F6'}
            onChange={(e) => updateSetting('primary_color', e.target.value)}
            className="w-full h-10 border border-gray-300 rounded-lg"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Вторичный цвет</label>
          <input
            type="color"
            value={settings.secondary_color || '#10B981'}
            onChange={(e) => updateSetting('secondary_color', e.target.value)}
            className="w-full h-10 border border-gray-300 rounded-lg"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Цвет фона</label>
          <input
            type="color"
            value={settings.background_color || '#FFFFFF'}
            onChange={(e) => updateSetting('background_color', e.target.value)}
            className="w-full h-10 border border-gray-300 rounded-lg"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Цвет текста</label>
          <input
            type="color"
            value={settings.text_color || '#1F2937'}
            onChange={(e) => updateSetting('text_color', e.target.value)}
            className="w-full h-10 border border-gray-300 rounded-lg"
          />
        </div>
      </div>
    </div>
  )
}

const FontsSettings = ({ settings, updateSetting }: any) => {
  const fontFamilies = [
    'Arial, sans-serif',
    'Georgia, serif',
    'Times New Roman, serif',
    'Verdana, sans-serif',
    'Montserrat, sans-serif',
    'Roboto, sans-serif',
    'Open Sans, sans-serif',
  ]
  
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Настройки шрифтов</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Основной шрифт</label>
          <select
            value={settings.primary_font || 'Arial, sans-serif'}
            onChange={(e) => updateSetting('primary_font', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {fontFamilies.map((font) => (
              <option key={font} value={font}>
                {font}
              </option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Размер основного шрифта</label>
          <input
            type="number"
            value={settings.font_size || 16}
            onChange={(e) => updateSetting('font_size', parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            min="12"
            max="24"
          />
        </div>
      </div>
    </div>
  )
}

const WidgetSettings = ({ settings, updateSetting }: any) => {
  const providerValue = settings.llm_provider ?? 'yandex'
  const llmProvider: LlmProvider = isLlmProvider(providerValue) ? providerValue : 'yandex'

  const availableModels = useMemo(
    () => (llmProvider === 'yandex' ? YANDEX_MODELS : OPENAI_MODELS),
    [llmProvider]
  )

  useEffect(() => {
    const currentModel = settings.llm_model
    if (!availableModels.some((model) => model.value === currentModel)) {
      const fallbackModel = DEFAULT_LLM_MODEL[llmProvider] || availableModels[0]?.value
      if (fallbackModel) {
        updateSetting('llm_model', fallbackModel)
      }
    }
  }, [llmProvider, availableModels, settings.llm_model, updateSetting])

  const handleProviderChange = (providerValue: string) => {
    const normalizedProvider: LlmProvider = isLlmProvider(providerValue) ? providerValue : 'yandex'
    updateSetting('llm_provider', normalizedProvider)
    const defaultModel = DEFAULT_LLM_MODEL[normalizedProvider]
    updateSetting('llm_model', defaultModel)
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Настройки виджета чата</h2>
      
      <div className="space-y-6">
        {/* Основные настройки */}
        <div className="border-b pb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Основные настройки</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Заголовок виджета</label>
              <input
                type="text"
                value={settings.widget_title || 'Фитнес-консультант'}
                onChange={(e) => updateSetting('widget_title', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Приветственное сообщение</label>
              <textarea
                value={settings.greeting_message || 'Привет! 👋 Я помогу вам выбрать программу тренировок. Давайте начнем!'}
                onChange={(e) => updateSetting('greeting_message', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                rows={3}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Логотип (URL)</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={settings.widget_logo || ''}
                  onChange={(e) => updateSetting('widget_logo', e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="https://..."
                />
                <label className="px-3 py-2 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
                  Загрузить
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={async (e) => {
                      const file = e.target.files?.[0]
                      if (!file) return
                      const formData = new FormData()
                      formData.append('file', file)
                      try {
                        const res = await api.post('/uploads', formData, {
                          headers: { 'Content-Type': 'multipart/form-data' },
                        })
                        const url = res.data?.url
                        if (url) updateSetting('widget_logo', url)
                      } catch (err) {
                        alert('Ошибка загрузки файла')
                      } finally {
                        e.currentTarget.value = ''
                      }
                    }}
                  />
                </label>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Основной цвет виджета</label>
              <input
                type="color"
                value={settings.widget_primary_color || '#3B82F6'}
                onChange={(e) => updateSetting('widget_primary_color', e.target.value)}
                className="w-full h-10 border border-gray-300 rounded-lg"
              />
            </div>
          </div>
        </div>
        
        {/* Настройки LLM */}
        <div className="border-b pb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Настройки LLM</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Провайдер LLM</label>
              <select
                value={llmProvider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {LLM_PROVIDERS.map((provider) => (
                  <option key={provider.value} value={provider.value}>
                    {provider.label}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Модель</label>
              <select
                value={settings.llm_model || DEFAULT_LLM_MODEL[llmProvider]}
                onChange={(e) => updateSetting('llm_model', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {availableModels.map((model) => (
                  <option key={model.value} value={model.value}>
                    {model.label}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Temperature ({settings.temperature || 0.7})
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={settings.temperature || 0.7}
                onChange={(e) => updateSetting('temperature', parseFloat(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">0.0 - детерминированные ответы, 1.0 - креативные ответы</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Максимум токенов</label>
              <input
                type="number"
                value={settings.max_tokens || 2000}
                onChange={(e) => updateSetting('max_tokens', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                min="100"
                max="8000"
              />
            </div>
          </div>
        </div>
        
        {/* Системный промпт */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Системный промпт</h3>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Промпт для LLM</label>
            <textarea
              value={settings.system_prompt || ''}
              onChange={(e) => updateSetting('system_prompt', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-sm"
              rows={15}
              placeholder="Введите системный промпт для LLM..."
            />
            <p className="text-xs text-gray-500 mt-1">
              Промпт определяет поведение AI-ассистента. Оставьте пустым для использования дефолтного промпта.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default WebsiteSettings

