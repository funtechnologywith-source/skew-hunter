import { Check, X } from 'lucide-react'
import { clsx } from 'clsx'

interface ConditionRowProps {
  label: string
  value: number | string
  threshold?: number | string
  comparison?: 'gte' | 'lte' | 'gt' | 'lt' | 'eq' | 'in'
  passed: boolean
  showComparison?: boolean
}

export function ConditionRow({
  label,
  value,
  threshold,
  comparison = 'gte',
  passed,
  showComparison = true
}: ConditionRowProps) {
  const comparisonSymbol = {
    gte: '>=',
    lte: '<=',
    gt: '>',
    lt: '<',
    eq: '=',
    in: 'in'
  }[comparison]

  const formattedValue = typeof value === 'number' ? value.toFixed(2) : value
  const formattedThreshold = typeof threshold === 'number' ? threshold.toFixed(2) : threshold

  return (
    <div className="flex items-center justify-between py-1">
      <div className="flex items-center gap-2">
        <span className="text-sm text-secondary">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <span
          className={clsx(
            'text-sm font-mono tabular-nums',
            passed ? 'text-profit' : 'text-loss'
          )}
        >
          {formattedValue}
        </span>
        {showComparison && threshold !== undefined && (
          <span className="text-xs text-muted">
            {comparisonSymbol} {formattedThreshold}
          </span>
        )}
        {passed ? (
          <Check className="w-4 h-4 text-profit" />
        ) : (
          <X className="w-4 h-4 text-loss" />
        )}
      </div>
    </div>
  )
}
