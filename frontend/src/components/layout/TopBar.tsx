import { Link, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import { Activity, History, Settings, Target } from 'lucide-react'
import { StatusDot } from '../ui/StatusDot'
import { Badge } from '../ui/Badge'
import { formatNumber } from '../../lib/formatters'

interface TopBarProps {
  spot?: number
  spotChange?: number
  vix?: number
  mode?: string
  executionMode?: string
  broker?: string
  connected?: boolean
  status?: string
}

export function TopBar({
  spot = 0,
  spotChange = 0,
  vix = 15,
  mode = 'BALANCED',
  executionMode = 'OFF',
  broker = 'UPSTOX',
  connected = false,
  status = 'STOPPED'
}: TopBarProps) {
  const location = useLocation()

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: Activity },
    { path: '/trade', label: 'Trade', icon: Target },
    { path: '/history', label: 'History', icon: History },
    { path: '/settings', label: 'Settings', icon: Settings },
  ]

  return (
    <header className="sticky top-0 z-50 bg-background/95 backdrop-blur border-b border-border">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          {/* Logo and Status */}
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="flex items-center gap-2">
              <Target className="w-5 h-5 text-white" />
              <span className="font-semibold text-white tracking-tight">Skew Hunter</span>
            </Link>

            <div className="flex items-center gap-2">
              <Badge variant={status === 'TRADING' ? 'call' : status === 'SCANNING' ? 'warning' : 'default'}>
                {status}
              </Badge>
              <Badge>{mode}</Badge>
            </div>
          </div>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={clsx(
                  'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors',
                  location.pathname === item.path
                    ? 'bg-card text-primary'
                    : 'text-secondary hover:text-primary hover:bg-card'
                )}
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Market Info */}
          <div className="flex items-center gap-4">
            {/* Spot Price */}
            <div className="text-right">
              <div className="font-mono text-lg text-primary tabular-nums">
                {formatNumber(spot, 0)}
              </div>
              <div className={clsx(
                'text-xs font-mono tabular-nums',
                spotChange >= 0 ? 'text-profit' : 'text-loss'
              )}>
                {spotChange >= 0 ? '+' : ''}{spotChange.toFixed(2)}%
              </div>
            </div>

            {/* VIX */}
            <div className="text-right">
              <div className="text-xs text-secondary">VIX</div>
              <div className="font-mono text-sm text-primary tabular-nums">
                {vix.toFixed(2)}
              </div>
            </div>

            {/* Connection Status */}
            <div className="flex items-center gap-2">
              <StatusDot
                status={connected ? (executionMode === 'LIVE' ? 'live' : executionMode === 'PAPER' ? 'paper' : 'connected') : 'disconnected'}
                pulse={connected}
              />
              <span className="text-xs text-secondary">
                {executionMode}/{broker}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
