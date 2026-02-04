import { useState, useCallback } from 'react'

const API_BASE = '/api'

interface EngineConfig {
  token: string
  capital: number
  executionMode: 'OFF' | 'PAPER' | 'LIVE'
  broker: 'UPSTOX' | 'DHAN'
  dhanToken?: string
  dhanClientId?: string
}

export function useEngine() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const validateToken = useCallback(async (token: string) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/validate-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      })
      const data = await response.json()
      return data
    } catch (e) {
      setError('Failed to validate token')
      return { valid: false, message: 'Network error' }
    } finally {
      setLoading(false)
    }
  }, [])

  const validateDhan = useCallback(async (accessToken: string, clientId: string, expiry: string) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/validate-dhan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: accessToken, client_id: clientId, expiry })
      })
      return await response.json()
    } catch (e) {
      setError('Failed to validate DHAN credentials')
      return { valid: false, message: 'Network error' }
    } finally {
      setLoading(false)
    }
  }, [])

  const startEngine = useCallback(async (config: EngineConfig) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/engine/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: config.token,
          capital: config.capital,
          execution_mode: config.executionMode,
          broker: config.broker,
          dhan_token: config.dhanToken,
          dhan_client_id: config.dhanClientId
        })
      })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to start engine')
      }
      return await response.json()
    } catch (e: any) {
      setError(e.message)
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const stopEngine = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/engine/stop`, {
        method: 'POST'
      })
      return await response.json()
    } catch (e) {
      setError('Failed to stop engine')
    } finally {
      setLoading(false)
    }
  }, [])

  const requestExit = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/trade/exit`, {
        method: 'POST'
      })
      return await response.json()
    } catch (e) {
      setError('Failed to request exit')
    }
  }, [])

  const emergencyExit = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/trade/emergency-exit`, {
        method: 'POST'
      })
      return await response.json()
    } catch (e) {
      setError('Failed to execute emergency exit')
    }
  }, [])

  const cycleMode = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/mode/cycle`, {
        method: 'POST'
      })
      return await response.json()
    } catch (e) {
      setError('Failed to cycle mode')
    }
  }, [])

  const setMode = useCallback(async (mode: string) => {
    try {
      const response = await fetch(`${API_BASE}/mode/set`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
      })
      return await response.json()
    } catch (e) {
      setError('Failed to set mode')
    }
  }, [])

  const getConfig = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/config`)
      return await response.json()
    } catch (e) {
      setError('Failed to get config')
    }
  }, [])

  const updateConfig = useCallback(async (config: any) => {
    try {
      const response = await fetch(`${API_BASE}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config })
      })
      return await response.json()
    } catch (e) {
      setError('Failed to update config')
    }
  }, [])

  const checkOrphan = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/orphan`)
      return await response.json()
    } catch (e) {
      return { has_orphan: false }
    }
  }, [])

  const handleOrphan = useCallback(async (action: 'RECOVER' | 'EXIT' | 'IGNORE', tradeData?: any) => {
    try {
      const response = await fetch(`${API_BASE}/orphan/recover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, trade_data: tradeData })
      })
      return await response.json()
    } catch (e) {
      setError('Failed to handle orphan')
    }
  }, [])

  const exitTrade = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/trade/exit`, {
        method: 'POST'
      })
      return await response.json()
    } catch (e) {
      setError('Failed to exit trade')
    } finally {
      setLoading(false)
    }
  }, [])

  const getTrades = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/trades`)
      return await response.json()
    } catch (e) {
      setError('Failed to fetch trades')
      return []
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    loading,
    error,
    validateToken,
    validateDhan,
    startEngine,
    stopEngine,
    requestExit,
    exitTrade,
    emergencyExit,
    cycleMode,
    setMode,
    getConfig,
    updateConfig,
    checkOrphan,
    handleOrphan,
    getTrades
  }
}
