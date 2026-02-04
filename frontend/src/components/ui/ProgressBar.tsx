import { clsx } from 'clsx'

interface ProgressBarProps {
  value: number
  max?: number
  min?: number
  color?: 'profit' | 'loss' | 'warning' | 'default'
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  showMarkers?: boolean
  className?: string
  animate?: boolean
}

export function ProgressBar({
  value,
  max = 100,
  min = 0,
  color = 'default',
  size = 'md',
  showLabel = false,
  showMarkers = false,
  className,
  animate = false
}: ProgressBarProps) {
  const range = max - min
  const percentage = Math.min(Math.max(((value - min) / range) * 100, 0), 100)

  return (
    <div className={clsx('w-full', className)}>
      <div
        className={clsx(
          'w-full bg-border rounded-full overflow-hidden relative',
          {
            'h-1': size === 'sm',
            'h-2': size === 'md',
            'h-3': size === 'lg',
          }
        )}
      >
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-300',
            {
              'bg-profit': color === 'profit',
              'bg-loss': color === 'loss',
              'bg-white': color === 'warning',
              'bg-white/50': color === 'default',
            },
            animate && 'progress-animate'
          )}
          style={{ width: `${percentage}%` }}
        />
        {showMarkers && (
          <>
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-loss/50"
              style={{ left: '0%' }}
              title={`Stop: ${min}`}
            />
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-profit/50"
              style={{ left: '100%' }}
              title={`High: ${max}`}
            />
          </>
        )}
      </div>
      {showLabel && (
        <span className="text-xs text-secondary mt-1">
          {value.toFixed(1)} / {max}
        </span>
      )}
    </div>
  )
}
