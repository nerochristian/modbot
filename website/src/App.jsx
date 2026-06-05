import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import GuildDashboard from './pages/GuildDashboard'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/dashboard/:guildId/*" element={<GuildDashboard />} />
    </Routes>
  )
}
