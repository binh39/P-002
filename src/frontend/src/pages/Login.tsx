import { useState } from 'react'
import { IC } from '../components/Icons'

interface Props { onLogin: () => void }

export default function Login({ onLogin }: Props) {
  const [email, setEmail] = useState('alex.morgan@company.com')
  const [password, setPassword] = useState('••••••••••')
  const [loading, setLoading] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setTimeout(() => { setLoading(false); onLogin() }, 900)
  }

  return (
    <div style={{
      minHeight: '100vh', background: '#F5F7FF',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'Inter, system-ui, sans-serif',
    }}>
      {/* Background decoration */}
      <div style={{ position: 'fixed', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
        <div style={{
          position: 'absolute', top: -200, right: -200, width: 600, height: 600,
          background: 'radial-gradient(circle, rgba(124,58,237,0.08) 0%, transparent 70%)',
          borderRadius: '50%',
        }} />
        <div style={{
          position: 'absolute', bottom: -200, left: -100, width: 500, height: 500,
          background: 'radial-gradient(circle, rgba(79,110,247,0.08) 0%, transparent 70%)',
          borderRadius: '50%',
        }} />
      </div>

      <div style={{ position: 'relative', width: '100%', maxWidth: 420, padding: '0 24px' }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
            <div style={{
              width: 52, height: 52, borderRadius: 14,
              background: 'linear-gradient(135deg, #4F6EF7, #7C3AED)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 8px 24px rgba(79,110,247,0.3)',
              color: '#fff',
            }}>
              <IC.Zap />
            </div>
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: '#0F1117', margin: 0, letterSpacing: '-0.02em' }}>PromptOpt</h1>
          <p style={{ color: '#6B7280', fontSize: 14, marginTop: 6 }}>AI Prompt Optimization Platform</p>
        </div>

        {/* Card */}
        <div style={{
          background: '#fff', borderRadius: 16,
          border: '1px solid #E8EBF5',
          boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
          padding: 32,
        }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: '#0F1117', margin: '0 0 6px' }}>Sign in to your workspace</h2>
          <p style={{ color: '#9CA3AF', fontSize: 13.5, margin: '0 0 28px' }}>Welcome back, Alex.</p>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 6 }}>Email address</label>
              <input
                value={email}
                onChange={e => setEmail(e.target.value)}
                type="email"
                style={{
                  width: '100%', padding: '10px 14px', border: '1px solid #E8EBF5',
                  borderRadius: 10, fontSize: 14, color: '#374151', background: '#F8F9FC',
                  outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box',
                }}
              />
            </div>
            <div style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: '#374151' }}>Password</label>
                <button type="button" onClick={() => window.alert('A password reset link has been sent to your email.')} style={{ padding: 0, border: 0, background: 'none', fontSize: 12.5, color: '#4F6EF7', cursor: 'pointer' }}>Forgot password?</button>
              </div>
              <input
                value={password}
                onChange={e => setPassword(e.target.value)}
                type="password"
                style={{
                  width: '100%', padding: '10px 14px', border: '1px solid #E8EBF5',
                  borderRadius: 10, fontSize: 14, color: '#374151', background: '#F8F9FC',
                  outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box',
                }}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%', padding: '11px 20px',
                background: loading ? '#9BA8F5' : 'linear-gradient(135deg, #4F6EF7, #7C3AED)',
                color: '#fff', border: 'none', borderRadius: 10, fontSize: 14,
                fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
                fontFamily: 'inherit', boxShadow: '0 4px 12px rgba(79,110,247,0.3)',
                transition: 'all 0.2s',
              }}
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <div style={{ marginTop: 20, display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ flex: 1, height: 1, background: '#E8EBF5' }} />
            <span style={{ fontSize: 12, color: '#9CA3AF' }}>or continue with</span>
            <div style={{ flex: 1, height: 1, background: '#E8EBF5' }} />
          </div>

          <button type="button" onClick={onLogin} style={{
            width: '100%', marginTop: 16, padding: '10px 20px',
            background: '#fff', border: '1px solid #E8EBF5', borderRadius: 10,
            fontSize: 13.5, fontWeight: 500, color: '#374151', cursor: 'pointer',
            fontFamily: 'inherit', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
            Sign in with Google
          </button>
        </div>

        <p style={{ textAlign: 'center', fontSize: 12, color: '#9CA3AF', marginTop: 20 }}>
          By signing in, you agree to the Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  )
}
