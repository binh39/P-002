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
  const [isLoggedIn, setIsLoggedIn] = useState(() => sessionStorage.getItem('promptopt-auth') === 'true')
  const [page, setPage] = useState<Page>('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  if (!isLoggedIn) {
    return <Login onLogin={() => { sessionStorage.setItem('promptopt-auth', 'true'); setIsLoggedIn(true); setPage('dashboard') }} />
  }

  const navigate = (nextPage: Page) => {
    setPage(nextPage)
    setSidebarOpen(false)
  }

  return (
    <div className="app-shell" style={{ display: 'flex', height: '100vh', overflow: 'hidden', fontFamily: 'Inter, system-ui, sans-serif', background: '#F5F7FF' }}>
      {sidebarOpen && <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <Sidebar currentPage={page} onNavigate={navigate} isOpen={sidebarOpen} />
      <div className="app-main" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        <TopNav onMenu={() => setSidebarOpen(true)} />
        <main className="main-scroll" style={{ flex: 1, overflowY: 'auto' }}>
          {page === 'dashboard' && <Dashboard onNavigate={navigate} />}
          {page === 'experiments' && <CreateExperiment onNavigate={navigate} />}
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
