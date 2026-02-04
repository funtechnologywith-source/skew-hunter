import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  TrendingUp, TrendingDown, Clock, AlertTriangle,
  ChevronDown, ChevronUp, DoorOpen, Shield,
  Activity, Zap
} from 'lucide-react'
import { TopBar } from '../components/layout/TopBar'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { AnimatedNumber } from '../components/ui/AnimatedNumber'
import { ProgressBar } from '../components/ui/ProgressBar'
import { useWebSocket } from '../hooks/useWebSocket'
import { useEngine } from '../hooks/useEngine'
import { WS_URL } from '../lib/constants'
import { formatCurrency, formatPercent, formatNumber } from '../lib/formatters'

export default function TradeTracker() {
  const navigate = useNavigate()
  const { connected, data } = useWebSocket(WS_URL)
  const { exitTrade, emergencyExit, loading } = useEngine()
  const [showMetrics, setShowMetrics] = useState(false)
  const [exitConfirm, setExitConfirm] = useState(false)

  // Redirect to dashboard if no active trade
  useEffect(() => {
    if (data && !data.active_trade) {
      navigate('/dashboard')
    }
  }, [data?.active_trade, navigate])

  // Handle keyboard shortcut for exit
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'e' && data?.active_trade) {
        setExitConfirm(true)
      }
      if (e.key === 'Escape') {
        setExitConfirm(false)
      }
    }
    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [data?.active_trade])

  if (!data || !data.active_trade) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-12 h-12 text-white animate-pulse mx-auto mb-4" />
          <p className="text-secondary">Loading trade data...</p>
        </div>
      </div>
    )
  }

  const trade = data.active_trade
  const isProfitable = trade.pnl_percent >= 0
  const isTrailingActive = trade.trailing_active

  const handleExit = async () => {
    await exitTrade()
    setExitConfirm(false)
  }

  const handleEmergencyExit = async () => {
    await emergencyExit()
    setExitConfirm(false)
  }

  return (
    <div className="min-h-screen bg-background">
      <TopBar
        spot={data.spot_price}
        spotChange={data.spot_change_pct}
        vix={data.india_vix}
        mode={data.mode}
        executionMode={data.execution_mode}
        broker={data.broker}
        connected={connected}
        status={data.status}
      />

      <main className="container mx-auto px-4 py-6">
        {/* Hero P&L Display */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-6"
        >
          <Card padding="lg" className="text-center">
            <div className="mb-2">
              <Badge variant={trade.trade_type === 'CALL' ? 'call' : 'put'}>
                {trade.instrument}
              </Badge>
            </div>

            <div className={`text-6xl font-bold font-mono tabular-nums mb-2 ${
              isProfitable ? 'text-profit' : 'text-loss'
            }`}>
              <AnimatedNumber
                value={trade.pnl_percent}
                decimals={2}
                suffix="%"
                colorize
              />
            </div>

            <div className={`text-2xl font-mono tabular-nums ${
              isProfitable ? 'text-profit' : 'text-loss'
            }`}>
              <AnimatedNumber
                value={trade.pnl_rupees}
                decimals={0}
                prefix={trade.pnl_rupees >= 0 ? '+₹' : '₹'}
                colorize
              />
            </div>

            <div className="flex items-center justify-center gap-4 mt-4 text-sm text-secondary">
              <div className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                <span>{formatDuration(trade.duration_seconds)}</span>
              </div>
              <div className="flex items-center gap-1">
                {trade.trade_type === 'CALL' ? (
                  <TrendingUp className="w-4 h-4 text-profit" />
                ) : (
                  <TrendingDown className="w-4 h-4 text-loss" />
                )}
                <span>{trade.trade_type}</span>
              </div>
              <div className="flex items-center gap-1">
                <Zap className="w-4 h-4" />
                <span>{trade.signal_path}</span>
              </div>
            </div>
          </Card>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left Column - Price Info */}
          <div className="space-y-4">
            {/* Current Price Card */}
            <Card>
              <CardHeader>
                <CardTitle>Premium</CardTitle>
                <Badge variant={isProfitable ? 'call' : 'put'}>
                  {isProfitable ? 'PROFIT' : 'LOSS'}
                </Badge>
              </CardHeader>

              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-secondary">Entry</span>
                  <span className="font-mono text-primary">
                    ₹{formatNumber(trade.entry_price, 2)}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-secondary">Current (LTP)</span>
                  <span className={`font-mono font-bold ${isProfitable ? 'text-profit' : 'text-loss'}`}>
                    ₹{formatNumber(trade.current_ltp, 2)}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-secondary">Highest</span>
                  <span className="font-mono text-profit">
                    ₹{formatNumber(trade.highest_price, 2)}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-secondary">Lowest</span>
                  <span className="font-mono text-loss">
                    ₹{formatNumber(trade.lowest_price, 2)}
                  </span>
                </div>
              </div>
            </Card>

            {/* Stop Loss Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-white" />
                  Stop Loss
                </CardTitle>
                <Badge variant={isTrailingActive ? 'warning' : 'default'}>
                  {isTrailingActive ? 'TRAILING' : 'INITIAL'}
                </Badge>
              </CardHeader>

              <div className="space-y-3">
                <div className="text-center">
                  <div className="text-3xl font-bold font-mono text-white">
                    ₹{formatNumber(trade.current_stop, 2)}
                  </div>
                  <div className="text-sm text-secondary mt-1">
                    {formatPercent((trade.current_stop - trade.entry_price) / trade.entry_price * 100)} from entry
                  </div>
                </div>

                <ProgressBar
                  value={trade.current_ltp}
                  max={trade.highest_price}
                  min={trade.current_stop}
                  color={trade.current_ltp > trade.current_stop ? 'profit' : 'loss'}
                  showMarkers
                />

                <div className="pt-2 border-t border-border text-sm">
                  <div className="flex justify-between">
                    <span className="text-secondary">VIX Regime</span>
                    <span className="text-primary">{trade.vix_regime}</span>
                  </div>
                  <div className="flex justify-between mt-1">
                    <span className="text-secondary">Trail Distance</span>
                    <span className="text-primary">{formatPercent(trade.trail_distance_pct * 100)}</span>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Middle Column - Chart Placeholder & Session */}
          <div className="lg:col-span-2 space-y-4">
            {/* Premium Chart Placeholder */}
            <Card className="h-64">
              <CardHeader>
                <CardTitle>Premium Chart</CardTitle>
              </CardHeader>
              <div className="flex items-center justify-center h-full text-secondary">
                <div className="text-center">
                  <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Real-time chart coming soon</p>
                </div>
              </div>
            </Card>

            {/* Reversal Warning */}
            {data.reversal_warning && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <Card className="border-white/30 bg-white/5">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-6 h-6 text-white" />
                    <div>
                      <div className="font-medium text-white">Reversal Warning</div>
                      <div className="text-sm text-secondary">
                        {data.reversal_reason || 'Potential trend reversal detected'}
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            )}

            {/* Session Info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card padding="sm">
                <div className="text-xs text-secondary mb-1">MFE</div>
                <div className="font-mono text-lg text-profit">
                  +{formatPercent(trade.mfe_percent)}
                </div>
              </Card>

              <Card padding="sm">
                <div className="text-xs text-secondary mb-1">MAE</div>
                <div className="font-mono text-lg text-loss">
                  {formatPercent(trade.mae_percent)}
                </div>
              </Card>

              <Card padding="sm">
                <div className="text-xs text-secondary mb-1">Qty</div>
                <div className="font-mono text-lg text-primary">
                  {trade.qty}
                </div>
              </Card>

              <Card padding="sm">
                <div className="text-xs text-secondary mb-1">Strike</div>
                <div className="font-mono text-lg text-primary">
                  {trade.strike}
                </div>
              </Card>
            </div>

            {/* Entry Metrics (Collapsible) */}
            <Card>
              <button
                onClick={() => setShowMetrics(!showMetrics)}
                className="w-full flex items-center justify-between"
              >
                <CardTitle>Entry Metrics</CardTitle>
                {showMetrics ? (
                  <ChevronUp className="w-5 h-5 text-secondary" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-secondary" />
                )}
              </button>

              <AnimatePresence>
                {showMetrics && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-border mt-4">
                      <div>
                        <div className="text-xs text-secondary mb-1">Alpha 1</div>
                        <div className="font-mono text-primary">
                          {trade.entry_alpha_1?.toFixed(3) || '-'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-secondary mb-1">Alpha 2</div>
                        <div className="font-mono text-primary">
                          {trade.entry_alpha_2?.toFixed(3) || '-'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-secondary mb-1">PCR</div>
                        <div className="font-mono text-primary">
                          {trade.entry_pcr?.toFixed(3) || '-'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-secondary mb-1">Quality</div>
                        <div className="font-mono text-primary">
                          {trade.entry_quality?.toFixed(1) || '-'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-secondary mb-1">Confidence</div>
                        <div className="font-mono text-primary">
                          {trade.entry_confidence?.toFixed(1) || '-'}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-secondary mb-1">Trend</div>
                        <div className="font-mono text-primary">
                          {trade.entry_trend || '-'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-secondary mb-1">Entry VIX</div>
                        <div className="font-mono text-primary">
                          {trade.entry_vix?.toFixed(2) || '-'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-secondary mb-1">Signal Path</div>
                        <div className="font-mono text-primary">
                          {trade.signal_path || '-'}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </Card>

            {/* Exit Button */}
            <Card>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-secondary mb-1">Manual Exit</div>
                  <div className="text-xs text-muted">Press E to exit trade</div>
                </div>

                <button
                  onClick={() => setExitConfirm(true)}
                  className="btn btn-danger flex items-center gap-2"
                >
                  <DoorOpen className="w-4 h-4" />
                  Exit Trade
                </button>
              </div>
            </Card>
          </div>
        </div>
      </main>

      {/* Exit Confirmation Modal */}
      <AnimatePresence>
        {exitConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
            onClick={() => setExitConfirm(false)}
          >
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
            >
              <Card padding="lg" className="max-w-md">
                <div className="text-center mb-6">
                  <DoorOpen className="w-12 h-12 text-loss mx-auto mb-4" />
                  <h2 className="text-xl font-bold text-primary mb-2">Exit Trade?</h2>
                  <p className="text-secondary">
                    Current P&L: <span className={isProfitable ? 'text-profit' : 'text-loss'}>
                      {formatPercent(trade.pnl_percent)} ({formatCurrency(trade.pnl_rupees)})
                    </span>
                  </p>
                </div>

                <div className="space-y-3">
                  <button
                    onClick={handleExit}
                    disabled={loading}
                    className="btn btn-danger w-full"
                  >
                    Confirm Exit
                  </button>

                  {data.execution_mode === 'LIVE' && (
                    <button
                      onClick={handleEmergencyExit}
                      disabled={loading}
                      className="btn bg-loss/20 text-loss border border-loss/50 hover:bg-loss/30 w-full"
                    >
                      Emergency Market Exit
                    </button>
                  )}

                  <button
                    onClick={() => setExitConfirm(false)}
                    className="btn btn-secondary w-full"
                  >
                    Cancel
                  </button>
                </div>
              </Card>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-background/95 backdrop-blur border-t border-border">
        <div className="container mx-auto px-4 py-2">
          <div className="flex items-center justify-between text-xs text-secondary">
            <span>Press E to exit trade</span>
            <span>
              {data.execution_mode !== 'OFF' ? (
                <span className={data.execution_mode === 'LIVE' ? 'text-loss' : 'text-white'}>
                  {data.execution_mode} MODE
                </span>
              ) : (
                <span>SIGNALS ONLY</span>
              )}
            </span>
            <span>Last update: {new Date(data.timestamp).toLocaleTimeString()}</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins > 0) {
    return `${mins}m ${secs}s`
  }
  return `${secs}s`
}
