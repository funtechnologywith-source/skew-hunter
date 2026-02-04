import { Routes, Route, Navigate } from 'react-router-dom'
import Setup from './pages/Setup'
import Dashboard from './pages/Dashboard'
import TradeTracker from './pages/TradeTracker'
import History from './pages/History'
import Settings from './pages/Settings'

function App() {
  return (
    <div className="min-h-screen bg-background">
      <Routes>
        <Route path="/" element={<Navigate to="/setup" replace />} />
        <Route path="/setup" element={<Setup />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/trade" element={<TradeTracker />} />
        <Route path="/history" element={<History />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </div>
  )
}

export default App
