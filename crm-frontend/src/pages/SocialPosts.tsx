import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useModal } from '../components/ui/modal/ModalContext'


type SocialPost = {
  id: number
  platform: string
  title?: string | null
  content: string
  media_url?: string | null
  scheduled_at?: string | null
  status: string
}

// Тип пресета закомментирован до реализации UI для экспорта/импорта
// type SocialPreset = {
//   name: string
//   orderBy: 'id' | 'title' | 'scheduled_at'
//   seqStep: number
//   templateId?: number
// }

const SocialPosts = () => {
  const queryClient = useQueryClient()
  const { showModal } = useModal()
  const { data: posts, isLoading } = useQuery({
    queryKey: ['social-posts'],
    queryFn: async () => {
      const res = await api.get('/social-posts')
      return res.data as SocialPost[]
    },
  })
  const { data: templates } = useQuery({
    queryKey: ['social-post-templates'],
    queryFn: async () => {
      const res = await api.get('/social-posts/templates')
      return res.data as Array<{ id: number; name: string; platform?: string | null; title?: string | null; content: string; media_url?: string | null }>
    },
  })

  const createMutation = useMutation({
    mutationFn: async (payload: Partial<SocialPost>) => {
      const res = await api.post('/social-posts', payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-posts'] })
      setForm(initialForm)
      setEditing(null)
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Partial<SocialPost> }) => {
      const res = await api.put(`/social-posts/${id}`, payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-posts'] })
      setForm(initialForm)
      setEditing(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/social-posts/${id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['social-posts'] }),
  })

  const processMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/social-posts/process-scheduled')
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-posts'] })
    },
  })

  const retryMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await api.post(`/social-posts/${id}/retry`)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-posts'] })
    },
  })

  const duplicateMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await api.post(`/social-posts/${id}/duplicate`)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-posts'] })
    },
  })

  const bulkScheduleMutation = useMutation({
    mutationFn: async ({ ids, when }: { ids: number[]; when: string }) => {
      const res = await api.post('/social-posts/bulk/schedule', {
        ids,
        scheduled_at: new Date(when).toISOString(),
        status: 'scheduled',
      })
      return res.data
    },
    onSuccess: () => {
      setSelected(new Set())
      queryClient.invalidateQueries({ queryKey: ['social-posts'] })
    },
  })

  const bulkSequenceMutation = useMutation({
    mutationFn: async ({ ids, start, step, useServerQuiet, quietStart, quietEnd }: { ids: number[]; start: string; step: number; useServerQuiet?: boolean; quietStart?: number; quietEnd?: number }) => {
      const body: any = {
        ids,
        start_at: new Date(start).toISOString(),
        step_minutes: step,
        status: 'scheduled',
      }
      if (useServerQuiet) {
        body.quiet_hours_enabled = true
        body.quiet_start = quietStart
        body.quiet_end = quietEnd
      }
      const res = await api.post('/social-posts/bulk/sequence', body)
      return res.data
    },
    onSuccess: () => {
      setSelected(new Set())
      queryClient.invalidateQueries({ queryKey: ['social-posts'] })
    },
  })

  const bulkApplyTemplateMutation = useMutation({
    mutationFn: async ({ ids, templateId, ow }: { ids: number[]; templateId: number; ow: { t: boolean; m: boolean; p: boolean } }) => {
      const res = await api.post('/social-posts/bulk/apply-template', {
        ids,
        template_id: templateId,
        overwrite_title: ow.t,
        overwrite_media: ow.m,
        overwrite_platform: ow.p,
      })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-posts'] })
    },
  })

  const uploadFile = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api.post('/uploads', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      return res.data.file_url as string
    },
    onSuccess: (url) => {
      setForm((prev) => ({ ...prev, media_url: url }))
    },
  })

  const updateTemplateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: { name: string; platform?: string; title?: string; content: string; media_url?: string } }) => {
      const res = await api.put(`/social-posts/templates/${id}`, payload)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['social-post-templates'] })
      setEditingTemplate(null)
      setTemplateForm({ name: '', platform: '', title: '', content: '', media_url: '' })
    },
  })
  const deleteTemplateMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/social-posts/templates/${id}`)
    },
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['social-post-templates'] })
      if (editingTemplate === deletedId) {
        setEditingTemplate(null)
        setTemplateForm({ name: '', platform: '', title: '', content: '', media_url: '' })
      }
    },
  })

  const initialForm = {
    platform: 'telegram',
    title: '',
    content: '',
    media_url: '',
    scheduled_at: '',
    status: 'draft',
  }

  const [form, setForm] = useState(initialForm)
  const [editing, setEditing] = useState<SocialPost | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [bulkWhen, setBulkWhen] = useState('')
  const [editingTemplate, setEditingTemplate] = useState<number | null>(null)
  const [templateForm, setTemplateForm] = useState({ name: '', platform: '', title: '', content: '', media_url: '' })
  const [showPreview, setShowPreview] = useState(false)
  const [seqStart, setSeqStart] = useState('')
  const [seqStep, setSeqStep] = useState(60)
  const [orderBy, setOrderBy] = useState<'id' | 'title' | 'scheduled_at'>('id')
  const [applyTplForSelected, setApplyTplForSelected] = useState<number | ''>('')
  const [owTitle, setOwTitle] = useState(true)
  const [owMedia, setOwMedia] = useState(true)
  const [owPlatform, setOwPlatform] = useState(false)
  // Пресеты закомментированы до реализации UI для экспорта/импорта
  // const [presets, setPresets] = useState<SocialPreset[]>([])
  const [quietEnabled, setQuietEnabled] = useState(false)
  const [quietStart, setQuietStart] = useState(9)
  const [quietEnd, setQuietEnd] = useState(21)
  const [showBulkPreview, setShowBulkPreview] = useState(false)
  const [useServerQuiet, setUseServerQuiet] = useState(false)

  // Загрузка пресетов из localStorage закомментирована до реализации UI
  // useEffect(() => {
  //   try {
  //     const raw = localStorage.getItem('social_presets')
  //     if (raw) setPresets(JSON.parse(raw))
  //   } catch {}
  // }, [])

  // Функция сохранения пресетов закомментирована до реализации UI
  // const savePresets = (next: SocialPreset[]) => {
  //   setPresets(next)
  //   try {
  //     localStorage.setItem('social_presets', JSON.stringify(next))
  //   } catch {}
  // }

  // Функции экспорта/импорта пресетов закомментированы до реализации UI
  // const exportPresets = () => {
  //   const blob = new Blob([JSON.stringify(presets, null, 2)], { type: 'application/json' })
  //   const url = URL.createObjectURL(blob)
  //   const a = document.createElement('a')
  //   a.href = url
  //   a.download = 'social_presets.json'
  //   a.click()
  //   URL.revokeObjectURL(url)
  // }

  // const importPresets = (file: File) => {
  //   const reader = new FileReader()
  //   reader.onload = () => {
  //     try {
  //       const parsed = JSON.parse(String(reader.result)) as SocialPreset[]
  //       if (Array.isArray(parsed)) {
  //         savePresets(parsed)
  //         alert('Пресеты импортированы')
  //       }
  //     } catch {
  //       alert('Некорректный файл пресетов')
  //     }
  //   }
  //   reader.readAsText(file)
  // }

  const adjustToQuietHours = (d: Date) => {
    if (!quietEnabled) return d
    const dt = new Date(d)
    const h = dt.getHours()
    if (quietStart < quietEnd) {
      if (h < quietStart) {
        dt.setHours(quietStart, 0, 0, 0)
      } else if (h >= quietEnd) {
        dt.setDate(dt.getDate() + 1)
        dt.setHours(quietStart, 0, 0, 0)
      }
    } else {
      // quiet window wraps midnight; allow posting only outside [quietEnd, quietStart)
      if (h >= quietEnd && h < quietStart) {
        dt.setHours(quietStart, 0, 0, 0)
      }
    }
    return dt
  }

  const selectedIdsOrdered = useMemo(() => {
    const all = posts || []
    const sel = all.filter((p) => selected.has(p.id))
    const sorted = [...sel].sort((a, b) => {
      if (orderBy === 'title') {
        return (a.title || '').localeCompare(b.title || '')
      }
      if (orderBy === 'scheduled_at') {
        return (new Date(a.scheduled_at || 0).getTime()) - (new Date(b.scheduled_at || 0).getTime())
      }
      return a.id - b.id
    })
    return sorted.map((p) => p.id)
  }, [selected, posts, orderBy])

  const onSubmit = () => {
    if (!form.content.trim()) {
      showModal({
        title: 'Незаполненный пост',
        message: 'Заполните контент поста',
        tone: 'error',
      })
      return
    }
    const payload = {
      platform: form.platform,
      title: form.title || '',
      content: form.content,
      media_url: form.media_url || undefined,
      scheduled_at: form.scheduled_at ? new Date(form.scheduled_at).toISOString() : null,
      status: form.status,
    }
    if (editing) {
      updateMutation.mutate({ id: editing.id, payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  const beginEdit = (post: SocialPost) => {
    setEditing(post)
    setForm({
      platform: post.platform,
      title: post.title || '',
      content: post.content,
      media_url: post.media_url || '',
      scheduled_at: post.scheduled_at ? new Date(post.scheduled_at).toISOString().slice(0, 16) : '',
      status: post.status,
    })
  }

  const toggleSelected = (id: number) => {
    setSelected((prev) => {
      const copy = new Set(prev)
      if (copy.has(id)) copy.delete(id)
      else copy.add(id)
      return copy
    })
  }

  const applyTemplate = (tplId: number) => {
    const tpl = (templates || []).find((t) => t.id === tplId)
    if (!tpl) return
    setForm({
      platform: tpl.platform || form.platform,
      title: tpl.title || '',
      content: tpl.content,
      media_url: tpl.media_url || '',
      scheduled_at: form.scheduled_at,
      status: form.status,
    })
  }

  const scheduleNow = () => {
    const nowLocal = new Date()
    const isoLocal = new Date(nowLocal.getTime() - nowLocal.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
    setForm((prev) => ({ ...prev, scheduled_at: isoLocal, status: 'scheduled' }))
  }

  const clientSideSequenceWithQuietHours = async () => {
    if (selectedIdsOrdered.length === 0 || !seqStart) return
    const base = adjustToQuietHours(new Date(seqStart))
    let current = base
    for (const id of selectedIdsOrdered) {
      const when = adjustToQuietHours(current)
      await updateMutation.mutateAsync({ id, payload: { scheduled_at: when.toISOString(), status: 'scheduled' } })
      current = new Date(when.getTime() + seqStep * 60000)
    }
    setSelected(new Set())
  }

  const previewList = useMemo(() => {
    const list: Array<{ id: number; title: string; time?: string }> = []
    let current = seqStart ? adjustToQuietHours(new Date(seqStart)) : undefined
    for (const id of selectedIdsOrdered.slice(0, 5)) {
      const p = (posts || []).find((x) => x.id === id)
      if (!p) continue
      const title = p.title || `Пост #${p.id}`
      let time: string | undefined
      if (current) {
        const when = adjustToQuietHours(current)
        time = new Date(when.getTime()).toLocaleString('ru-RU')
        current = new Date(when.getTime() + seqStep * 60000)
      }
      list.push({ id, title, time })
    }
    return list
  }, [selectedIdsOrdered, posts, seqStart, seqStep, quietEnabled, quietStart, quietEnd])

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Соцсети</h1>
        <p className="text-gray-500 mt-2">Планирование постов для Telegram (и других соцсетей). Пока поддерживается отправка в Telegram-канал.</p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Посты</h2>
          <button
            onClick={() => {
              processMutation.mutate()
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
          >
            Обработать отправленные (ручной запуск)
          </button>
        </div>
        {isLoading ? (
          <p>Загрузка...</p>
        ) : (
          <div className="divide-y border border-gray-200 rounded-lg">
            <div className="px-4 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div className="flex items-center gap-2">
                <input
                  type="datetime-local"
                  value={bulkWhen}
                  onChange={(e) => setBulkWhen(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg"
                />
                <button
                  disabled={selected.size === 0 || !bulkWhen || bulkScheduleMutation.isPending}
                  onClick={() => bulkScheduleMutation.mutate({ ids: selectedIdsOrdered, when: bulkWhen })}
                  className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm"
                >
                  Запланировать выбранные
                </button>
                {selected.size > 0 && <span className="text-xs text-gray-500">Выбрано: {selected.size}</span>}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={orderBy}
                  onChange={(e) => setOrderBy(e.target.value as any)}
                  className="px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="id">Порядок: по ID</option>
                  <option value="title">Порядок: по заголовку</option>
                  <option value="scheduled_at">Порядок: по времени публикации</option>
                </select>
                <select
                  onChange={(e) => {
                    const val = e.target.value
                    setApplyTplForSelected(val ? parseInt(val) : '')
                  }}
                  className="px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="">Шаблон: выбрать…</option>
                  {(templates || []).map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-1 text-xs text-gray-700"><input type="checkbox" checked={owTitle} onChange={(e) => setOwTitle(e.target.checked)} /> Заголовок</label>
                <label className="flex items-center gap-1 text-xs text-gray-700"><input type="checkbox" checked={owMedia} onChange={(e) => setOwMedia(e.target.checked)} /> Медиа</label>
                <label className="flex items-center gap-1 text-xs text-gray-700"><input type="checkbox" checked={owPlatform} onChange={(e) => setOwPlatform(e.target.checked)} /> Платформа</label>
                <button
                  disabled={selected.size === 0 || !applyTplForSelected || bulkApplyTemplateMutation.isPending}
                  onClick={() => applyTplForSelected && bulkApplyTemplateMutation.mutate({ ids: selectedIdsOrdered, templateId: applyTplForSelected as number, ow: { t: owTitle, m: owMedia, p: owPlatform } })}
                  className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
                >
                  Применить шаблон к выбранным
                </button>
              </div>
            </div>
            <div className="px-4 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div className="flex items-center gap-2">
                <input
                  type="datetime-local"
                  value={seqStart}
                  onChange={(e) => setSeqStart(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg"
                />
                <input
                  type="number"
                  min={1}
                  value={seqStep}
                  onChange={(e) => setSeqStep(parseInt(e.target.value) || 1)}
                  className="w-28 px-3 py-2 border border-gray-300 rounded-lg"
                />
                <span className="text-sm text-gray-700">минут шаг</span>
                <button
                  disabled={selected.size === 0 || !seqStart || bulkSequenceMutation.isPending}
                  onClick={() => bulkSequenceMutation.mutate({ ids: selectedIdsOrdered, start: seqStart, step: seqStep, useServerQuiet, quietStart, quietEnd })}
                  className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm"
                >
                  Последовательно по интервалу
                </button>
                <label className="flex items-center gap-1 text-xs text-gray-700 ml-3"><input type="checkbox" checked={quietEnabled} onChange={(e) => setQuietEnabled(e.target.checked)} /> Учитывать тихие часы (клиент)</label>
                <input type="number" min={0} max={23} value={quietStart} onChange={(e) => setQuietStart(Math.max(0, Math.min(23, parseInt(e.target.value) || 0)))} className="w-16 px-2 py-1 border border-gray-300 rounded" />
                <span className="text-xs text-gray-600">—</span>
                <input type="number" min={0} max={23} value={quietEnd} onChange={(e) => setQuietEnd(Math.max(0, Math.min(23, parseInt(e.target.value) || 0)))} className="w-16 px-2 py-1 border border-gray-300 rounded" />
                <button
                  disabled={selected.size === 0 || !seqStart}
                  onClick={clientSideSequenceWithQuietHours}
                  className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
                >
                  Последовательно (с тихими часами)
                </button>
              </div>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1 text-xs text-gray-700"><input type="checkbox" checked={useServerQuiet} onChange={(e) => setUseServerQuiet(e.target.checked)} /> Сдвиг тихих часов на сервере</label>
              </div>
            </div>
            {(posts || []).map((post) => (
              <div key={post.id} className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={selected.has(post.id)}
                  onChange={() => toggleSelected(post.id)}
                />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-900">{post.title || `Пост #${post.id}`}</span>
                    <span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full">{post.platform}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${post.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-gray-100'}`}>
                      {post.status}
                    </span>
                  </div>
                  {post.scheduled_at && (
                    <div className="text-xs text-gray-500">
                      {new Date(post.scheduled_at).toLocaleString('ru-RU')}
                    </div>
                  )}
                  <p className="text-sm text-gray-600 mt-2 whitespace-pre-wrap">{post.content.slice(0, 200)}</p>
                  {'error' in post && (post as any).error && (
                    <div className="mt-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded p-2">
                      Ошибка: {(post as any).error}
                    </div>
                  )}
                </div>
              </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => beginEdit(post)} className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm">
                    Редактировать
                  </button>
                <button
                  onClick={() => duplicateMutation.mutate(post.id)}
                  className="px-3 py-1 border border-indigo-300 text-indigo-700 rounded-lg hover:bg-indigo-50 text-sm"
                >
                  Дублировать
                </button>
                {post.status === 'failed' && (
                  <button
                    onClick={() => retryMutation.mutate(post.id)}
                    className="px-3 py-1 border border-amber-300 text-amber-700 rounded-lg hover:bg-amber-50 text-sm"
                  >
                    Повторить
                  </button>
                )}
                  <button
                    onClick={() => deleteMutation.mutate(post.id)}
                    className="px-3 py-1 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 text-sm"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            ))}
            {posts && posts.length === 0 && <div className="p-4 text-gray-500">Постов пока нет</div>}

            {/* Templates manager */}
            <div className="px-4 py-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Шаблоны</h3>
              <div className="border border-gray-200 rounded-lg divide-y">
                {(templates || []).map((t) => (
                  <div key={t.id} className="p-3 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                    <div className="min-w-0">
                      <div className="font-medium text-gray-900 truncate">{t.name}</div>
                      <div className="text-xs text-gray-500 truncate">{t.title || '(без заголовка)'} • {t.platform || '—'}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          setEditingTemplate(t.id)
                          setTemplateForm({ name: t.name, platform: t.platform || '', title: t.title || '', content: t.content, media_url: t.media_url || '' })
                        }}
                        className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
                      >
                        Редактировать
                      </button>
                      <button
                        onClick={() => applyTemplate(t.id)}
                        className="px-3 py-1 border border-indigo-300 text-indigo-700 rounded-lg hover:bg-indigo-50 text-sm"
                      >
                        Применить
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('Удалить шаблон?')) deleteTemplateMutation.mutate(t.id)
                        }}
                        className="px-3 py-1 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 text-sm"
                      >
                        Удалить
                      </button>
                    </div>
                  </div>
                ))}
                {templates && templates.length === 0 && <div className="p-3 text-gray-500">Шаблонов пока нет</div>}
              </div>

              {editingTemplate !== null && (
                <div className="mt-3 border border-gray-200 rounded-lg p-3">
                  <h4 className="font-medium text-gray-900 mb-2">Редактирование шаблона</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm text-gray-700 mb-1">Название</label>
                      <input
                        type="text"
                        value={templateForm.name}
                        onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-700 mb-1">Платформа (опционально)</label>
                      <input
                        type="text"
                        value={templateForm.platform}
                        onChange={(e) => setTemplateForm({ ...templateForm, platform: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                    <div className="md:col-span-2">
                      <label className="block text-sm text-gray-700 mb-1">Заголовок</label>
                      <input
                        type="text"
                        value={templateForm.title}
                        onChange={(e) => setTemplateForm({ ...templateForm, title: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                    <div className="md:col-span-2">
                      <label className="block text-sm text-gray-700 mb-1">Текст</label>
                      <textarea
                        rows={4}
                        value={templateForm.content}
                        onChange={(e) => setTemplateForm({ ...templateForm, content: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                    <div className="md:col-span-2">
                      <label className="block text-sm text-gray-700 mb-1">Медиа (URL)</label>
                      <input
                        type="text"
                        value={templateForm.media_url}
                        onChange={(e) => setTemplateForm({ ...templateForm, media_url: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                  </div>
                  <div className="mt-3 flex items-center gap-2">
                    <button
                      onClick={() => {
                        if (editingTemplate === null) return
                        if (!templateForm.name.trim() || !templateForm.content.trim()) {
                          showModal({
                            title: 'Недостаточно данных',
                            message: 'Заполните название и текст',
                            tone: 'error',
                          })
                          return
                        }
                        updateTemplateMutation.mutate({
                          id: editingTemplate,
                          payload: {
                            name: templateForm.name,
                            platform: templateForm.platform || undefined,
                            title: templateForm.title || undefined,
                            content: templateForm.content,
                            media_url: templateForm.media_url || undefined,
                          },
                        })
                      }}
                      className="px-3 py-1 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm"
                    >
                      Сохранить шаблон
                    </button>
                    <button
                      onClick={() => {
                        setEditingTemplate(null)
                        setTemplateForm({ name: '', platform: '', title: '', content: '', media_url: '' })
                      }}
                      className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
                    >
                      Отмена
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">{editing ? 'Редактирование поста' : 'Новый пост'}</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Платформа</label>
            <select
              value={form.platform}
              onChange={(e) => setForm({ ...form, platform: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="telegram">Telegram</option>
              <option value="vk">VK (пока не реализовано)</option>
              <option value="instagram">Instagram (пока не реализовано)</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {form.platform === 'telegram'
                ? 'Поддерживаются текст и изображение (по ссылке).'
                : form.platform === 'vk'
                ? 'Поддерживаются текст и изображение (будет загружено в альбом стены).'
                : 'В разработке.'}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Статус</label>
            <select
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="draft">draft</option>
              <option value="scheduled">scheduled</option>
              <option value="sent">sent</option>
              <option value="failed">failed</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Заголовок</label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Медиа (URL)</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={form.media_url}
                onChange={(e) => setForm({ ...form, media_url: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
              <label className="px-3 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 text-sm">
                Загрузить
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      uploadFile.mutate(e.target.files[0])
                    }
                  }}
                />
              </label>
            </div>
            {uploadFile.isPending && <div className="text-xs text-gray-500 mt-1">Загрузка...</div>}
            {form.media_url && (
              <div className="mt-2">
                <img
                  src={form.media_url}
                  alt="preview"
                  className="max-h-48 rounded border border-gray-200"
                  onError={() => {
                    /* ignore preview errors */
                  }}
                />
              </div>
            )}
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Текст</label>
            <textarea
              rows={6}
              value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Время публикации</label>
            <input
              type="datetime-local"
              value={form.scheduled_at}
              onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <p className="text-xs text-gray-500 mt-1">Оставьте пустым и статус draft для подготовки черновика.</p>
            <div className="mt-2 flex items-center gap-2">
              <button
                type="button"
                onClick={scheduleNow}
                className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
              >
                Запланировать на сейчас
              </button>
              <button
                type="button"
                onClick={() => setShowPreview(true)}
                className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm"
              >
                Предпросмотр
              </button>
            </div>
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <button onClick={onSubmit} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700" disabled={createMutation.isPending || updateMutation.isPending}>
            {editing ? 'Сохранить' : 'Создать'}
          </button>
          {editing && (
            <button
              onClick={() => {
                setEditing(null)
                setForm(initialForm)
              }}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
            >
              Отмена
            </button>
          )}
        </div>
      </div>

      {showPreview && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-lg font-semibold">Предпросмотр ({form.platform})</div>
              <button onClick={() => setShowPreview(false)} className="text-gray-500 hover:text-gray-700">✕</button>
            </div>
            <div className="border border-gray-200 rounded-lg p-3">
              {form.media_url ? (
                <div className="mb-3">
                  <img src={form.media_url} alt="preview" className="max-h-64 rounded" />
                </div>
              ) : null}
              {form.title && <div className="font-semibold mb-1">{form.title}</div>}
              <div className="whitespace-pre-wrap text-sm text-gray-800">{form.content}</div>
            </div>
            <div className="mt-3 text-right">
              <button onClick={() => setShowPreview(false)} className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm">Закрыть</button>
            </div>
          </div>
        </div>
      )}

      {showBulkPreview && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-lg font-semibold">Предпросмотр публикаций (первые 5)</div>
              <button onClick={() => setShowBulkPreview(false)} className="text-gray-500 hover:text-gray-700">✕</button>
            </div>
            <div className="border border-gray-200 rounded-lg divide-y">
              {previewList.map((row) => (
                <div key={row.id} className="p-2 text-sm flex items-center justify-between">
                  <span className="truncate mr-2">{row.title}</span>
                  <span className="text-gray-600">{row.time || '—'}</span>
                </div>
              ))}
              {previewList.length === 0 && <div className="p-3 text-gray-500">Нет выбранных постов или не задан старт</div>}
            </div>
            <div className="mt-3 text-right">
              <button onClick={() => setShowBulkPreview(false)} className="px-3 py-1 border border-gray-300 rounded-lg hover:bg-gray-100 text-sm">Закрыть</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SocialPosts


