import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useState, useMemo, useEffect } from 'react'
import EditableTable from '../components/EditableTable'
import React from 'react'
import { useModal } from '../components/ui/modal/ModalContext'

const ProgramView = () => {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const { showModal } = useModal()
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null)

  const { data: program, isLoading } = useQuery({
    queryKey: ['program', id],
    queryFn: async () => {
      const response = await api.get(`/programs/${id}`)
      return response.data
    },
  })

  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')
  const [localProgramData, setLocalProgramData] = useState<any>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [versions, setVersions] = useState<Array<{ id: number; created_at?: string; created_by?: number }>>([])

  const updateMutation = useMutation({
    mutationFn: async (programData: any) => {
      const response = await api.put(`/programs/${id}`, {
        program_data: programData,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['program', id] })
      setSaveStatus('saved')
      setHasUnsavedChanges(false)
      setTimeout(() => setSaveStatus('idle'), 2000)
    },
    onMutate: () => {
      setSaveStatus('saving')
    },
  })

  // Инициализируем локальные данные при загрузке программы
  React.useEffect(() => {
    if (program?.program_data && !localProgramData) {
      const cloned = JSON.parse(JSON.stringify(program.program_data))
      setLocalProgramData(cloned)
      if (cloned?.weeks) {
        const firstWeek = Object.keys(cloned.weeks)
          .map(Number)
          .sort((a, b) => a - b)[0]
        if (firstWeek) {
          setSelectedWeek(firstWeek)
        }
      }
    }
  }, [program?.program_data, localProgramData])

  // Warn user if there are unsaved changes when leaving the page
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [hasUnsavedChanges])

  // Загрузка списка версий
  useQuery({
    queryKey: ['program-versions', id],
    queryFn: async () => {
      const response = await api.get(`/programs/${id}/versions`)
      setVersions(response.data || [])
      return response.data
    },
  })

  // Преобразуем program_data в табличный формат (используем локальные данные если есть изменения)
  const tableData = useMemo(() => {
    const dataSource = localProgramData || program?.program_data
    if (!dataSource?.weeks) return []

    const weeks = dataSource.weeks
    const allRows: any[] = []

    // Сортируем недели
    const sortedWeeks = Object.keys(weeks)
      .map(Number)
      .sort((a, b) => a - b)

    sortedWeeks.forEach((weekNum) => {
      const weekRecords = weeks[weekNum] || []
      weekRecords.forEach((record: any, recordIndex: number) => {
        // Создаем строку для каждого упражнения (Ex1-Ex5)
        for (let i = 1; i <= 5; i++) {
          const exName = record[`Ex${i}_Name`]
          if (exName) {
            allRows.push({
              week: weekNum,
              day: record.Day || '',
              session: record.Session || '',
              microcycle: record.Microcycle || '',
              deload: String(record.Deload || 0),
              exercise_num: i,
              exercise_name: exName,
              sets: record[`Ex${i}_Sets`] || '',
              reps: record[`Ex${i}_Reps`] || '',
              pattern: record[`Ex${i}_Pattern`] || '',
              alt: record[`Ex${i}_Alt`] || '',
              notes: record[`Ex${i}_Notes`] || '',
              // Сохраняем оригинальный индекс записи для обновления
              _recordIndex: recordIndex,
            })
          }
        }
      })
    })

    return allRows
  }, [localProgramData || program?.program_data])

  // Фильтруем данные по выбранной неделе
  const filteredData = useMemo(() => {
    if (selectedWeek === null) return tableData
    return tableData.filter((row) => row.week === selectedWeek)
  }, [tableData, selectedWeek])

  // Получаем список недель
  const availableWeeks = useMemo(() => {
    const dataSource = localProgramData || program?.program_data
    if (!dataSource?.weeks) return [] as number[]
    return Object.keys(dataSource.weeks)
      .map(Number)
      .sort((a, b) => a - b)
  }, [localProgramData || program?.program_data])

  // Обработчик изменений ячеек
  const handleCellChange = (rowIndex: number, columnId: string, value: any) => {
    if (!localProgramData) return

    setLocalProgramData((prevData: any) => {
      const newData = JSON.parse(JSON.stringify(prevData))
      const tableRows = filteredData
      const targetRow = tableRows[rowIndex]
      const recordIndex = targetRow?._recordIndex
      const week = targetRow?.week

      if (recordIndex !== undefined && week !== undefined) {
        const record = newData.weeks[week][recordIndex]
        if (columnId === 'exercise_name') {
          record[`Ex${targetRow.exercise_num}_Name`] = value
        } else if (columnId === 'sets') {
          record[`Ex${targetRow.exercise_num}_Sets`] = value
        } else if (columnId === 'reps') {
          record[`Ex${targetRow.exercise_num}_Reps`] = value
        } else if (columnId === 'pattern') {
          record[`Ex${targetRow.exercise_num}_Pattern`] = value
        } else if (columnId === 'alt') {
          record[`Ex${targetRow.exercise_num}_Alt`] = value
        } else if (columnId === 'notes') {
          record[`Ex${targetRow.exercise_num}_Notes`] = value
        } else if (columnId === 'deload') {
          record['Deload'] = value === '1' ? 1 : 0
        }
      }

      return newData
    })

    setHasUnsavedChanges(true)
  }

  // Сохранение изменений
  const handleSave = () => {
    if (!localProgramData) return
    updateMutation.mutate(localProgramData)
  }

  // Отмена изменений
  const handleCancel = () => {
    if (program?.program_data) {
      const cloned = JSON.parse(JSON.stringify(program.program_data))
      setLocalProgramData(cloned)
      setHasUnsavedChanges(false)
    }
  }

  // Колонки таблицы
  const columns = React.useMemo(
    () => [
      { key: 'week', label: 'Неделя' },
      { key: 'day', label: 'День' },
      { key: 'session', label: 'Сессия' },
      { key: 'microcycle', label: 'Микроцикл' },
      { key: 'deload', label: 'Делод', type: 'select' as const, options: ['0', '1'] },
      { key: 'exercise_name', label: 'Упражнение', editable: true },
      { key: 'sets', label: 'Подходы', editable: true },
      { key: 'reps', label: 'Повторения', editable: true },
      { key: 'pattern', label: 'Паттерн', editable: true },
      { key: 'alt', label: 'Альтернатива', editable: true },
      { key: 'notes', label: 'Заметки', editable: true },
    ],
    []
  )

  if (isLoading) {
    return <div>Загрузка...</div>
  }

  if (!program) {
    return <div>Программа не найдена</div>
  }

  return (
    <div>
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-8">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-gray-900">Программа #{program.id}</h1>
          <div className="text-sm text-gray-600 space-y-1">
            <p>
              <span className="font-medium">Клиент:</span> #{program.client_id}
            </p>
            <p>
              <span className="font-medium">Тип:</span> {program.program_type || '—'}
            </p>
            <p>
              <span className="font-medium">Создана:</span>{' '}
              {program.created_at ? new Date(program.created_at).toLocaleString('ru-RU') : '—'}
            </p>
            <p>
              <span className="font-medium">Назначена:</span>{' '}
              {program.assigned_at ? new Date(program.assigned_at).toLocaleString('ru-RU') : '—'}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={async () => {
              try {
                const resp = await api.get(`/programs/${id}/export-pdf`)
                const url = resp.data?.url
                if (url) {
                  // Используем полный URL к API для обхода React Router
                  // В development используем localhost:8009, в production - текущий домен
                  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 
                    (import.meta.env.DEV ? 'http://localhost:8009' : window.location.origin)
                  const fullUrl = `${apiBaseUrl}${url}`
                  window.open(fullUrl, '_blank')
                }
              } catch (error: any) {
                showModal({
                  title: 'Не удалось экспортировать PDF',
                  message: error?.response?.data?.detail || 'Попробуйте повторить позже.',
                  tone: 'error',
                })
              }
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
            title="Экспортировать в PDF"
          >
            Экспорт PDF
          </button>
          <button
            onClick={async () => {
              const message = prompt('Сообщение к программе (необязательно):', 'Ваша персональная программа тренировок')
              const useTelegram = confirm('Отправить в Telegram? (Да/Нет)')
              const useEmail = confirm('Отправить на e-mail? (Да/Нет)')
              const channels: string[] = []
              if (useTelegram) channels.push('telegram')
              if (useEmail) channels.push('email')
              if (channels.length === 0) return
              try {
                const resp = await api.post(`/programs/${id}/send`, { channels, message })
                const results = resp.data?.results || {}
                const tg = results.telegram ? (results.telegram.success ? 'Telegram: отправлено' : `Telegram: ${results.telegram.error || 'ошибка'}`) : null
                const em = results.email ? (results.email.success ? 'Email: отправлено' : `Email: ${results.email.error || 'ошибка'}`) : null
                const summary = [tg, em].filter(Boolean).join('\n') || 'Готово'
                const hasErrors = [tg, em].some((line) => line && line.toLowerCase().includes('ошибка'))
                showModal({
                  title: 'Результат отправки',
                  message: summary,
                  tone: hasErrors ? 'warning' : 'success',
                })
              } catch (error: any) {
                showModal({
                  title: 'Не удалось отправить программу',
                  message: error?.response?.data?.detail || 'Попробуйте позже или отправьте вручную.',
                  tone: 'error',
                })
              }
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
            title="Отправить клиенту (Telegram/E-mail)"
          >
            Отправить
          </button>
          {hasUnsavedChanges && (
            <span className="text-xs text-amber-600 bg-amber-100 px-2 py-1 rounded-full">
              Есть несохранённые изменения
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={!hasUnsavedChanges || updateMutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {updateMutation.isPending ? 'Сохранение...' : 'Сохранить изменения'}
          </button>
          <button
            onClick={handleCancel}
            disabled={!hasUnsavedChanges}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 disabled:opacity-50"
          >
            Отменить изменения
          </button>
        </div>
      </div>

      {/* Фильтр по неделям */}
      {availableWeeks.length > 0 && (
        <div className="mb-6 bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-gray-700">Фильтр по неделям:</span>
            <button
              onClick={() => setSelectedWeek(null)}
              className={`px-3 py-1 rounded-lg text-sm ${
                selectedWeek === null
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Все недели
            </button>
            {availableWeeks.map((week) => (
              <button
                key={week}
                onClick={() => setSelectedWeek(week)}
                className={`px-3 py-1 rounded-lg text-sm ${
                  selectedWeek === week
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Неделя {week}
              </button>
            ))}
            <div className="ml-auto">
              <button
                onClick={async () => {
                  try {
                    await api.post(`/programs/${id}/versions`)
                    // refresh page data next time if needed
                    showModal({
                      title: 'Снимок сохранён',
                      message: 'Снимок версии сохранён',
                      tone: 'success',
                    })
                  } catch (error: any) {
                    showModal({
                      title: 'Не удалось создать снимок',
                      message: error?.response?.data?.detail || 'Попробуйте позже.',
                      tone: 'error',
                    })
                  }
                }}
                className="px-3 py-1 rounded-lg text-sm border border-gray-300 hover:bg-gray-100"
                title="Создать снимок текущей версии"
              >
                Создать снимок
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Редактируемая таблица */}
      {filteredData.length > 0 ? (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-900">
              {selectedWeek !== null ? `Неделя ${selectedWeek}` : 'Все тренировки'}
            </h2>
            <div className="text-sm text-gray-500">Всего упражнений: {filteredData.length}</div>
          </div>
          <div className="mb-4 text-sm text-gray-600">
            💡 Нажмите на ячейку, чтобы изменить упражнение или параметры. После правок сохраните изменения.
          </div>
          <EditableTable
            data={filteredData}
            columns={columns}
            onCellChange={handleCellChange}
          />
          {saveStatus === 'saving' && (
            <div className="mt-4 text-sm text-primary-600 flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Сохранение изменений...
            </div>
          )}
          {saveStatus === 'saved' && !hasUnsavedChanges && (
            <div className="mt-4 text-sm text-green-600">
              ✓ Изменения сохранены
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-500">Нет данных для отображения</p>
        </div>
      )}

      {/* Текстовое представление (для справки) */}
      {program.formatted_program && (
        <details className="mt-6 bg-white rounded-lg shadow p-6">
          <summary className="cursor-pointer text-sm font-medium text-gray-700">
            Текстовое представление программы
          </summary>
          <div className="mt-4">
            <pre className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded-lg">
              {program.formatted_program}
            </pre>
          </div>
        </details>
      )}

      {versions.length > 0 && (
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">История версий</h3>
          <div className="space-y-2">
            {versions.map((v) => (
              <div key={v.id} className="flex items-center justify-between text-sm border-b pb-2">
                <div className="text-gray-700">
                  <span className="font-medium">Версия #{v.id}</span>{' '}
                  <span className="text-gray-500">
                    {v.created_at ? new Date(v.created_at).toLocaleString('ru-RU') : ''}
                  </span>
                </div>
                <button
                  onClick={async () => {
                    if (!confirm('Восстановить эту версию? Несохранённые изменения будут потеряны.')) return
                    await api.post(`/programs/versions/${v.id}/restore`)
                    setLocalProgramData(null)
                    setHasUnsavedChanges(false)
                    queryClient.invalidateQueries({ queryKey: ['program', id] })
                    // Перезагрузка списка версий
                    const res = await api.get(`/programs/${id}/versions`)
                    setVersions(res.data || [])
                  }}
                  className="px-3 py-1 rounded-lg border border-gray-300 hover:bg-gray-100"
                >
                  Восстановить
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default ProgramView
