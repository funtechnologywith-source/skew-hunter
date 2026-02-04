import { useEffect, useState, useRef } from 'react'
import { clsx } from 'clsx'

interface AnimatedNumberProps {
  value: number
  decimals?: number
  prefix?: string
  suffix?: string
  className?: string
  colorize?: boolean
  duration?: number
}

export function AnimatedNumber({
  value,
  decimals = 2,
  prefix = '',
  suffix = '',
  className,
  colorize = false,
  duration = 300
}: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(value)
  const prevValue = useRef(value)
  const animationRef = useRef<number>()

  useEffect(() => {
    const startValue = prevValue.current
    const endValue = value
    const startTime = performance.now()

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)

      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      const current = startValue + (endValue - startValue) * eased

      setDisplayValue(current)

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate)
      } else {
        prevValue.current = endValue
      }
    }

    animationRef.current = requestAnimationFrame(animate)

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [value, duration])

  const formattedValue = displayValue.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })

  return (
    <span
      className={clsx(
        'tabular-nums font-mono',
        colorize && {
          'text-profit': value > 0,
          'text-loss': value < 0,
          'text-primary': value === 0
        },
        className
      )}
    >
      {prefix}{formattedValue}{suffix}
    </span>
  )
}
