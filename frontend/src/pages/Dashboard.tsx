import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  TrendingUp, TrendingDown, Activity,
  ArrowUpRight, ArrowDownRight,
  Clock
} from 'lucide-react'
import { TopBar } from '../components/layout/TopBar'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { ProgressBar } from '../components/ui/ProgressBar'
import { ConditionRow } from '../components/ui/ConditionRow'
import { AnimatedNumber } from '../components/ui/AnimatedNumber'
import { useWebSocket } from '../hooks/useWebSocket'
import { useEngine } from '../hooks/useEngine'
import { WS_URL, CONFLUENCE_FACTORS } from '../lib/constants'
import { formatCurrency, formatOI, formatNumber } from '../lib/formatters'

export default function Dashboard() {
  const navigate = useNavigate()
  const { connected, data } = useWebSocket(WS_URL)
  const { cycleMode } = useEngine()

  // Redirect to trade page if there's an active trade
  useEffect(() => {
    if (data?.active_trade) {
      navigate('/trade')
    }
  }, [data?.active_trade, navigate])

  // Handle keyboard shortcut for mode cycling
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'm' && !data?.active_trade) {
        cycleMode()
      }
    }
    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [cycleMode, data?.active_trade])

  if (!data) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-12 h-12 text-white animate-pulse mx-auto mb-4" />
          <p className="text-secondary">Connecting to engine...</p>
        </div>
      </div>
    )
  }

  const thresholds = data.thresholds || {}

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
        {/* Market Status */}
        {!data.trading_allowed && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 p-3 bg-white/5 border border-white/10 rounded-lg flex items-center gap-2"
          >
            <Clock className="w-5 h-5 text-white" />
            <span className="text-white text-sm">
              {data.is_lunch_hour ? 'Lunch hour - signals paused' : `Market ${data.market_status} - ${data.next_action}`}
            </span>
          </motion.div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left Column - PCR & OI */}
          <div className="space-y-4">
            {/* PCR Card */}
            <Card>
              <CardHeader>
                <CardTitle>PCR Analysis</CardTitle>
                <Badge variant={data.pcr > 1.05 ? 'call' : data.pcr < 0.95 ? 'put' : 'default'}>
                  {data.pcr_trend}
                </Badge>
              </CardHeader>

              <div className="text-center mb-4">
                <div className="text-4xl font-bold font-mono tabular-nums text-primary">
                  {data.pcr.toFixed(3)}
                </div>
                <div className="text-sm text-secondary mt-1">
                  {data.pcr > 1.05 ? 'Fear (Bullish)' : data.pcr < 0.95 ? 'Greed (Bearish)' : 'Neutral'}
                </div>
              </div>

              <ProgressBar
                value={data.pcr}
                max={2}
                color={data.pcr > 1.05 ? 'profit' : data.pcr < 0.95 ? 'loss' : 'default'}
              />
            </Card>

            {/* OI Flow Card */}
            <Card>
              <CardHeader>
                <CardTitle>OI Flow</CardTitle>
                <Badge variant={data.oi_flow_direction === 'BULLISH' ? 'call' : data.oi_flow_direction === 'BEARISH' ? 'put' : 'default'}>
                  {data.oi_flow_direction}
                </Badge>
              </CardHeader>

              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-secondary">CE OI Change</span>
                  <span className={`font-mono text-sm ${data.ce_oi_change > 0 ? 'text-loss' : 'text-profit'}`}>
                    {formatOI(data.ce_oi_change)}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-secondary">PE OI Change</span>
                  <span className={`font-mono text-sm ${data.pe_oi_change > 0 ? 'text-profit' : 'text-loss'}`}>
                    {formatOI(data.pe_oi_change)}
                  </span>
                </div>

                <div className="pt-2 border-t border-border">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-secondary">Flow Ratio</span>
                    <span className="font-mono text-sm text-primary">
                      {data.oi_flow_ratio > 0 ? '+' : ''}{data.oi_flow_ratio.toFixed(3)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center mt-1">
                    <span className="text-sm text-secondary">Velocity</span>
                    <span className="font-mono text-sm text-primary">
                      {data.oi_velocity.toFixed(1)}
                    </span>
                  </div>
                </div>
              </div>
            </Card>

            {/* Session Stats */}
            <Card>
              <CardHeader>
                <CardTitle>Session Stats</CardTitle>
              </CardHeader>

              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-secondary">Trades Today</span>
                  <span className="font-mono text-primary">
                    {data.trades_today} / {data.max_trades_per_day}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-secondary">Daily P&L</span>
                  <AnimatedNumber
                    value={data.daily_pnl}
                    prefix="₹"
                    colorize
                    className="font-bold"
                  />
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-secondary">Peak MTM</span>
                  <span className="font-mono text-profit">
                    {formatCurrency(data.peak_session_mtm)}
                  </span>
                </div>
              </div>
            </Card>
          </div>

          {/* Middle Column - Signal Conditions */}
          <div className="lg:col-span-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* CALL Conditions */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-profit" />
                    CALL Signal
                  </CardTitle>
                  <Badge variant="call">
                    {data.confluence_call}/6
                  </Badge>
                </CardHeader>

                <div className="space-y-1">
                  <ConditionRow
                    label="Alpha 1"
                    value={data.alpha_1_call}
                    threshold={thresholds.alpha_1_call || 0.75}
                    passed={data.alpha_1_call >= (thresholds.alpha_1_call || 0.75)}
                  />
                  <ConditionRow
                    label="Alpha 2"
                    value={data.alpha_2_call}
                    threshold={thresholds.alpha_2_call || 0.73}
                    passed={data.alpha_2_call >= (thresholds.alpha_2_call || 0.73)}
                  />
                  <ConditionRow
                    label="Quality"
                    value={data.quality_score_call}
                    threshold={thresholds.min_quality_score || 75}
                    passed={data.quality_score_call >= (thresholds.min_quality_score || 75)}
                  />
                  <ConditionRow
                    label="Volume Ratio"
                    value={data.volume_ratio_call}
                    threshold={thresholds.volume_ratio_threshold || 1.8}
                    passed={data.volume_ratio_call >= (thresholds.volume_ratio_threshold || 1.8)}
                  />
                  <ConditionRow
                    label="PCR"
                    value={data.pcr}
                    threshold={1.05}
                    comparison="gt"
                    passed={data.pcr > 1.05}
                  />
                  <ConditionRow
                    label="RSI"
                    value={data.rsi}
                    threshold={75}
                    comparison="lt"
                    passed={data.rsi < 75}
                  />
                </div>

                <div className="mt-3 pt-3 border-t border-border">
                  <div className="flex flex-wrap gap-1">
                    {CONFLUENCE_FACTORS.map(factor => (
                      <Badge
                        key={factor}
                        variant={data.confluence_conditions_call?.includes(factor) ? 'call' : 'default'}
                      >
                        {factor}
                      </Badge>
                    ))}
                  </div>
                </div>
              </Card>

              {/* PUT Conditions */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingDown className="w-4 h-4 text-loss" />
                    PUT Signal
                  </CardTitle>
                  <Badge variant="put">
                    {data.confluence_put}/6
                  </Badge>
                </CardHeader>

                <div className="space-y-1">
                  <ConditionRow
                    label="Alpha 1"
                    value={data.alpha_1_put}
                    threshold={thresholds.alpha_1_put || 0.75}
                    passed={data.alpha_1_put >= (thresholds.alpha_1_put || 0.75)}
                  />
                  <ConditionRow
                    label="Alpha 2"
                    value={data.alpha_2_put}
                    threshold={thresholds.alpha_2_put || 0.73}
                    passed={data.alpha_2_put >= (thresholds.alpha_2_put || 0.73)}
                  />
                  <ConditionRow
                    label="Quality"
                    value={data.quality_score_put}
                    threshold={thresholds.min_quality_score || 75}
                    passed={data.quality_score_put >= (thresholds.min_quality_score || 75)}
                  />
                  <ConditionRow
                    label="Volume Ratio"
                    value={data.volume_ratio_put}
                    threshold={thresholds.volume_ratio_threshold || 1.8}
                    passed={data.volume_ratio_put >= (thresholds.volume_ratio_threshold || 1.8)}
                  />
                  <ConditionRow
                    label="PCR"
                    value={data.pcr}
                    threshold={0.95}
                    comparison="lt"
                    passed={data.pcr < 0.95}
                  />
                  <ConditionRow
                    label="RSI"
                    value={data.rsi}
                    threshold={25}
                    comparison="gt"
                    passed={data.rsi > 25}
                  />
                </div>

                <div className="mt-3 pt-3 border-t border-border">
                  <div className="flex flex-wrap gap-1">
                    {CONFLUENCE_FACTORS.map(factor => (
                      <Badge
                        key={factor}
                        variant={data.confluence_conditions_put?.includes(factor) ? 'put' : 'default'}
                      >
                        {factor}
                      </Badge>
                    ))}
                  </div>
                </div>
              </Card>
            </div>

            {/* Market Info Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              <Card padding="sm">
                <div className="text-xs text-secondary mb-1">ATM Strike</div>
                <div className="font-mono text-lg text-primary">{data.atm_strike}</div>
              </Card>

              <Card padding="sm">
                <div className="text-xs text-secondary mb-1">Trend</div>
                <div className="flex items-center gap-1">
                  {data.trend === 'UPTREND' && <ArrowUpRight className="w-4 h-4 text-profit" />}
                  {data.trend === 'DOWNTREND' && <ArrowDownRight className="w-4 h-4 text-loss" />}
                  <span className="font-medium text-primary">{data.trend}</span>
                </div>
              </Card>

              <Card padding="sm">
                <div className="text-xs text-secondary mb-1">RSI</div>
                <div className={`font-mono text-lg ${
                  data.rsi > 70 ? 'text-loss' : data.rsi < 30 ? 'text-profit' : 'text-primary'
                }`}>
                  {data.rsi.toFixed(1)}
                </div>
              </Card>

              <Card padding="sm">
                <div className="text-xs text-secondary mb-1">ATR %</div>
                <div className="font-mono text-lg text-primary">{data.atr_pct.toFixed(2)}%</div>
              </Card>
            </div>

            {/* Support/Resistance */}
            <Card className="mt-4">
              <CardHeader>
                <CardTitle>Support & Resistance</CardTitle>
              </CardHeader>

              <div className="flex items-center justify-between">
                <div className="text-center">
                  <div className="text-xs text-secondary mb-1">Support</div>
                  <div className="font-mono text-lg text-profit">{data.support}</div>
                </div>

                <div className="flex-1 mx-4">
                  <div className="relative h-2 bg-border rounded-full">
                    <div
                      className="absolute h-4 w-1 bg-primary rounded-full top-1/2 -translate-y-1/2"
                      style={{
                        left: `${((data.spot_price - data.support) / (data.resistance - data.support)) * 100}%`
                      }}
                    />
                  </div>
                  <div className="text-center mt-1">
                    <span className="text-xs text-secondary">Spot: </span>
                    <span className="font-mono text-sm text-primary">{formatNumber(data.spot_price, 0)}</span>
                  </div>
                </div>

                <div className="text-center">
                  <div className="text-xs text-secondary mb-1">Resistance</div>
                  <div className="font-mono text-lg text-loss">{data.resistance}</div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-background/95 backdrop-blur border-t border-border">
        <div className="container mx-auto px-4 py-2">
          <div className="flex items-center justify-between text-xs text-secondary">
            <span>Press M to cycle mode</span>
            <span>
              {data.data_live ? (
                <span className="text-white">LIVE DATA</span>
              ) : (
                <span className="text-secondary">CACHED DATA</span>
              )}
            </span>
            <span>Last update: {new Date(data.timestamp).toLocaleTimeString()}</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
