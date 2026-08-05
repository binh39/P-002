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
- Add clear docstrings explaining the test purpose

Generate tests that systematically cover:
1. Happy path scenarios with valid inputs
2. Error handling paths (exceptions, failed states)
3. Edge cases and boundary conditions
4. Integration points with mocked dependencies`

type DiffToken = { text: string; type: 'same' | 'add' | 'remove' }

function diffLines(original: string, optimized: string) {
  const origLines = original.split('\n')
  const optLines = optimized.split('\n')
  const result: { line: string; type: 'same' | 'add' | 'remove' }[] = []

  const origSet = new Set(origLines.map(l => l.trim()))
  for (const line of optLines) {
    if (origSet.has(line.trim()) && line.trim() !== '') {
      result.push({ line, type: 'same' })
    } else if (line.trim() === '') {
      result.push({ line, type: 'same' })
    } else {
      result.push({ line, type: 'add' })
    }
  }
  return result
}

const metrics = [
  { label: 'Branch Coverage', original: '62.1%', optimized: '87.3%', delta: '+25.2%', positive: true },
  { label: 'Statement Coverage', original: '70.3%', optimized: '93.1%', delta: '+22.8%', positive: true },
  { label: 'Test Count', original: '2', optimized: '9', delta: '+7', positive: true },
  { label: 'Avg Token Cost', original: '$0.052', optimized: '$0.043', delta: '-17.3%', positive: true },
  { label: 'P95 Latency', original: '2.30s', optimized: '1.84s', delta: '-20.0%', positive: true },
  { label: 'Prompt Tokens', original: '67', optimized: '189', delta: '+122', positive: null },
]

export default function Comparison() {
  const diffResult = diffLines(ORIGINAL, OPTIMIZED)

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0F1117', margin: 0, letterSpacing: '-0.02em' }}>Prompt Comparison</h1>
          <p style={{ color: '#9CA3AF', fontSize: 13, margin: '4px 0 0' }}>EXP-047 · Original vs. Generation 5 Candidate A</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
            background: '#fff', border: '1px solid #E8EBF5', borderRadius: 8,
            fontSize: 13, fontWeight: 500, color: '#6B7280', cursor: 'pointer', fontFamily: 'inherit',
          }}><IC.ExternalLink /> Share</button>
        </div>
      </div>

      {/* Side-by-side prompts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
        {/* Original */}
        <div style={{ ...card, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #F0F1F5', background: '#FEF2F2', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#EF4444', display: 'inline-block' }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: '#991B1B' }}>Original Prompt</span>
            </div>
            <span style={{ fontSize: 11, color: '#9CA3AF', background: '#FFF', padding: '2px 7px', borderRadius: 5 }}>{ORIGINAL.split(' ').length} words</span>
          </div>
          <pre style={{ margin: 0, padding: '18px 20px', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, lineHeight: 1.7, color: '#374151', whiteSpace: 'pre-wrap' }}>
            {ORIGINAL}
          </pre>
        </div>

        {/* Optimized */}
        <div style={{ ...card, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #F0F1F5', background: '#F0FDF4', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: '#065F46' }}>Optimized Prompt</span>
            </div>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#059669', background: '#DCFCE7', padding: '2px 7px', borderRadius: 5, fontWeight: 600 }}>
              <IC.Award /> Best Candidate
            </span>
          </div>
          <pre style={{ margin: 0, padding: '18px 20px', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, lineHeight: 1.7, color: '#374151', whiteSpace: 'pre-wrap' }}>
            {OPTIMIZED}
          </pre>
        </div>
      </div>

      {/* Metrics comparison table */}
      <div style={{ ...card, overflow: 'hidden', marginBottom: 20 }}>
        <div style={{ padding: '16px 22px', borderBottom: '1px solid #F0F1F5' }}>
          <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#0F1117' }}>Performance Comparison</h3>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#FAFBFF' }}>
              {['Metric', 'Original', 'Optimized', 'Delta'].map(h => (
                <th key={h} style={{ padding: '10px 22px', textAlign: 'left', fontSize: 11.5, fontWeight: 600, color: '#9CA3AF', letterSpacing: '0.04em', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.map(({ label, original, optimized, delta, positive }, i) => (
              <tr key={label} style={{ borderTop: '1px solid #F0F1F5', background: i % 2 === 0 ? '#fff' : '#FAFBFF' }}>
                <td style={{ padding: '13px 22px', fontSize: 13.5, fontWeight: 500, color: '#374151' }}>{label}</td>
                <td style={{ padding: '13px 22px', fontSize: 13.5, color: '#9CA3AF', fontFamily: 'JetBrains Mono, monospace' }}>{original}</td>
                <td style={{ padding: '13px 22px', fontSize: 13.5, fontWeight: 600, color: '#0F1117', fontFamily: 'JetBrains Mono, monospace' }}>{optimized}</td>
                <td style={{ padding: '13px 22px' }}>
                  <span style={{
                    fontSize: 12.5, fontWeight: 600, padding: '3px 10px', borderRadius: 20,
                    background: positive === true ? '#F0FDF4' : positive === false ? '#FEF2F2' : '#F0F1F5',
                    color: positive === true ? '#059669' : positive === false ? '#DC2626' : '#6B7280',
                  }}>{delta}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Diff view */}
      <div style={{ ...card, overflow: 'hidden' }}>
        <div style={{ padding: '16px 22px', borderBottom: '1px solid #F0F1F5', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#0F1117' }}>Prompt Diff</h3>
          <div style={{ display: 'flex', gap: 12, fontSize: 12 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#6B7280' }}>
              <span style={{ display: 'inline-block', width: 10, height: 10, background: '#DCFCE7', border: '1px solid #BBF7D0', borderRadius: 2 }} /> Added
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#6B7280' }}>
              <span style={{ display: 'inline-block', width: 10, height: 10, background: '#FEE2E2', border: '1px solid #FECACA', borderRadius: 2 }} /> Removed
            </span>
          </div>
        </div>
        <div style={{ padding: '16px 0', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, lineHeight: 1.8 }}>
          {diffResult.map((item, i) => (
            <div key={i} style={{
              paddingInline: 22,
              background: item.type === 'add' ? '#F0FDF4' : 'transparent',
              borderLeft: item.type === 'add' ? '3px solid #10B981' : '3px solid transparent',
              display: 'flex', gap: 16, alignItems: 'flex-start',
            }}>
              <span style={{
                color: item.type === 'add' ? '#10B981' : '#D1D5DB',
                width: 14, flexShrink: 0, userSelect: 'none', fontSize: 13,
              }}>
                {item.type === 'add' ? '+' : ' '}
              </span>
              <span style={{ color: item.type === 'add' ? '#065F46' : '#374151', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {item.line || ' '}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
