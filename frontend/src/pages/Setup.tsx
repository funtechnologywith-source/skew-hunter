import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Target, Key, DollarSign, Play, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { useEngine } from '../hooks/useEngine'
import { MODES, EXECUTION_MODES, BROKERS } from '../lib/constants'

type Step = 'token' | 'config' | 'execution' | 'broker' | 'confirm' | 'starting'

export default function Setup() {
  const navigate = useNavigate()
  const {
    loading,
    validateToken,
    validateDhan,
    startEngine,
    getConfig,
    checkOrphan
  } = useEngine()

  const [step, setStep] = useState<Step>('token')
  const [token, setToken] = useState('')
  const [userName, setUserName] = useState('')
  const [capital, setCapital] = useState(100000)
  const [mode, setMode] = useState<typeof MODES[number]>('BALANCED')
  const [executionMode, setExecutionMode] = useState<typeof EXECUTION_MODES[number]>('OFF')
  const [broker, setBroker] = useState<typeof BROKERS[number]>('UPSTOX')
  const [dhanToken, setDhanToken] = useState('')
  const [dhanClientId, setDhanClientId] = useState('')
  const [confirmText, setConfirmText] = useState('')
  const [validationError, setValidationError] = useState('')

  const handleValidateToken = async () => {
    if (!token.trim()) {
      setValidationError('Please enter your Upstox access token')
      return
    }

    const result = await validateToken(token)
    if (result.valid) {
      setUserName(result.user_name || 'User')
      setValidationError('')
      setStep('config')
    } else {
      setValidationError(result.message || 'Invalid token')
    }
  }

  const handleConfigNext = async () => {
    setStep('execution')
  }

  const handleExecutionNext = () => {
    if (executionMode === 'OFF') {
      handleStart()
    } else {
      setStep('broker')
    }
  }

  const handleBrokerNext = async () => {
    if (broker === 'DHAN') {
      if (!dhanToken || !dhanClientId) {
        setValidationError('Please enter DHAN credentials')
        return
      }
      const config = await getConfig()
      const result = await validateDhan(dhanToken, dhanClientId, config?.EXPIRY || '')
      if (!result.valid) {
        setValidationError(result.message || 'Invalid DHAN credentials')
        return
      }
    }

    if (executionMode === 'LIVE') {
      setStep('confirm')
    } else {
      handleStart()
    }
  }

  const handleStart = async () => {
    if (executionMode === 'LIVE' && confirmText !== 'CONFIRM') {
      setValidationError('Please type CONFIRM to enable live trading')
      return
    }

    setStep('starting')
    try {
      await startEngine({
        token,
        capital,
        executionMode,
        broker,
        dhanToken: broker === 'DHAN' ? dhanToken : undefined,
        dhanClientId: broker === 'DHAN' ? dhanClientId : undefined
      })

      // Check for orphan before navigating
      const orphan = await checkOrphan()
      if (orphan.has_orphan) {
        // Handle orphan - for now just navigate
      }

      navigate('/dashboard')
    } catch (e) {
      setStep('execution')
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-white/5 border border-white/10 rounded-full">
              <Target className="w-8 h-8 text-white" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight mb-2">Skew Hunter</h1>
          <p className="text-secondary">NIFTY 50 Options Trading System</p>
        </div>

        {/* Steps */}
        <AnimatePresence mode="wait">
          {/* Token Step */}
          {step === 'token' && (
            <motion.div
              key="token"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card padding="lg">
                <CardHeader>
                  <CardTitle>Connect to Upstox</CardTitle>
                  <Key className="w-5 h-5 text-secondary" />
                </CardHeader>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-secondary mb-2">
                      Access Token
                    </label>
                    <input
                      type="password"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      placeholder="Enter your Upstox access token"
                      className="w-full"
                      onKeyDown={(e) => e.key === 'Enter' && handleValidateToken()}
                    />
                  </div>

                  {validationError && (
                    <div className="flex items-center gap-2 text-loss text-sm">
                      <AlertCircle className="w-4 h-4" />
                      {validationError}
                    </div>
                  )}

                  <button
                    onClick={handleValidateToken}
                    disabled={loading}
                    className="btn btn-primary w-full"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <Key className="w-4 h-4 mr-2" />
                    )}
                    Validate Token
                  </button>
                </div>
              </Card>
            </motion.div>
          )}

          {/* Config Step */}
          {step === 'config' && (
            <motion.div
              key="config"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card padding="lg">
                <CardHeader>
                  <CardTitle>Configuration</CardTitle>
                  <DollarSign className="w-5 h-5 text-secondary" />
                </CardHeader>

                <div className="space-y-4">
                  <div className="flex items-center gap-2 p-3 bg-white/5 border border-white/10 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-white" />
                    <span className="text-white">Welcome, {userName}!</span>
                  </div>

                  <div>
                    <label className="block text-sm text-secondary mb-2">
                      Trading Capital (Rs)
                    </label>
                    <input
                      type="number"
                      value={capital}
                      onChange={(e) => setCapital(Number(e.target.value))}
                      min={10000}
                      step={10000}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm text-secondary mb-2">
                      Signal Mode
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {MODES.map(m => (
                        <button
                          key={m}
                          onClick={() => setMode(m)}
                          className={`py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                            mode === m
                              ? 'bg-white text-black'
                              : 'bg-transparent border border-white/10 text-secondary hover:text-white hover:border-white/30'
                          }`}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={handleConfigNext}
                    className="btn btn-primary w-full"
                  >
                    Next
                  </button>
                </div>
              </Card>
            </motion.div>
          )}

          {/* Execution Mode Step */}
          {step === 'execution' && (
            <motion.div
              key="execution"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card padding="lg">
                <CardHeader>
                  <CardTitle>Execution Mode</CardTitle>
                </CardHeader>

                <div className="space-y-4">
                  {EXECUTION_MODES.map(em => (
                    <button
                      key={em}
                      onClick={() => setExecutionMode(em)}
                      className={`w-full p-4 rounded-lg text-left transition-colors ${
                        executionMode === em
                          ? 'bg-white/5 border-2 border-white'
                          : 'bg-transparent border border-white/10 hover:border-white/30'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-primary">{em}</div>
                          <div className="text-sm text-secondary">
                            {em === 'OFF' && 'Signals only, no order tracking'}
                            {em === 'PAPER' && 'Simulated orders (no real money)'}
                            {em === 'LIVE' && 'Real orders via broker API'}
                          </div>
                        </div>
                        <Badge variant={em === 'LIVE' ? 'loss' : em === 'PAPER' ? 'warning' : 'default'}>
                          {em}
                        </Badge>
                      </div>
                    </button>
                  ))}

                  <button
                    onClick={handleExecutionNext}
                    className="btn btn-primary w-full"
                  >
                    {executionMode === 'OFF' ? 'Start Engine' : 'Next'}
                  </button>
                </div>
              </Card>
            </motion.div>
          )}

          {/* Broker Step */}
          {step === 'broker' && (
            <motion.div
              key="broker"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card padding="lg">
                <CardHeader>
                  <CardTitle>Select Broker</CardTitle>
                </CardHeader>

                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-2">
                    {BROKERS.map(b => (
                      <button
                        key={b}
                        onClick={() => setBroker(b)}
                        className={`py-3 px-4 rounded-lg font-medium transition-colors ${
                          broker === b
                            ? 'bg-white text-black'
                            : 'bg-transparent border border-white/10 text-secondary hover:text-white hover:border-white/30'
                        }`}
                      >
                        {b}
                      </button>
                    ))}
                  </div>

                  {broker === 'DHAN' && (
                    <div className="space-y-4 pt-4 border-t border-border">
                      <div>
                        <label className="block text-sm text-secondary mb-2">
                          DHAN Access Token
                        </label>
                        <input
                          type="password"
                          value={dhanToken}
                          onChange={(e) => setDhanToken(e.target.value)}
                          placeholder="Enter DHAN JWT token"
                          className="w-full"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-secondary mb-2">
                          DHAN Client ID
                        </label>
                        <input
                          type="text"
                          value={dhanClientId}
                          onChange={(e) => setDhanClientId(e.target.value)}
                          placeholder="Enter DHAN client ID"
                          className="w-full"
                        />
                      </div>
                    </div>
                  )}

                  {validationError && (
                    <div className="flex items-center gap-2 text-loss text-sm">
                      <AlertCircle className="w-4 h-4" />
                      {validationError}
                    </div>
                  )}

                  <button
                    onClick={handleBrokerNext}
                    disabled={loading}
                    className="btn btn-primary w-full"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : null}
                    {executionMode === 'LIVE' ? 'Next' : 'Start Engine'}
                  </button>
                </div>
              </Card>
            </motion.div>
          )}

          {/* Confirm Step (LIVE only) */}
          {step === 'confirm' && (
            <motion.div
              key="confirm"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card padding="lg">
                <CardHeader>
                  <CardTitle>Confirm Live Trading</CardTitle>
                  <AlertCircle className="w-5 h-5 text-loss" />
                </CardHeader>

                <div className="space-y-4">
                  <div className="p-4 bg-loss/10 border border-loss/20 rounded-lg">
                    <p className="text-sm text-loss">
                      Warning: You are about to enable LIVE trading with real money.
                      Orders will be placed automatically through {broker}.
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm text-secondary mb-2">
                      Type CONFIRM to proceed
                    </label>
                    <input
                      type="text"
                      value={confirmText}
                      onChange={(e) => setConfirmText(e.target.value.toUpperCase())}
                      placeholder="CONFIRM"
                      className="w-full"
                    />
                  </div>

                  {validationError && (
                    <div className="flex items-center gap-2 text-loss text-sm">
                      <AlertCircle className="w-4 h-4" />
                      {validationError}
                    </div>
                  )}

                  <button
                    onClick={handleStart}
                    disabled={loading || confirmText !== 'CONFIRM'}
                    className="btn btn-danger w-full"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <Play className="w-4 h-4 mr-2" />
                    )}
                    Start Live Trading
                  </button>
                </div>
              </Card>
            </motion.div>
          )}

          {/* Starting Step */}
          {step === 'starting' && (
            <motion.div
              key="starting"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card padding="lg">
                <div className="flex flex-col items-center justify-center py-8">
                  <Loader2 className="w-12 h-12 text-white animate-spin mb-4" />
                  <h2 className="text-lg font-medium text-white mb-2">Starting Engine</h2>
                  <p className="text-sm text-secondary">Connecting to market data...</p>
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
