import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useState, useMemo, useEffect } from 'react'
import EditableTable from '../components/EditableTable'
import React from 'react'

const ProgramView = () => {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
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
      setLocalProgramData(JSON.parse(JSON.stringify(program.program_data)))
    }
  }, [program?.program_data])

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
    if (!program?.program_data?.weeks) return []
    return Object.keys(program.program_data.weeks)
      .map(Number)
      .sort((a, b) => a - b)
  }, [program?.program_data])

  const handleCellChange = (rowIndex: number, columnKey: string, value: any) => {
    const dataSource = localProgramData || program?.program_data
    if (!dataSource) return

    const row = filteredData[rowIndex]
    const weeks = JSON.parse(JSON.stringify(dataSource.weeks)) // Deep copy
    const weekRecords = [...weeks[row.week]]

    // Обновляем значение в соответствующей записи
    const record = weekRecords[row._recordIndex]
    if (record) {
      // Маппинг колонок на поля в данных
      const fieldMap: Record<string, string> = {
        day: 'Day',
        session: 'Session',
        microcycle: 'Microcycle',
        deload: 'Deload',
        exercise_name: `Ex${row.exercise_num}_Name`,
        sets: `Ex${row.exercise_num}_Sets`,
        reps: `Ex${row.exercise_num}_Reps`,
        pattern: `Ex${row.exercise_num}_Pattern`,
        alt: `Ex${row.exercise_num}_Alt`,
        notes: `Ex${row.exercise_num}_Notes`,
      }

      const fieldName = fieldMap[columnKey]
      if (fieldName) {
        // Преобразуем значение для deload (должно быть число)
        if (columnKey === 'deload') {
          record[fieldName] = value === '1' || value === 1 ? 1 : 0
        } else if (columnKey === 'sets' || columnKey === 'day') {
          record[fieldName] = typeof value === 'number' ? value : parseInt(value) || 0
        } else {
          record[fieldName] = value
        }

        weeks[row.week] = weekRecords
        const updatedProgramData = {
          ...dataSource,
          weeks,
        }

        // Обновляем локальные данные вместо немедленного сохранения
        setLocalProgramData(updatedProgramData)
        setHasUnsavedChanges(true)
      }
    }
  }

  const handleSave = () => {
    if (localProgramData) {
      updateMutation.mutate(localProgramData)
    }
  }

  const handleCancel = () => {
    setLocalProgramData(null)
    setHasUnsavedChanges(false)
    queryClient.invalidateQueries({ queryKey: ['program', id] })
  }

  // Определяем колонки таблицы
  const columns = [
    { key: 'week', label: 'Неделя', type: 'number' as const, editable: false },
    { key: 'day', label: 'День', type: 'number' as const },
    { key: 'session', label: 'Тренировка', type: 'text' as const },
    {
      key: 'microcycle',
      label: 'Микроцикл',
      type: 'select' as const,
      options: ['FB', 'UL', 'PPL', 'Upper', 'Lower', 'Full Body', ''],
    },
    {
      key: 'deload',
      label: 'Разгрузка',
      type: 'select' as const,
      options: ['0', '1'],
    },
    { key: 'exercise_name', label: 'Упражнение', type: 'text' as const },
    { key: 'sets', label: 'Подходы', type: 'number' as const },
    { key: 'reps', label: 'Повторения', type: 'text' as const },
    {
      key: 'pattern',
      label: 'Паттерн',
      type: 'select' as const,
      options: [
        '',
        'Колено-доминант',
        'Таз-доминант',
        'Тяга горизонтальная',
        'Тяга вертикальная',
        'Жим горизонтальный',
        'Жим вертикальный',
        'Изоляция',
        'Кардио',
        'Другое',
      ],
    },
    { key: 'alt', label: 'Альтернативы', type: 'text' as const },
    { key: 'notes', label: 'Примечания', type: 'text' as const },
  ]

  if (isLoading) {
    return <div>Загрузка...</div>
  }

  if (!program) {
    return <div>Программа не найдена</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Программа #{program.id}</h1>
          <p className="text-gray-500 mt-2">
            Клиент: #{program.client_id} | Тип: {program.program_type}
          </p>
        </div>
        {hasUnsavedChanges && (
          <div className="flex gap-2">
            <button
              onClick={handleCancel}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Отмена
            </button>
            <button
              onClick={handleSave}
              disabled={updateMutation.isPending}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {updateMutation.isPending ? 'Сохранение...' : 'Сохранить изменения'}
            </button>
          </div>
        )}
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
            <div className="text-sm text-gray-500">
              Всего записей: {filteredData.length}
            </div>
          </div>
          <div className="mb-4 text-sm text-gray-600">
            💡 Нажмите на любую ячейку для редактирования. Не забудьте нажать "Сохранить изменения" после редактирования.
            {hasUnsavedChanges && (
              <span className="ml-2 text-orange-600 font-medium">
                ⚠️ Есть несохраненные изменения
              </span>
            )}
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
    </div>
  )
}

export default ProgramView
