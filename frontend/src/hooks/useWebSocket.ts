import { useEffect, useRef, useState, useCallback } from 'react'

interface WebSocketState {
  connected: boolean
  data: any
  error: string | null
}

export function useWebSocket(url: string) {
  const [state, setState] = useState<WebSocketState>({
    connected: false,
    data: null,
    error: null
  })
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url)

      ws.onopen = () => {
        setState(prev => ({ ...prev, connected: true, error: null }))
        console.log('WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type !== 'ping' && data.type !== 'pong') {
            setState(prev => ({ ...prev, data }))
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onclose = () => {
        setState(prev => ({ ...prev, connected: false }))
        console.log('WebSocket disconnected')

        // Fast reconnect - 500ms for low latency
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Reconnecting...')
          connect()
        }, 500)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setState(prev => ({ ...prev, error: 'Connection error' }))
      }

      wsRef.current = ws
    } catch (error) {
      setState(prev => ({ ...prev, error: 'Failed to connect' }))
    }
  }, [url])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const send = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return {
    ...state,
    send,
    reconnect: connect,
    disconnect
  }
}
