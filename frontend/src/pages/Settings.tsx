import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Settings as SettingsIcon, Save, RefreshCw,
  Sliders, Shield, Clock, Filter, AlertTriangle
} from 'lucide-react'
import { TopBar } from '../components/layout/TopBar'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { useWebSocket } from '../hooks/useWebSocket'
import { useEngine } from '../hooks/useEngine'
import { WS_URL, MODES } from '../lib/constants'

interface Config {
  ACTIVE_MODE: string
  EXPIRY: string
  MODES: {
    [key: string]: {
      alpha_1_call: number
      alpha_1_put: number
      alpha_2_call: number
      alpha_2_put: number
      min_quality_score: number
      min_confluence: number
      volume_ratio_threshold: number
      oi_change_velocity: number
    }
  }
  RISK: {
    position_size_lots: number
    max_risk_per_trade_pct: number
    daily_loss_limit_pct: number
    max_trades_per_day: number
  }
  EXIT: {
    profit_target_pct: number
    time_exit: string
    mtm_max_loss: number
    mtm_protect_trigger: number
    mtm_protect_pct: number
    min_hold_seconds: number
  }
  FILTERS: {
    min_option_price: number
    max_option_price: number
    min_volume: number
    max_spread_pct: number
    min_trend_strength: number
    min_vix: number
    min_oi_change_writing: number
  }
  TIMING: {
    trading_start: string
    lunch_avoid_start: string
    lunch_avoid_end: string
    eod_squareoff: string
    market_close: string
  }
  REFRESH_INTERVAL_SECONDS: number
}

export default function Settings() {
  const { connected, data } = useWebSocket(WS_URL)
  const { getConfig, updateConfig, loading } = useEngine()
  const [config, setConfig] = useState<Config | null>(null)
  const [activeTab, setActiveTab] = useState<'modes' | 'risk' | 'exit' | 'filters' | 'timing'>('modes')
  const [hasChanges, setHasChanges] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    const result = await getConfig()
    if (result) {
      setConfig(result)
      setHasChanges(false)
    }
  }

  const handleSave = async () => {
    if (!config) return
    const success = await updateConfig(config)
    if (success) {
      setSaveSuccess(true)
      setHasChanges(false)
      setTimeout(() => setSaveSuccess(false), 3000)
    }
  }

  const updateValue = (path: string[], value: any) => {
    if (!config) return
    const newConfig = { ...config }
    let obj: any = newConfig
    for (let i = 0; i < path.length - 1; i++) {
      obj = obj[path[i]]
    }
    obj[path[path.length - 1]] = value
    setConfig(newConfig)
    setHasChanges(true)
  }

  const tabs = [
    { id: 'modes', label: 'Mode Thresholds', icon: Sliders },
    { id: 'risk', label: 'Risk Management', icon: Shield },
    { id: 'exit', label: 'Exit Rules', icon: AlertTriangle },
    { id: 'filters', label: 'Filters', icon: Filter },
    { id: 'timing', label: 'Timing', icon: Clock },
  ] as const

  if (!config) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <SettingsIcon className="w-12 h-12 text-profit animate-pulse mx-auto mb-4" />
          <p className="text-secondary">Loading configuration...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background pb-20">
      <TopBar
        spot={data?.spot_price}
        spotChange={data?.spot_change_pct}
        vix={data?.india_vix}
        mode={data?.mode}
        executionMode={data?.execution_mode}
        broker={data?.broker}
        connected={connected}
        status={data?.status}
      />

      <main className="container mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <SettingsIcon className="w-6 h-6 text-profit" />
            <h1 className="text-xl font-bold text-primary">Settings</h1>
            {hasChanges && (
              <Badge variant="warning">Unsaved Changes</Badge>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={loadConfig}
              disabled={loading}
              className="btn btn-secondary"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Reload
            </button>
            <button
              onClick={handleSave}
              disabled={loading || !hasChanges}
              className="btn btn-primary"
            >
              <Save className="w-4 h-4 mr-2" />
              Save Changes
            </button>
          </div>
        </div>

        {saveSuccess && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 p-3 bg-profit/10 border border-profit/20 rounded-lg text-profit text-sm"
          >
            Configuration saved successfully!
          </motion.div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'bg-profit text-background'
                  : 'bg-card border border-border text-secondary hover:text-primary'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {/* Mode Thresholds */}
          {activeTab === 'modes' && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Active Mode</CardTitle>
                </CardHeader>
                <div className="grid grid-cols-3 gap-2">
                  {MODES.map(mode => (
                    <button
                      key={mode}
                      onClick={() => updateValue(['ACTIVE_MODE'], mode)}
                      className={`py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                        config.ACTIVE_MODE === mode
                          ? 'bg-profit text-background'
                          : 'bg-card border border-border text-secondary hover:text-primary'
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </Card>

              {MODES.map(mode => (
                <Card key={mode}>
                  <CardHeader>
                    <CardTitle>{mode} Mode</CardTitle>
                    {config.ACTIVE_MODE === mode && <Badge variant="call">Active</Badge>}
                  </CardHeader>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <InputField
                      label="Alpha 1 (CALL)"
                      value={config.MODES[mode].alpha_1_call}
                      onChange={(v) => updateValue(['MODES', mode, 'alpha_1_call'], v)}
                      step={0.01}
                    />
                    <InputField
                      label="Alpha 1 (PUT)"
                      value={config.MODES[mode].alpha_1_put}
                      onChange={(v) => updateValue(['MODES', mode, 'alpha_1_put'], v)}
                      step={0.01}
                    />
                    <InputField
                      label="Alpha 2 (CALL)"
                      value={config.MODES[mode].alpha_2_call}
                      onChange={(v) => updateValue(['MODES', mode, 'alpha_2_call'], v)}
                      step={0.01}
                    />
                    <InputField
                      label="Alpha 2 (PUT)"
                      value={config.MODES[mode].alpha_2_put}
                      onChange={(v) => updateValue(['MODES', mode, 'alpha_2_put'], v)}
                      step={0.01}
                    />
                    <InputField
                      label="Min Quality Score"
                      value={config.MODES[mode].min_quality_score}
                      onChange={(v) => updateValue(['MODES', mode, 'min_quality_score'], v)}
                      step={1}
                    />
                    <InputField
                      label="Min Confluence"
                      value={config.MODES[mode].min_confluence}
                      onChange={(v) => updateValue(['MODES', mode, 'min_confluence'], v)}
                      step={1}
                    />
                    <InputField
                      label="Volume Ratio"
                      value={config.MODES[mode].volume_ratio_threshold}
                      onChange={(v) => updateValue(['MODES', mode, 'volume_ratio_threshold'], v)}
                      step={0.1}
                    />
                    <InputField
                      label="OI Velocity"
                      value={config.MODES[mode].oi_change_velocity}
                      onChange={(v) => updateValue(['MODES', mode, 'oi_change_velocity'], v)}
                      step={1}
                    />
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* Risk Management */}
          {activeTab === 'risk' && (
            <Card>
              <CardHeader>
                <CardTitle>Risk Management</CardTitle>
              </CardHeader>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <InputField
                  label="Position Size (Lots)"
                  value={config.RISK.position_size_lots}
                  onChange={(v) => updateValue(['RISK', 'position_size_lots'], v)}
                  step={1}
                />
                <InputField
                  label="Max Risk/Trade %"
                  value={config.RISK.max_risk_per_trade_pct}
                  onChange={(v) => updateValue(['RISK', 'max_risk_per_trade_pct'], v)}
                  step={0.5}
                />
                <InputField
                  label="Daily Loss Limit %"
                  value={config.RISK.daily_loss_limit_pct}
                  onChange={(v) => updateValue(['RISK', 'daily_loss_limit_pct'], v)}
                  step={0.5}
                />
                <InputField
                  label="Max Trades/Day"
                  value={config.RISK.max_trades_per_day}
                  onChange={(v) => updateValue(['RISK', 'max_trades_per_day'], v)}
                  step={1}
                />
              </div>
            </Card>
          )}

          {/* Exit Rules */}
          {activeTab === 'exit' && (
            <Card>
              <CardHeader>
                <CardTitle>Exit Rules</CardTitle>
              </CardHeader>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <InputField
                  label="Profit Target %"
                  value={config.EXIT.profit_target_pct}
                  onChange={(v) => updateValue(['EXIT', 'profit_target_pct'], v)}
                  step={1}
                />
                <InputField
                  label="Time Exit"
                  value={config.EXIT.time_exit}
                  onChange={(v) => updateValue(['EXIT', 'time_exit'], v)}
                  type="text"
                />
                <InputField
                  label="MTM Max Loss (₹)"
                  value={config.EXIT.mtm_max_loss}
                  onChange={(v) => updateValue(['EXIT', 'mtm_max_loss'], v)}
                  step={500}
                />
                <InputField
                  label="MTM Protect Trigger (₹)"
                  value={config.EXIT.mtm_protect_trigger}
                  onChange={(v) => updateValue(['EXIT', 'mtm_protect_trigger'], v)}
                  step={500}
                />
                <InputField
                  label="MTM Protect %"
                  value={config.EXIT.mtm_protect_pct}
                  onChange={(v) => updateValue(['EXIT', 'mtm_protect_pct'], v)}
                  step={0.1}
                />
                <InputField
                  label="Min Hold (seconds)"
                  value={config.EXIT.min_hold_seconds}
                  onChange={(v) => updateValue(['EXIT', 'min_hold_seconds'], v)}
                  step={10}
                />
              </div>
            </Card>
          )}

          {/* Filters */}
          {activeTab === 'filters' && (
            <Card>
              <CardHeader>
                <CardTitle>Signal Filters</CardTitle>
              </CardHeader>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <InputField
                  label="Min Option Price (₹)"
                  value={config.FILTERS.min_option_price}
                  onChange={(v) => updateValue(['FILTERS', 'min_option_price'], v)}
                  step={5}
                />
                <InputField
                  label="Max Option Price (₹)"
                  value={config.FILTERS.max_option_price}
                  onChange={(v) => updateValue(['FILTERS', 'max_option_price'], v)}
                  step={10}
                />
                <InputField
                  label="Min Volume"
                  value={config.FILTERS.min_volume}
                  onChange={(v) => updateValue(['FILTERS', 'min_volume'], v)}
                  step={1000}
                />
                <InputField
                  label="Max Spread %"
                  value={config.FILTERS.max_spread_pct}
                  onChange={(v) => updateValue(['FILTERS', 'max_spread_pct'], v)}
                  step={0.5}
                />
                <InputField
                  label="Min Trend Strength"
                  value={config.FILTERS.min_trend_strength}
                  onChange={(v) => updateValue(['FILTERS', 'min_trend_strength'], v)}
                  step={0.05}
                />
                <InputField
                  label="Min VIX"
                  value={config.FILTERS.min_vix}
                  onChange={(v) => updateValue(['FILTERS', 'min_vix'], v)}
                  step={1}
                />
                <InputField
                  label="Min OI Change (Writing)"
                  value={config.FILTERS.min_oi_change_writing}
                  onChange={(v) => updateValue(['FILTERS', 'min_oi_change_writing'], v)}
                  step={50000}
                />
              </div>
            </Card>
          )}

          {/* Timing */}
          {activeTab === 'timing' && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Trading Hours</CardTitle>
                </CardHeader>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <InputField
                    label="Trading Start"
                    value={config.TIMING.trading_start}
                    onChange={(v) => updateValue(['TIMING', 'trading_start'], v)}
                    type="text"
                  />
                  <InputField
                    label="EOD Squareoff"
                    value={config.TIMING.eod_squareoff}
                    onChange={(v) => updateValue(['TIMING', 'eod_squareoff'], v)}
                    type="text"
                  />
                  <InputField
                    label="Market Close"
                    value={config.TIMING.market_close}
                    onChange={(v) => updateValue(['TIMING', 'market_close'], v)}
                    type="text"
                  />
                </div>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Lunch Hour Avoidance</CardTitle>
                </CardHeader>

                <div className="grid grid-cols-2 gap-4">
                  <InputField
                    label="Lunch Start"
                    value={config.TIMING.lunch_avoid_start}
                    onChange={(v) => updateValue(['TIMING', 'lunch_avoid_start'], v)}
                    type="text"
                  />
                  <InputField
                    label="Lunch End"
                    value={config.TIMING.lunch_avoid_end}
                    onChange={(v) => updateValue(['TIMING', 'lunch_avoid_end'], v)}
                    type="text"
                  />
                </div>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Refresh Rate</CardTitle>
                </CardHeader>

                <InputField
                  label="Refresh Interval (seconds)"
                  value={config.REFRESH_INTERVAL_SECONDS}
                  onChange={(v) => updateValue(['REFRESH_INTERVAL_SECONDS'], v)}
                  step={1}
                />
              </Card>
            </div>
          )}
        </motion.div>
      </main>
    </div>
  )
}

interface InputFieldProps {
  label: string
  value: number | string
  onChange: (value: number | string) => void
  type?: 'number' | 'text'
  step?: number
}

function InputField({ label, value, onChange, type = 'number', step = 1 }: InputFieldProps) {
  return (
    <div>
      <label className="block text-sm text-secondary mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(type === 'number' ? Number(e.target.value) : e.target.value)}
        step={step}
        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-primary font-mono text-sm"
      />
    </div>
  )
}
