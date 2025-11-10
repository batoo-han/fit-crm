import { useState, useEffect } from 'react'

interface EditableCellProps {
  value: string | number
  onSave: (value: string | number) => void
  type?: 'text' | 'number' | 'select'
  options?: string[]
  className?: string
}

const EditableCell: React.FC<EditableCellProps> = ({
  value,
  onSave,
  type = 'text',
  options = [],
  className = '',
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(String(value))

  useEffect(() => {
    setEditValue(String(value))
  }, [value])

  const handleSave = () => {
    if (type === 'number') {
      const numValue = parseFloat(editValue)
      if (!isNaN(numValue)) {
        onSave(numValue)
      } else {
        onSave(value)
      }
    } else {
      onSave(editValue)
    }
    setIsEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave()
    } else if (e.key === 'Escape') {
      setEditValue(String(value))
      setIsEditing(false)
    }
  }

  if (isEditing) {
    if (type === 'select' && options.length > 0) {
      // Текущее значение как дефолт, не подставляем автоматически пустое
      const currentValue = String(value ?? '')
      const effectiveValue = options.includes(currentValue) ? currentValue : ''
      // Если мы открыли редактор и значение не совпадает с текущим — синхронизируем один раз
      if (editValue !== currentValue && editValue !== effectiveValue) {
        setEditValue(effectiveValue)
      }
      
      return (
        <select
          value={editValue}
          onChange={(e) => {
            setEditValue(e.target.value)
          }}
          onBlur={handleSave}
          onKeyDown={handleKeyDown}
          autoFocus
          className={`w-full px-2 py-1 border border-primary-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 ${className}`}
        >
          {options
            // Не добавляем дубликаты и приводим к строке
            .filter((opt, idx, arr) => arr.indexOf(opt) === idx)
            .map((option) => (
              <option key={option || 'empty'} value={option}>
                {option || '(пусто)'}
              </option>
            ))}
        </select>
      )
    }

    return (
      <input
        type={type}
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        autoFocus
        className={`w-full px-2 py-1 border border-primary-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 ${className}`}
      />
    )
  }

  return (
    <div
      onClick={() => setIsEditing(true)}
      className={`px-2 py-1 cursor-pointer hover:bg-primary-50 hover:border hover:border-primary-200 rounded transition-colors ${className}`}
      title="Нажмите для редактирования"
    >
      {value || <span className="text-gray-400">-</span>}
    </div>
  )
}

interface EditableTableProps {
  data: any[]
  columns: Array<{
    key: string
    label: string
    type?: 'text' | 'number' | 'select'
    options?: string[]
    editable?: boolean
  }>
  onCellChange: (rowIndex: number, columnKey: string, value: any) => void
}

const EditableTable: React.FC<EditableTableProps> = ({
  data,
  columns,
  onCellChange,
}) => {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 border border-gray-300">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-300"
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.map((row, rowIndex) => (
            <tr key={rowIndex} className="hover:bg-gray-50">
              {columns.map((column) => (
                <td
                  key={column.key}
                  className="px-4 py-2 text-sm text-gray-900 border-r border-gray-200"
                >
                  {column.editable !== false ? (
                    <EditableCell
                      value={row[column.key] || ''}
                      onSave={(value) => onCellChange(rowIndex, column.key, value)}
                      type={column.type || 'text'}
                      options={column.options}
                    />
                  ) : (
                    <span>{row[column.key] || '-'}</span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default EditableTable

