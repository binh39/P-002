import { useState } from 'react'
import Sidebar from './components/Sidebar'
import TopNav from './components/TopNav'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import CreateExperiment from './pages/CreateExperiment'
import Playground from './pages/Playground'
import OptimizationProgress from './pages/OptimizationProgress'
import Comparison from './pages/Comparison'
import ReviewApproval from './pages/ReviewApproval'
import Registry from './pages/Registry'
import Settings from './pages/Settings'

type Page = 'dashboard' | 'experiments' | 'playground' | 'optimization' | 'comparison' | 'review' | 'registry' | 'settings'

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [page, setPage] = useState<Page>('dashboard')

  if (!isLoggedIn) {
    return <Login onLogin={() => { setIsLoggedIn(true); setPage('dashboard') }} />
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', fontFamily: 'Inter, system-ui, sans-serif', background: '#F5F7FF' }}>
      <Sidebar currentPage={page} onNavigate={setPage} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        <TopNav />
        <main style={{ flex: 1, overflowY: 'auto' }}>
          {page === 'dashboard' && <Dashboard onNavigate={setPage} />}
          {page === 'experiments' && <CreateExperiment onNavigate={setPage} />}
          {page === 'playground' && <Playground />}
          {page === 'optimization' && <OptimizationProgress />}
          {page === 'comparison' && <Comparison />}
          {page === 'review' && <ReviewApproval />}
          {page === 'registry' && <Registry />}
          {page === 'settings' && <Settings />}
        </main>
      </div>
    </div>
  )
}
