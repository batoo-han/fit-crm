import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from 'react'
import { createPortal } from 'react-dom'

export type ModalTone = 'info' | 'success' | 'error' | 'warning'

type ModalAction = {
  label: string
  onClick?: () => void
  variant?: 'primary' | 'secondary'
  closeOnClick?: boolean
}

export type ModalOptions = {
  title?: string
  message: ReactNode
  tone?: ModalTone
  actions?: ModalAction[]
  autoCloseMs?: number
  onClose?: () => void
}

type ModalState = ModalOptions & { id: number }

type ModalContextValue = {
  showModal: (options: ModalOptions) => void
  hideModal: () => void
}

const ModalContext = createContext<ModalContextValue | undefined>(undefined)

const TONE_CONFIG: Record<ModalTone, { icon: string; accent: string }> = {
  info: { icon: 'ℹ', accent: 'text-sky-400' },
  success: { icon: '✔', accent: 'text-emerald-400' },
  error: { icon: '⚠', accent: 'text-rose-400' },
  warning: { icon: '⚠', accent: 'text-amber-400' },
}

let modalIdCounter = 0

export const ModalProvider = ({ children }: { children: ReactNode }) => {
  const [modal, setModal] = useState<ModalState | null>(null)

  const hideModal = useCallback(() => {
    if (modal?.onClose) {
      modal.onClose()
    }
    setModal(null)
  }, [modal])

  const showModal = useCallback((options: ModalOptions) => {
    modalIdCounter += 1
    const actions: ModalAction[] = options.actions && options.actions.length > 0
      ? options.actions
      : [{ label: 'ОК', variant: 'primary', closeOnClick: true }]

    setModal({
      id: modalIdCounter,
      tone: options.tone ?? 'info',
      title: options.title ?? 'Уведомление',
      message: options.message,
      actions,
      autoCloseMs: options.autoCloseMs,
      onClose: options.onClose,
    })
  }, [])

  useEffect(() => {
    if (!modal?.autoCloseMs) {
      return
    }

    const timer = setTimeout(() => {
      hideModal()
    }, modal.autoCloseMs)

    return () => clearTimeout(timer)
  }, [modal, hideModal])

  const value = useMemo<ModalContextValue>(() => ({ showModal, hideModal }), [showModal, hideModal])

  return (
    <ModalContext.Provider value={value}>
      {children}
      {modal && <ModalRoot modal={modal} onClose={hideModal} />}
    </ModalContext.Provider>
  )
}

type ModalRootProps = {
  modal: ModalState
  onClose: () => void
}

const ModalRoot = ({ modal, onClose }: ModalRootProps) => {
  const tone = modal.tone ?? 'info'
  const toneConfig = TONE_CONFIG[tone]

  useEffect(() => {
    const { style } = document.body
    const previousOverflow = style.overflow
    style.overflow = 'hidden'
    return () => {
      style.overflow = previousOverflow
    }
  }, [])

  return createPortal(
    <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-950/70 px-4 backdrop-blur-sm">
      <div className="absolute inset-0" onClick={onClose} aria-hidden="true" />
      <div className="relative w-full max-w-md rounded-2xl border border-slate-700/60 bg-slate-900/95 p-6 shadow-2xl ring-1 ring-slate-600/30">
        <button
          type="button"
          aria-label="Закрыть"
          className="absolute right-3 top-3 text-xl text-slate-400 transition hover:text-slate-100"
          onClick={onClose}
        >
          ×
        </button>
        <div className="flex items-start gap-4">
          <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-800/80 text-2xl ${toneConfig.accent}`}>
            {toneConfig.icon}
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-slate-100">
              {modal.title}
            </h3>
            <div className="mt-3 text-sm leading-relaxed text-slate-300">
              {typeof modal.message === 'string'
                ? modal.message.split('\n').map((line, index) => (
                    <p key={index} className={index > 0 ? 'mt-2' : undefined}>
                      {line}
                    </p>
                  ))
                : modal.message}
            </div>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          {modal.actions?.map((action, index) => {
            const handleClick = () => {
              action.onClick?.()
              if (action.closeOnClick !== false) {
                onClose()
              }
            }
            const baseClasses = 'rounded-xl px-4 py-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2'
            const variantClasses = action.variant === 'secondary'
              ? 'border border-slate-600/60 bg-transparent text-slate-200 hover:border-slate-400/80'
              : 'bg-primary-600 text-white shadow-lg shadow-primary-500/20 hover:bg-primary-500'
            return (
              <button key={index} type="button" onClick={handleClick} className={`${baseClasses} ${variantClasses}`}>
                {action.label}
              </button>
            )
          })}
        </div>
      </div>
    </div>,
    document.body
  )
}

export const useModal = () => {
  const context = useContext(ModalContext)
  if (!context) {
    throw new Error('useModal must be used within a ModalProvider')
  }
  return context
}
