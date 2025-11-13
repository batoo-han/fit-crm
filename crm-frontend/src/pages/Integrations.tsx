import { useState, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useModal } from '../components/ui/modal/ModalContext'

const Integrations = () => {
  const queryClient = useQueryClient()
  const { showModal } = useModal()
  const [lastHealth, setLastHealth] = useState<{ provider?: string; ok?: boolean; url?: string } | null>(null)
  const { data: status, isLoading } = useQuery({
    queryKey: ['amocrm-status'],
    queryFn: async () => {
      const res = await api.get('/integrations/amocrm/status')
      return res.data as { enabled: boolean; domain?: string; has_tokens: boolean; expires_at?: number }
    },
  })

  const enableMutation = useMutation({
    mutationFn: async (enabled: boolean) => {
      const res = await api.post('/integrations/amocrm/enable', { enabled })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['amocrm-status'] })
    },
  })

  const [connectForm, setConnectForm] = useState({
    domain: '',
    client_id: '',
    client_secret: '',
    redirect_uri: '',
    auth_code: '',
  })

  const connectMutation = useMutation({
    mutationFn: async () => {
      const payload = { ...connectForm }
      if (!payload.auth_code) delete (payload as any).auth_code
      const res = await api.post('/integrations/amocrm/connect', payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['amocrm-status'] })
      showModal({
        title: 'amoCRM',
        message: 'Настройки amoCRM сохранены',
        tone: 'success',
      })
    },
  })

  const { data: paySettings } = useQuery({
    queryKey: ['payment-settings'],
    queryFn: async () => {
      const res = await api.get('/payments/settings')
      return res.data as Record<string, any>
    },
  })

  const { data: promos } = useQuery({
    queryKey: ['promo-codes'],
    queryFn: async () => {
      const res = await api.get('/promocodes')
      return res.data as Array<{ id: number; code: string; description?: string | null; is_active: boolean }>
    },
  })

  const [pendingSettings, setPendingSettings] = useState<Record<string, any>>({})

  const savePaymentSettings = useMutation({
    mutationFn: async (payload: Record<string, any>) => {
      return api.post('/payments/settings', payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payment-settings'] })
      showModal({
        title: 'Настройки сохранены',
        message: 'Параметры платёжных систем успешно обновлены.',
        tone: 'success',
      })
    },
    onError: () => {
      showModal({
        title: 'Ошибка сохранения',
        message: 'Не удалось сохранить настройки платёжных систем. Попробуйте позже.',
        tone: 'error',
      })
    },
  })

  useEffect(() => {
    if (paySettings) {
      setPendingSettings({ ...paySettings })
    }
  }, [paySettings])

  const promoOptions = useMemo(
    () =>
      (promos || [])
        .filter((promo) => promo.is_active)
        .map((promo) => ({
          value: promo.code,
          label: promo.description ? `${promo.code} — ${promo.description}` : promo.code,
        })),
    [promos]
  )
  const defaultPromoValue = pendingSettings.default_promo_code || ''
  const promoExists =
    !defaultPromoValue || promoOptions.some((option) => option.value === defaultPromoValue)

  const handleFieldChange = (key: string, value: any) => {
    setPendingSettings((prev) => ({
      ...(prev || {}),
      [key]: value,
    }))
  }

  const normalizeSettings = (settings?: Record<string, any>) => {
    if (!settings) return {}
    const normalized: Record<string, any> = {}
    Object.entries(settings).forEach(([key, value]) => {
      if (value === undefined) {
        return
      }
      normalized[key] = value === null ? '' : value
    })
    return normalized
  }

  const hasPaymentChanges =
    !!paySettings &&
    JSON.stringify(normalizeSettings(pendingSettings)) !== JSON.stringify(normalizeSettings(paySettings))

  const handleResetPayments = () => {
    if (paySettings) {
      setPendingSettings({ ...paySettings })
    } else {
      setPendingSettings({})
    }
  }

  const handleSavePayments = () => {
    const payload = { ...(pendingSettings || {}) }
    if ('default_promo_code' in payload) {
      const val = payload.default_promo_code
      payload.default_promo_code = val ? String(val).toUpperCase() : ''
    }
    savePaymentSettings.mutate(payload)
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Интеграции</h1>
        <p className="text-gray-500 mt-2">Подключение сторонних сервисов. Здесь можно включить amoCRM как альтернативную CRM.</p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">amoCRM</h2>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-700">Включить</span>
            <input
              type="checkbox"
              checked={!!status?.enabled}
              onChange={(e) => enableMutation.mutate(e.target.checked)}
            />
          </div>
        </div>
        {isLoading ? (
          <p>Проверка статуса…</p>
        ) : (
          <div className="space-y-4">
            <div className="text-sm text-gray-700">
              <div>Статус: {status?.enabled ? 'Включено' : 'Выключено'}</div>
              <div>Домен: {status?.domain || '—'}</div>
              <div>
                Токены: {status?.has_tokens ? 'Сохранены' : 'Нет'}{' '}
                {status?.expires_at ? `(истекают: ${new Date(status.expires_at * 1000).toLocaleString('ru-RU')})` : ''}
              </div>
            </div>
            <div className="border-t pt-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Подключение</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Домен (example.amocrm.ru)</label>
                  <input
                    type="text"
                    value={connectForm.domain}
                    onChange={(e) => setConnectForm({ ...connectForm, domain: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="example.amocrm.ru"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Client ID</label>
                  <input
                    type="text"
                    value={connectForm.client_id}
                    onChange={(e) => setConnectForm({ ...connectForm, client_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Client Secret</label>
                  <input
                    type="text"
                    value={connectForm.client_secret}
                    onChange={(e) => setConnectForm({ ...connectForm, client_secret: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Redirect URI</label>
                  <input
                    type="text"
                    value={connectForm.redirect_uri}
                    onChange={(e) => setConnectForm({ ...connectForm, redirect_uri: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="https://your.domain/oauth/callback"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Auth Code (опционально)</label>
                  <input
                    type="text"
                    value={connectForm.auth_code}
                    onChange={(e) => setConnectForm({ ...connectForm, auth_code: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="Код авторизации из amoCRM после согласия"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Получите auth code через стандартный OAuth‑поток amoCRM и вставьте сюда для обмена на токены.
                  </p>
                </div>
              </div>
              <div className="mt-4">
                <button
                  onClick={() => {
                    const domain = connectForm.domain || status?.domain || ''
                    const clientId = connectForm.client_id
                    const redirectUri = connectForm.redirect_uri
                    if (!domain || !clientId || !redirectUri) {
                  showModal({
                    title: 'Недостаточно данных',
                    message: 'Укажите домен, client_id и redirect_uri для формирования ссылки авторизации.',
                    tone: 'error',
                  })
                      return
                    }
                    const url =
                      `https://${domain}/oauth2/authorize` +
                      `?client_id=${encodeURIComponent(clientId)}` +
                      `&redirect_uri=${encodeURIComponent(redirectUri)}` +
                      `&response_type=code&state=crm`
                    window.open(url, '_blank')
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 mr-2"
                >
                  Открыть авторизацию в amoCRM
                </button>
                <button
                  onClick={() => connectMutation.mutate()}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                  disabled={connectMutation.isPending}
                >
                  {connectMutation.isPending ? 'Сохранение…' : 'Сохранить/Подключить'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Платёжные системы</h2>
        <p className="text-sm text-gray-600 mb-4">Поддерживаются YooKassa и Tinkoff. Активна может быть только одна.</p>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Активный провайдер</label>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="radio"
                  name="payment_provider"
                  checked={(pendingSettings.payment_provider || 'yookassa') === 'yookassa'}
                  onChange={() => handleFieldChange('payment_provider', 'yookassa')}
                />
                YooKassa
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="radio"
                  name="payment_provider"
                  checked={pendingSettings.payment_provider === 'tinkoff'}
                  onChange={() => handleFieldChange('payment_provider', 'tinkoff')}
                />
                Tinkoff
              </label>
              <button
                onClick={async () => {
                  const res = await api.get('/payments/health')
                  if (res.data?.ok && res.data?.confirmation_url) {
                    const confirmationUrl = res.data.confirmation_url as string
                    setLastHealth({ ok: true, url: confirmationUrl })
                    showModal({
                      title: 'Провайдер доступен',
                      message: 'Провайдер доступен. Открыть ссылку оплаты для проверки?',
                      actions: [
                        { label: 'Позже', variant: 'secondary' },
                        {
                          label: 'Открыть ссылку',
                          variant: 'primary',
                          onClick: () => window.open(confirmationUrl, '_blank'),
                        },
                      ],
                    })
                  } else {
                    setLastHealth({ ok: false })
                    showModal({
                      title: 'Провайдер недоступен',
                      message: 'Проверьте ключи и настройки платёжной системы.',
                      tone: 'error',
                    })
                  }
                }}
                className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
              >
                Проверить провайдера
              </button>
              <button
                onClick={async () => {
                  const res = await api.get('/payments/health?provider=yookassa')
                  const ok = !!res.data?.ok
                  setLastHealth({ provider: 'YooKassa', ok, url: res.data?.confirmation_url })
                  showModal({
                    title: 'Проверка YooKassa',
                    message: ok ? 'YooKassa: OK' : 'YooKassa: ошибка',
                    tone: ok ? 'success' : 'error',
                  })
                }}
                className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
              >
                Проверить YooKassa
              </button>
              <button
                onClick={async () => {
                  const res = await api.get('/payments/health?provider=tinkoff')
                  const ok = !!res.data?.ok
                  setLastHealth({ provider: 'Tinkoff', ok, url: res.data?.confirmation_url })
                  showModal({
                    title: 'Проверка Tinkoff',
                    message: ok ? 'Tinkoff: OK' : 'Tinkoff: ошибка',
                    tone: ok ? 'success' : 'error',
                  })
                }}
                className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
              >
                Проверить Tinkoff
              </button>
            </div>
            {lastHealth && (
              <div className="mt-2 text-xs text-gray-600">
                <div>Последняя проверка{lastHealth.provider ? ` (${lastHealth.provider})` : ''}: {lastHealth.ok ? 'OK' : 'Ошибка'}</div>
                {lastHealth.url && (
                  <div className="truncate">
                    Ссылка подтверждения: <a href={lastHealth.url} target="_blank" rel="noreferrer" className="text-primary-600 underline">{lastHealth.url}</a>
                  </div>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Промокод по умолчанию (автоприменение)</label>
            <select
              value={defaultPromoValue}
              onChange={(e) => handleFieldChange('default_promo_code', e.target.value.toUpperCase())}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="">— без промокода —</option>
              {!promoExists && (
                <option value={defaultPromoValue}>
                  {defaultPromoValue} (неактивен)
                </option>
              )}
              {promoOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Выберите промокод из заранее созданных в разделе «Маркетинг». Если оставить поле пустым, автоприменение отключено.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="font-medium text-gray-900">YooKassa</div>
              <input
                type="text"
                placeholder="Shop ID"
                value={pendingSettings.yookassa_shop_id || ''}
                onChange={(e) => handleFieldChange('yookassa_shop_id', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
              <input
                type="password"
                placeholder="Secret Key"
                value={pendingSettings.yookassa_secret_key || ''}
                onChange={(e) => handleFieldChange('yookassa_secret_key', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
              <input
                type="text"
                placeholder="Return URL"
                value={pendingSettings.yookassa_return_url || ''}
                onChange={(e) => handleFieldChange('yookassa_return_url', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div className="space-y-2">
              <div className="font-medium text-gray-900">Tinkoff</div>
              <input
                type="text"
                placeholder="Terminal Key"
                value={pendingSettings.tinkoff_terminal_key || ''}
                onChange={(e) => handleFieldChange('tinkoff_terminal_key', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
              <input
                type="password"
                placeholder="Secret Key"
                value={pendingSettings.tinkoff_secret_key || ''}
                onChange={(e) => handleFieldChange('tinkoff_secret_key', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
              <input
                type="text"
                placeholder="Return URL"
                value={pendingSettings.tinkoff_return_url || ''}
                onChange={(e) => handleFieldChange('tinkoff_return_url', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
          </div>

          <div className="flex flex-col md:flex-row md:justify-end gap-2 border-t border-gray-200 pt-4 mt-6">
            <button
              type="button"
              onClick={handleResetPayments}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm disabled:opacity-60 disabled:cursor-not-allowed"
              disabled={!hasPaymentChanges || savePaymentSettings.isPending}
            >
              Сбросить изменения
            </button>
            <button
              type="button"
              onClick={handleSavePayments}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm disabled:opacity-60 disabled:cursor-not-allowed"
              disabled={!hasPaymentChanges || savePaymentSettings.isPending}
            >
              {savePaymentSettings.isPending ? 'Сохранение…' : 'Сохранить настройки'}
            </button>
          </div>

          <div className="border-t pt-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Тестовый платёж</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Сумма (₽)</label>
                <input id="testPayAmount" type="number" defaultValue={10} className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
                <input id="testPayDesc" type="text" defaultValue="Тестовый платёж" className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={async () => {
                    const amount = parseFloat((document.getElementById('testPayAmount') as HTMLInputElement).value || '10')
                    const description = (document.getElementById('testPayDesc') as HTMLInputElement).value || 'Тестовый платёж'
                    const res = await api.post('/payments/test-init', { amount, description })
                    const url = (res.data && res.data.confirmation_url) as string
                    if (url) window.open(url, '_blank')
                  else {
                    showModal({
                      title: 'Не удалось получить ссылку',
                      message: 'Ссылка оплаты не вернулась от сервиса. Проверьте настройки.',
                      tone: 'error',
                    })
                  }
                  }}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  Открыть ссылку оплаты
                </button>
              </div>
            </div>
          </div>

          <div className="border-t pt-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Webhooks</h3>
            <div className="text-sm text-gray-700 space-y-1">
              <div>
                YooKassa: <code className="px-1 py-0.5 bg-gray-100 rounded">/api/payments/webhook/yookassa</code>
              </div>
              <div>
                Tinkoff: <code className="px-1 py-0.5 bg-gray-100 rounded">/api/payments/webhook/tinkoff</code>
              </div>
              <p className="text-xs text-gray-500">Укажите эти пути в настройках нотификаций провайдеров (с полным доменом вашего сервера).</p>
            </div>
          </div>

          <WebhookLogPanel />
        </div>
      </div>
    </div>
  )
}

const WebhookLogPanel = () => {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['payment-webhook-logs'],
    queryFn: async () => {
      const res = await api.get('/payments/webhooks/logs?limit=50')
      return res.data as Array<{ id: number; provider: string; event?: string; created_at?: string }>
    },
  })

  return (
    <div className="border-t pt-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-900">Журнал вебхуков</h3>
        <button onClick={() => refetch()} className="text-sm px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100">Обновить</button>
      </div>
      {isLoading ? (
        <div className="text-sm text-gray-500">Загрузка…</div>
      ) : (
        <div className="max-h-64 overflow-auto text-sm">
          <table className="min-w-full">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="py-1 pr-4">Время</th>
                <th className="py-1 pr-4">Провайдер</th>
                <th className="py-1">Событие/статус</th>
              </tr>
            </thead>
            <tbody>
              {(data || []).map((r) => (
                <tr key={r.id} className="border-t">
                  <td className="py-1 pr-4 whitespace-nowrap">{r.created_at ? new Date(r.created_at).toLocaleString('ru-RU') : '—'}</td>
                  <td className="py-1 pr-4">{r.provider}</td>
                  <td className="py-1">{r.event || '—'}</td>
                </tr>
              ))}
              {(!data || data.length === 0) && (
                <tr>
                  <td colSpan={3} className="py-2 text-gray-500">Пока нет записей</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default Integrations


