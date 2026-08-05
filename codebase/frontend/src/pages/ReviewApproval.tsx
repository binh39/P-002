import { useState } from 'react'
import { IC } from '../components/Icons'

const card = { background: '#fff', borderRadius: 14, border: '1px solid #E8EBF5', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' } as const

const ORIGINAL = `You are a Python test engineer. Generate unit tests for the provided Python source code.

Use pytest as the testing framework. Make sure to cover the main functionality.

Generate comprehensive tests that validate the code behavior.`

const OPTIMIZED = `You are an expert Python test engineer specializing in high-coverage test generation. Your goal is to generate comprehensive unit tests for the provided Python source code.

Guidelines:
- Use pytest as the testing framework with fixtures and parametrize decorators
- Achieve maximum branch and statement coverage by testing all conditional paths
- Mock external dependencies appropriately using unittest.mock.patch and MagicMock
- Include edge cases and boundary conditions (zero, negative, empty, None values)
- Use descriptive test names following: test_<function>_<scenario>_<expected_outcome>
- Group related tests into classes when testing the same component

Generate tests that systematically cover all code paths including error handling.`

const reviews = [
  { id: 'EXP-047', name: 'GPT-4o Unit Test Generator v3', model: 'gpt-4o', status: 'pending', branch: '87.3%', statement: '93.1%', submittedBy: 'Auto-optimizer', time: '2h ago' },
  { id: 'EXP-045', name: 'Payment Service Test Suite', model: 'gpt-4o-mini', status: 'pending', branch: '74.2%', statement: '82.7%', submittedBy: 'Auto-optimizer', time: '3h ago' },
  { id: 'EXP-043', name: 'Auth Module Tests', model: 'claude-sonnet-4-6', status: 'pending', branch: '69.8%', statement: '79.3%', submittedBy: 'Auto-optimizer', time: '5h ago' },
]

export default function ReviewApproval() {
  const [selected, setSelected] = useState(reviews[0])
  const [decision, setDecision] = useState<'approved' | 'rejected' | null>(null)
  const [comment, setComment] = useState('')

  const handleDecision = (d: 'approved' | 'rejected') => setDecision(d)

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0F1117', margin: 0, letterSpacing: '-0.02em' }}>Review & Approval</h1>
        <p style={{ color: '#9CA3AF', fontSize: 13, margin: '4px 0 0' }}>3 prompts awaiting review</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20 }}>
        {/* Queue */}
        <div style={{ ...card, overflow: 'hidden', alignSelf: 'start' }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid #F0F1F5' }}>
            <h3 style={{ margin: 0, fontSize: 13.5, fontWeight: 600, color: '#0F1117' }}>Review Queue</h3>
          </div>
          {reviews.map(r => (
            <button
              key={r.id}
              onClick={() => { setSelected(r); setDecision(null); setComment('') }}
              style={{
                width: '100%', padding: '14px 18px', borderBottom: '1px solid #F0F1F5',
                background: selected.id === r.id ? 'linear-gradient(90deg, rgba(79,110,247,0.06), transparent)' : '#fff',
                border: 'none', borderLeft: selected.id === r.id ? '3px solid #4F6EF7' : '3px solid transparent',
                cursor: 'pointer', textAlign: 'left', fontFamily: 'inherit',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: '#9CA3AF' }}>{r.id}</span>
                <span style={{ fontSize: 11, background: '#FFFBEB', color: '#D97706', padding: '2px 7px', borderRadius: 10, fontWeight: 500 }}>Pending</span>
              </div>
              <div style={{ fontSize: 13, fontWeight: 500, color: '#0F1117', marginTop: 4, lineHeight: 1.3 }}>{r.name}</div>
              <div style={{ fontSize: 11.5, color: '#9CA3AF', marginTop: 4 }}>{r.time} · {r.branch} branch</div>
            </button>
          ))}
        </div>

        {/* Detail */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Experiment header */}
          <div style={{ ...card, padding: '20px 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                  <span style={{ fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: '#9CA3AF' }}>{selected.id}</span>
                  <span style={{ fontSize: 11.5, background: '#EEF2FF', color: '#4F6EF7', padding: '2px 7px', borderRadius: 5, fontFamily: 'JetBrains Mono, monospace' }}>{selected.model}</span>
                </div>
                <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#0F1117' }}>{selected.name}</h2>
                <p style={{ margin: '4px 0 0', fontSize: 13, color: '#9CA3AF' }}>Submitted by {selected.submittedBy} · {selected.time}</p>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                {[
                  { label: 'Branch', value: selected.branch, color: '#4F6EF7' },
                  { label: 'Stmt', value: selected.statement, color: '#8B5CF6' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ textAlign: 'center', padding: '8px 16px', background: '#F8F9FC', borderRadius: 10, border: '1px solid #E8EBF5' }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color }}>{value}</div>
                    <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 2 }}>{label} Cov.</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Before/After prompts */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <div style={{ ...card, overflow: 'hidden' }}>
              <div style={{ padding: '12px 18px', borderBottom: '1px solid #F0F1F5', background: '#FEF2F2' }}>
                <span style={{ fontSize: 12.5, fontWeight: 600, color: '#991B1B', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#EF4444', display: 'inline-block' }} />Before (Original)
                </span>
              </div>
              <pre style={{ margin: 0, padding: '16px 18px', fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5, lineHeight: 1.7, color: '#374151', whiteSpace: 'pre-wrap' }}>
                {ORIGINAL}
              </pre>
            </div>
            <div style={{ ...card, overflow: 'hidden' }}>
              <div style={{ padding: '12px 18px', borderBottom: '1px solid #F0F1F5', background: '#F0FDF4' }}>
                <span style={{ fontSize: 12.5, fontWeight: 600, color: '#065F46', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />After (Optimized)
                </span>
              </div>
              <pre style={{ margin: 0, padding: '16px 18px', fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5, lineHeight: 1.7, color: '#374151', whiteSpace: 'pre-wrap' }}>
                {OPTIMIZED}
              </pre>
            </div>
          </div>

          {/* Metrics row */}
          <div style={{ ...card, padding: '18px 22px' }}>
            <h4 style={{ margin: '0 0 14px', fontSize: 13, fontWeight: 600, color: '#0F1117' }}>Improvement Summary</h4>
            <div style={{ display: 'flex', gap: 12 }}>
              {[
                { label: 'Branch Coverage', from: '62.1%', to: '87.3%', gain: '+25.2%' },
                { label: 'Stmt Coverage', from: '70.3%', to: '93.1%', gain: '+22.8%' },
                { label: 'Test Count', from: '2', to: '9', gain: '+7 tests' },
                { label: 'Cost per Run', from: '$0.052', to: '$0.043', gain: '-17.3%' },
              ].map(({ label, from, to, gain }) => (
                <div key={label} style={{ flex: 1, background: '#F8F9FC', borderRadius: 10, padding: '12px 14px', border: '1px solid #E8EBF5' }}>
                  <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 6 }}>{label}</div>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                    <span style={{ fontSize: 13, color: '#9CA3AF', textDecoration: 'line-through', fontFamily: 'JetBrains Mono, monospace' }}>{from}</span>
                    <span style={{ fontSize: 15, fontWeight: 700, color: '#0F1117', fontFamily: 'JetBrains Mono, monospace' }}>{to}</span>
                  </div>
                  <div style={{ fontSize: 11.5, color: '#10B981', fontWeight: 600, marginTop: 4 }}>{gain}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Comment + actions */}
          {!decision ? (
            <div style={{ ...card, padding: '20px 24px' }}>
              <h4 style={{ margin: '0 0 12px', fontSize: 13, fontWeight: 600, color: '#0F1117' }}>Review Comment (optional)</h4>
              <textarea
                value={comment}
                onChange={e => setComment(e.target.value)}
                placeholder="Add notes for the team..."
                rows={3}
                style={{
                  width: '100%', padding: '10px 14px', border: '1px solid #E8EBF5',
                  borderRadius: 10, fontSize: 13.5, color: '#374151', background: '#FAFBFF',
                  outline: 'none', fontFamily: 'inherit', resize: 'vertical' as const,
                  marginBottom: 16, boxSizing: 'border-box' as const,
                }}
              />
              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  onClick={() => handleDecision('approved')}
                  style={{
                    flex: 1, padding: '11px 0',
                    background: 'linear-gradient(135deg, #10B981, #059669)',
                    color: '#fff', border: 'none', borderRadius: 10,
                    fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
                    boxShadow: '0 4px 12px rgba(16,185,129,0.25)',
                  }}
                >
                  <IC.Check /> Approve Prompt
                </button>
                <button
                  onClick={() => handleDecision('rejected')}
                  style={{
                    flex: 1, padding: '11px 0',
                    background: '#fff', color: '#DC2626',
                    border: '1px solid #FECACA', borderRadius: 10,
                    fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
                  }}
                >
                  <IC.X /> Reject
                </button>
                <button
                  style={{
                    padding: '11px 18px',
                    background: '#fff', color: '#6B7280',
                    border: '1px solid #E8EBF5', borderRadius: 10,
                    fontSize: 13.5, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                    display: 'flex', alignItems: 'center', gap: 6,
                  }}
                >
                  <IC.RefreshCw /> Re-run
                </button>
              </div>
            </div>
          ) : (
            <div style={{
              ...card, padding: '24px',
              background: decision === 'approved' ? '#F0FDF4' : '#FEF2F2',
              border: `1px solid ${decision === 'approved' ? '#BBF7D0' : '#FECACA'}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{
                  width: 40, height: 40, borderRadius: '50%',
                  background: decision === 'approved' ? '#10B981' : '#EF4444',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff',
                }}>
                  {decision === 'approved' ? <IC.Check /> : <IC.X />}
                </div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: decision === 'approved' ? '#065F46' : '#991B1B' }}>
                    Prompt {decision === 'approved' ? 'Approved' : 'Rejected'}
                  </div>
                  <div style={{ fontSize: 13, color: decision === 'approved' ? '#059669' : '#DC2626', marginTop: 2 }}>
                    {decision === 'approved' ? 'Prompt will be registered to the Prompt Registry.' : 'Experiment will be marked for revision.'}
                  </div>
                </div>
                <button
                  onClick={() => setDecision(null)}
                  style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#6B7280', fontSize: 12, fontFamily: 'inherit' }}
                >
                  Undo
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
