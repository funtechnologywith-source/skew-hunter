// Auto-detect WebSocket URL based on environment
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const wsHost = window.location.host // includes port if non-standard
export const WS_URL = `${wsProtocol}//${wsHost}/ws/live`

export const MODES = ['STRICT', 'BALANCED', 'RELAXED'] as const
export type Mode = typeof MODES[number]

export const EXECUTION_MODES = ['OFF', 'PAPER', 'LIVE'] as const
export type ExecutionMode = typeof EXECUTION_MODES[number]

export const BROKERS = ['UPSTOX', 'DHAN'] as const
export type Broker = typeof BROKERS[number]

export const VIX_REGIMES = ['low', 'normal', 'elevated', 'high', 'extreme'] as const
export type VixRegime = typeof VIX_REGIMES[number]

export const EXIT_REASONS = {
  profit_target: 'Target Hit',
  trailing_stop: 'Trailing Stop',
  initial_stop: 'Stop Loss',
  time_exit: 'Time Exit',
  mtm_max_loss: 'MTM Max Loss',
  mtm_profit_protection: 'Profit Protection',
  manual_exit: 'Manual Exit',
  emergency_stop: 'Emergency Stop'
} as const

export const CONFLUENCE_FACTORS = [
  'Alpha1',
  'Alpha2',
  'PCR',
  'Volume',
  'Trend',
  'OI_Vel',
  'OI_Flow'
] as const
