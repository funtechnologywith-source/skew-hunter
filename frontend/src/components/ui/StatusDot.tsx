import { clsx } from 'clsx'

interface StatusDotProps {
  status: 'connected' | 'disconnected' | 'warning' | 'live' | 'paper' | 'off'
  pulse?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export function StatusDot({ status, pulse = false, size = 'md' }: StatusDotProps) {
  return (
    <span className="relative inline-flex">
      <span
        className={clsx(
          'rounded-full',
          {
            'w-2 h-2': size === 'sm',
            'w-2.5 h-2.5': size === 'md',
            'w-3 h-3': size === 'lg',
          },
          {
            'bg-profit': status === 'live',
            'bg-white': status === 'connected' || status === 'paper',
            'bg-loss': status === 'disconnected',
            'bg-white/50': status === 'warning',
            'bg-secondary': status === 'off',
          }
        )}
      />
      {pulse && (status === 'connected' || status === 'live' || status === 'paper') && (
        <span
          className={clsx(
            'absolute rounded-full opacity-75 animate-ping',
            status === 'live' ? 'bg-profit' : 'bg-white',
            {
              'w-2 h-2': size === 'sm',
              'w-2.5 h-2.5': size === 'md',
              'w-3 h-3': size === 'lg',
            }
          )}
        />
      )}
    </span>
  )
}
