import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Calendar, Filter,
  ChevronLeft, ChevronRight, Download, BarChart3
} from 'lucide-react'
import { TopBar } from '../components/layout/TopBar'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { useWebSocket } from '../hooks/useWebSocket'
import { useEngine } from '../hooks/useEngine'
import { WS_URL } from '../lib/constants'
import { formatCurrency } from '../lib/formatters'

interface Trade {
  trade_id: number
  date: string
  entry_time: string
  exit_time: string
  duration_mins: number
  instrument: string
  trade_type: 'CALL' | 'PUT'
  strike: number
  entry_price: number
  exit_price: number
  qty: number
  pnl_rupees: number
  pnl_percent: number
  peak_profit_pct: number
  mae_pct: number
  exit_reason: string
  signal_confidence: number
  quality_score: number
  signal_path: string
}

export default function History() {
  const { connected, data } = useWebSocket(WS_URL)
  const { getTrades, loading } = useEngine()
  const [trades, setTrades] = useState<Trade[]>([])
  const [filter, setFilter] = useState<'all' | 'wins' | 'losses'>('all')
  const [dateFilter, setDateFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const pageSize = 10

  useEffect(() => {
    loadTrades()
  }, [])

  const loadTrades = async () => {
    const result = await getTrades()
    if (result) {
      setTrades(result)
    }
  }

  // Filter trades
  const filteredTrades = trades.filter(trade => {
    if (filter === 'wins' && trade.pnl_rupees <= 0) return false
    if (filter === 'losses' && trade.pnl_rupees > 0) return false
    if (dateFilter && trade.date !== dateFilter) return false
    return true
  })

  // Paginate
  const totalPages = Math.ceil(filteredTrades.length / pageSize)
  const paginatedTrades = filteredTrades.slice((page - 1) * pageSize, page * pageSize)

  // Calculate stats
  const stats = {
    totalTrades: filteredTrades.length,
    wins: filteredTrades.filter(t => t.pnl_rupees > 0).length,
    losses: filteredTrades.filter(t => t.pnl_rupees <= 0).length,
    totalPnl: filteredTrades.reduce((sum, t) => sum + t.pnl_rupees, 0),
    winRate: filteredTrades.length > 0
      ? (filteredTrades.filter(t => t.pnl_rupees > 0).length / filteredTrades.length * 100)
      : 0,
    avgWin: filteredTrades.filter(t => t.pnl_rupees > 0).length > 0
      ? filteredTrades.filter(t => t.pnl_rupees > 0).reduce((sum, t) => sum + t.pnl_rupees, 0) / filteredTrades.filter(t => t.pnl_rupees > 0).length
      : 0,
    avgLoss: filteredTrades.filter(t => t.pnl_rupees <= 0).length > 0
      ? filteredTrades.filter(t => t.pnl_rupees <= 0).reduce((sum, t) => sum + t.pnl_rupees, 0) / filteredTrades.filter(t => t.pnl_rupees <= 0).length
      : 0,
    profitFactor: (() => {
      const grossProfit = filteredTrades.filter(t => t.pnl_rupees > 0).reduce((sum, t) => sum + t.pnl_rupees, 0)
      const grossLoss = Math.abs(filteredTrades.filter(t => t.pnl_rupees <= 0).reduce((sum, t) => sum + t.pnl_rupees, 0))
      return grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0
    })()
  }

  // Get unique dates for filter
  const uniqueDates = [...new Set(trades.map(t => t.date))].sort().reverse()

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
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card padding="sm">
            <div className="text-xs text-secondary mb-1">Total P&L</div>
            <div className={`text-2xl font-bold font-mono ${stats.totalPnl >= 0 ? 'text-profit' : 'text-loss'}`}>
              {formatCurrency(stats.totalPnl)}
            </div>
          </Card>

          <Card padding="sm">
            <div className="text-xs text-secondary mb-1">Win Rate</div>
            <div className={`text-2xl font-bold font-mono ${stats.winRate >= 50 ? 'text-profit' : 'text-loss'}`}>
              {stats.winRate.toFixed(1)}%
            </div>
          </Card>

          <Card padding="sm">
            <div className="text-xs text-secondary mb-1">W/L</div>
            <div className="text-2xl font-bold font-mono text-primary">
              <span className="text-profit">{stats.wins}</span>
              <span className="text-secondary">/</span>
              <span className="text-loss">{stats.losses}</span>
            </div>
          </Card>

          <Card padding="sm">
            <div className="text-xs text-secondary mb-1">Profit Factor</div>
            <div className={`text-2xl font-bold font-mono ${stats.profitFactor >= 1 ? 'text-profit' : 'text-loss'}`}>
              {stats.profitFactor === Infinity ? '∞' : stats.profitFactor.toFixed(2)}
            </div>
          </Card>
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-secondary" />
              <span className="text-sm text-secondary">Filter:</span>
            </div>

            <div className="flex gap-2">
              {(['all', 'wins', 'losses'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => { setFilter(f); setPage(1); }}
                  className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                    filter === f
                      ? f === 'wins' ? 'bg-profit text-black'
                        : f === 'losses' ? 'bg-loss text-black'
                        : 'bg-white text-black'
                      : 'bg-transparent border border-white/10 text-secondary hover:text-white hover:border-white/30'
                  }`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-secondary" />
              <select
                value={dateFilter}
                onChange={(e) => { setDateFilter(e.target.value); setPage(1); }}
                className="bg-card border border-border rounded-lg px-3 py-1 text-sm text-primary"
              >
                <option value="">All Dates</option>
                {uniqueDates.map(date => (
                  <option key={date} value={date}>{date}</option>
                ))}
              </select>
            </div>

            <button
              onClick={loadTrades}
              disabled={loading}
              className="ml-auto btn btn-secondary text-sm"
            >
              <Download className="w-4 h-4 mr-1" />
              Refresh
            </button>
          </div>
        </Card>

        {/* Trade Table */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Trade History
            </CardTitle>
            <span className="text-sm text-secondary">
              {filteredTrades.length} trades
            </span>
          </CardHeader>

          {paginatedTrades.length === 0 ? (
            <div className="text-center py-12 text-secondary">
              <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No trades found</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-2 text-xs text-secondary font-medium">Date</th>
                      <th className="text-left py-3 px-2 text-xs text-secondary font-medium">Time</th>
                      <th className="text-left py-3 px-2 text-xs text-secondary font-medium">Type</th>
                      <th className="text-left py-3 px-2 text-xs text-secondary font-medium">Strike</th>
                      <th className="text-right py-3 px-2 text-xs text-secondary font-medium">Entry</th>
                      <th className="text-right py-3 px-2 text-xs text-secondary font-medium">Exit</th>
                      <th className="text-right py-3 px-2 text-xs text-secondary font-medium">P&L %</th>
                      <th className="text-right py-3 px-2 text-xs text-secondary font-medium">P&L ₹</th>
                      <th className="text-left py-3 px-2 text-xs text-secondary font-medium">Exit Reason</th>
                      <th className="text-left py-3 px-2 text-xs text-secondary font-medium">Path</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedTrades.map((trade, index) => (
                      <motion.tr
                        key={trade.trade_id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="border-b border-border/50 hover:bg-card/50 transition-colors"
                      >
                        <td className="py-3 px-2 text-sm text-primary font-mono">
                          {trade.date}
                        </td>
                        <td className="py-3 px-2 text-sm text-secondary font-mono">
                          {trade.entry_time.split(' ')[1]?.substring(0, 5) || trade.entry_time}
                        </td>
                        <td className="py-3 px-2">
                          <Badge variant={trade.trade_type === 'CALL' ? 'call' : 'put'}>
                            {trade.trade_type}
                          </Badge>
                        </td>
                        <td className="py-3 px-2 text-sm font-mono text-primary">
                          {trade.strike}
                        </td>
                        <td className="py-3 px-2 text-sm font-mono text-right text-secondary">
                          ₹{trade.entry_price.toFixed(2)}
                        </td>
                        <td className="py-3 px-2 text-sm font-mono text-right text-secondary">
                          ₹{trade.exit_price.toFixed(2)}
                        </td>
                        <td className={`py-3 px-2 text-sm font-mono text-right font-medium ${
                          trade.pnl_percent >= 0 ? 'text-profit' : 'text-loss'
                        }`}>
                          {trade.pnl_percent >= 0 ? '+' : ''}{trade.pnl_percent.toFixed(2)}%
                        </td>
                        <td className={`py-3 px-2 text-sm font-mono text-right font-medium ${
                          trade.pnl_rupees >= 0 ? 'text-profit' : 'text-loss'
                        }`}>
                          {trade.pnl_rupees >= 0 ? '+' : ''}₹{trade.pnl_rupees.toFixed(0)}
                        </td>
                        <td className="py-3 px-2 text-sm">
                          <Badge variant={
                            trade.exit_reason === 'profit_target' ? 'call' :
                            trade.exit_reason === 'trailing_stop' ? 'warning' :
                            trade.exit_reason === 'stop_loss' || trade.exit_reason === 'mtm_max_loss' ? 'put' :
                            'default'
                          }>
                            {trade.exit_reason.replace(/_/g, ' ')}
                          </Badge>
                        </td>
                        <td className="py-3 px-2 text-sm text-secondary">
                          {trade.signal_path}
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
                  <span className="text-sm text-secondary">
                    Page {page} of {totalPages}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="btn btn-secondary text-sm"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="btn btn-secondary text-sm"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
      </main>
    </div>
  )
}
