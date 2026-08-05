import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { IC } from '../components/Icons'

type Page = 'dashboard' | 'experiments' | 'playground' | 'optimization' | 'comparison' | 'review' | 'registry' | 'settings'
interface Props { onNavigate: (p: Page) => void }

const coverageData = [
  { day: 'Jul 28', branch: 62, statement: 71 },
  { day: 'Jul 29', branch: 65, statement: 74 },
  { day: 'Jul 30', branch: 68, statement: 76 },
  { day: 'Jul 31', branch: 72, statement: 79 },
  { day: 'Aug 1', branch: 75, statement: 82 },
  { day: 'Aug 2', branch: 81, statement: 87 },
  { day: 'Aug 3', branch: 84, statement: 91 },
  { day: 'Aug 4', branch: 87, statement: 93 },
]

const kpis = [
  { label: 'Total Experiments', value: '47', delta: '+8 this month', deltaPositive: true, icon: IC.Flask, color: '#4F6EF7', bg: '#EEF2FF' },
  { label: 'Running', value: '3', delta: '2 queued', deltaPositive: null, icon: IC.Play, color: '#F59E0B', bg: '#FFFBEB' },
  { label: 'Branch Coverage', value: '87.3%', delta: '+4.2% vs last week', deltaPositive: true, icon: IC.BarChart, color: '#10B981', bg: '#F0FDF4' },
  { label: 'Statement Coverage', value: '93.1%', delta: '+2.8% vs last week', deltaPositive: true, icon: IC.Code, color: '#8B5CF6', bg: '#F5F3FF' },
]

const experiments = [
  { id: 'EXP-047', name: 'GPT-4o Unit Test Generator v3', model: 'gpt-4o', branch: '87.3%', statement: '93.1%', status: 'completed', updated: '2h ago' },
  { id: 'EXP-046', name: 'Claude Haiku Coverage Optimizer', model: 'claude-haiku-4-5', branch: '81.5%', statement: '88.4%', status: 'running', updated: '45m ago' },
  { id: 'EXP-045', name: 'Payment Service Test Suite', model: 'gpt-4o-mini', branch: '74.2%', statement: '82.7%', status: 'running', updated: '1h ago' },
  { id: 'EXP-044', name: 'Auth Module Regression Tests', model: 'claude-sonnet-4-6', branch: '69.8%', statement: '79.3%', status: 'pending', updated: '3h ago' },
  { id: 'EXP-043', name: 'Database Layer Coverage Run', model: 'gpt-4o', branch: '91.2%', statement: '95.6%', status: 'completed', updated: '6h ago' },
  { id: 'EXP-042', name: 'API Gateway Integration Tests', model: 'gpt-4o-mini', branch: '55.4%', statement: '63.2%', status: 'failed', updated: '8h ago' },
]

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; color: string; dot: string }> = {
    completed: { bg: '#F0FDF4', color: '#059669', dot: '#10B981' },
    running: { bg: '#EFF6FF', color: '#2563EB', dot: '#3B82F6' },
    pending: { bg: '#FFFBEB', color: '#D97706', dot: '#F59E0B' },
    failed: { bg: '#FEF2F2', color: '#DC2626', dot: '#EF4444' },
  }
  const s = styles[status] || styles.pending
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: s.bg, color: s.color,
      padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 500,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.dot, display: 'inline-block' }} />
      {status}
    </span>
  )
}

function CoverageBar({ value }: { value: string }) {
  const num = parseFloat(value)
  const color = num >= 80 ? '#10B981' : num >= 65 ? '#F59E0B' : '#EF4444'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: '#F0F1F5', borderRadius: 2, maxWidth: 60 }}>
        <div style={{ width: `${num}%`, height: '100%', background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 13, fontWeight: 500, color: '#374151' }}>{value}</span>
    </div>
  )
}

const card = {
  background: '#fff', borderRadius: 14, border: '1px solid #E8EBF5',
  boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
} as const

export default function Dashboard({ onNavigate }: Props) {
  return (
    <div style={{ padding: '28px 32px', maxWidth: 1280 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0F1117', margin: 0, letterSpacing: '-0.02em' }}>Dashboard</h1>
          <p style={{ color: '#9CA3AF', fontSize: 13.5, margin: '4px 0 0' }}>Monday, August 4, 2026 — payment-service project</p>
        </div>
        <button
          onClick={() => onNavigate('experiments')}
          style={{
            display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px',
            background: 'linear-gradient(135deg, #4F6EF7, #7C3AED)', color: '#fff',
            border: 'none', borderRadius: 10, fontSize: 13.5, fontWeight: 600,
            cursor: 'pointer', fontFamily: 'inherit',
            boxShadow: '0 4px 12px rgba(79,110,247,0.25)',
          }}
        >
          <IC.Plus /> New Experiment
        </button>
      </div>

      {/* KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        {kpis.map(({ label, value, delta, deltaPositive, icon: Icon, color, bg }) => (
          <div key={label} style={{ ...card, padding: '20px 22px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
              <span style={{ fontSize: 13, color: '#6B7280', fontWeight: 500 }}>{label}</span>
              <div style={{ width: 34, height: 34, borderRadius: 9, background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', color }}>
                <Icon />
              </div>
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#0F1117', letterSpacing: '-0.03em', lineHeight: 1 }}>{value}</div>
            <div style={{ marginTop: 8, fontSize: 12, color: deltaPositive === true ? '#10B981' : deltaPositive === false ? '#EF4444' : '#9CA3AF', fontWeight: 500 }}>
              {deltaPositive === true ? '↑ ' : deltaPositive === false ? '↓ ' : ''}{delta}
            </div>
          </div>
        ))}
      </div>

      {/* Chart + activity grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 16, marginBottom: 24 }}>
        {/* Coverage chart */}
        <div style={{ ...card, padding: '22px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#0F1117' }}>Coverage Trend</h3>
              <p style={{ margin: '3px 0 0', fontSize: 12.5, color: '#9CA3AF' }}>Last 8 days</p>
            </div>
            <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#6B7280' }}>
                <span style={{ width: 10, height: 3, background: '#4F6EF7', borderRadius: 2, display: 'inline-block' }} />Branch
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#6B7280' }}>
                <span style={{ width: 10, height: 3, background: '#8B5CF6', borderRadius: 2, display: 'inline-block' }} />Statement
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={coverageData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="gradBlue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4F6EF7" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#4F6EF7" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradPurple" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F0F1F5" vertical={false} />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} domain={[50, 100]} />
              <Tooltip
                contentStyle={{ border: '1px solid #E8EBF5', borderRadius: 8, fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}
                formatter={(v) => [`${v}%`]}
              />
              <Area type="monotone" dataKey="branch" stroke="#4F6EF7" strokeWidth={2} fill="url(#gradBlue)" />
              <Area type="monotone" dataKey="statement" stroke="#8B5CF6" strokeWidth={2} fill="url(#gradPurple)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Quick stats */}
        <div style={{ ...card, padding: '22px 24px' }}>
          <h3 style={{ margin: '0 0 18px', fontSize: 15, fontWeight: 600, color: '#0F1117' }}>Quick Stats</h3>
          {[
            { label: 'Avg. optimization time', value: '4.2 min', icon: '⏱' },
            { label: 'Avg. token cost per run', value: '$0.043', icon: '💰' },
            { label: 'Best coverage gain', value: '+18.4%', icon: '📈' },
            { label: 'Prompts approved', value: '31 / 47', icon: '✅' },
            { label: 'Models in use', value: '4 models', icon: '🤖' },
            { label: 'P95 latency', value: '1.84s', icon: '⚡' },
          ].map(({ label, value, icon }) => (
            <div key={label} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              paddingBlock: 10, borderBottom: '1px solid #F0F1F5',
            }}>
              <span style={{ fontSize: 13, color: '#6B7280' }}>{icon} {label}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#0F1117' }}>{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent experiments */}
      <div style={{ ...card, overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 24px', borderBottom: '1px solid #F0F1F5' }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#0F1117' }}>Recent Experiments</h3>
          <button
            onClick={() => onNavigate('registry')}
            style={{
              fontSize: 12.5, color: '#4F6EF7', background: 'none', border: 'none',
              cursor: 'pointer', fontFamily: 'inherit', fontWeight: 500,
              display: 'flex', alignItems: 'center', gap: 4,
            }}
          >View all <IC.ArrowRight /></button>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#FAFBFF' }}>
              {['ID', 'Name', 'Model', 'Branch Cov.', 'Stmt Cov.', 'Status', 'Updated'].map(h => (
                <th key={h} style={{ padding: '10px 20px', textAlign: 'left', fontSize: 11.5, fontWeight: 600, color: '#9CA3AF', letterSpacing: '0.04em', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {experiments.map((exp, i) => (
              <tr key={exp.id} style={{ borderTop: '1px solid #F0F1F5', background: i % 2 === 0 ? '#fff' : '#FAFBFF' }}>
                <td style={{ padding: '13px 20px', fontSize: 12.5, color: '#6B7280', fontFamily: 'JetBrains Mono, monospace', fontWeight: 500 }}>{exp.id}</td>
                <td style={{ padding: '13px 20px', fontSize: 13.5, color: '#0F1117', fontWeight: 500 }}>{exp.name}</td>
                <td style={{ padding: '13px 20px' }}>
                  <span style={{ fontSize: 12, background: '#F0F1F5', color: '#6B7280', padding: '3px 8px', borderRadius: 6, fontFamily: 'JetBrains Mono, monospace' }}>{exp.model}</span>
                </td>
                <td style={{ padding: '13px 20px' }}><CoverageBar value={exp.branch} /></td>
                <td style={{ padding: '13px 20px' }}><CoverageBar value={exp.statement} /></td>
                <td style={{ padding: '13px 20px' }}><StatusBadge status={exp.status} /></td>
                <td style={{ padding: '13px 20px', fontSize: 12.5, color: '#9CA3AF' }}>{exp.updated}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
