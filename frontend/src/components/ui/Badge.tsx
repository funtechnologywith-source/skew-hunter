import { clsx } from 'clsx'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'call' | 'put' | 'win' | 'loss' | 'warning'
  className?: string
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
        {
          'bg-white/5 border border-white/10 text-secondary': variant === 'default',
          'bg-profit/15 text-profit border border-profit/20': variant === 'call' || variant === 'win',
          'bg-loss/15 text-loss border border-loss/20': variant === 'put' || variant === 'loss',
          'bg-white/10 text-white border border-white/20': variant === 'warning',
        },
        className
      )}
    >
      {children}
    </span>
  )
}
