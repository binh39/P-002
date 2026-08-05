import { useState } from 'react'
import { IC } from '../components/Icons'

type Page = 'dashboard' | 'experiments' | 'playground' | 'optimization' | 'comparison' | 'review' | 'registry' | 'settings'
interface Props { onNavigate: (p: Page) => void }

const card = { background: '#fff', borderRadius: 14, border: '1px solid #E8EBF5', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' } as const

const inputStyle = {
  width: '100%', padding: '10px 14px', border: '1px solid #E8EBF5',
  borderRadius: 10, fontSize: 13.5, color: '#374151', background: '#FAFBFF',
  outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box' as const,
}

const labelStyle = { display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 6 } as const

export default function CreateExperiment({ onNavigate }: Props) {
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [model, setModel] = useState('gpt-4o')
  const [iterations, setIterations] = useState('5')
  const [temperature, setTemperature] = useState('0.7')
  const [topP, setTopP] = useState('0.9')
  const [maxTokens, setMaxTokens] = useState('2048')
  const [file, setFile] = useState<string | null>(null)
  const [prompt, setPrompt] = useState(`You are an expert Python test engineer. Your goal is to generate comprehensive unit tests for the provided Python source code.

Guidelines:
- Use pytest as the testing framework
- Achieve maximum branch and statement coverage
- Mock external dependencies appropriately
- Include edge cases and boundary conditions
- Use descriptive test names following the pattern: test_<function>_<scenario>

Generate tests that cover all code paths including error handling.`)

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100 }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <button
          onClick={() => onNavigate('dashboard')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6B7280', fontSize: 13, fontFamily: 'inherit', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12, padding: 0 }}
        >
          ← Back to Dashboard
        </button>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#0F1117', margin: 0, letterSpacing: '-0.02em' }}>Create Experiment</h1>
        <p style={{ color: '#9CA3AF', fontSize: 13.5, margin: '4px 0 0' }}>Configure a new prompt optimization experiment</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>
        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Basic info */}
          <div style={{ ...card, padding: '24px' }}>
            <h3 style={{ margin: '0 0 18px', fontSize: 14, fontWeight: 600, color: '#0F1117' }}>Experiment Details</h3>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Experiment Name <span style={{ color: '#EF4444' }}>*</span></label>
              <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. GPT-4o Unit Test Generator v3" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Description</label>
              <textarea
                value={desc} onChange={e => setDesc(e.target.value)}
                placeholder="Describe the goal of this experiment..."
                rows={3}
                style={{ ...inputStyle, resize: 'vertical' as const, lineHeight: 1.5 }}
              />
            </div>
          </div>

          {/* File upload */}
          <div style={{ ...card, padding: '24px' }}>
            <h3 style={{ margin: '0 0 6px', fontSize: 14, fontWeight: 600, color: '#0F1117' }}>Python Project</h3>
            <p style={{ margin: '0 0 16px', fontSize: 13, color: '#9CA3AF' }}>Upload your Python source files for test generation</p>
            {!file ? (
              <label style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                border: '2px dashed #D1D5DB', borderRadius: 12, padding: '32px 24px',
                cursor: 'pointer', background: '#FAFBFF', transition: 'all 0.15s',
              }}>
                <span style={{ color: '#9CA3AF', marginBottom: 8 }}><IC.Upload /></span>
                <span style={{ fontSize: 13.5, fontWeight: 500, color: '#374151' }}>Drop files here or click to browse</span>
                <span style={{ fontSize: 12, color: '#9CA3AF', marginTop: 4 }}>Supports .zip, .tar.gz, or individual .py files (max 50MB)</span>
                <input type="file" style={{ display: 'none' }} onChange={() => setFile('payment_service.zip')} accept=".py,.zip,.tar.gz" />
              </label>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px', background: '#F0FDF4', borderRadius: 10, border: '1px solid #BBF7D0' }}>
                <span style={{ color: '#10B981' }}><IC.Check /></span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 500, color: '#065F46' }}>{file}</div>
                  <div style={{ fontSize: 12, color: '#6EE7B7' }}>24 Python files · 18.4 KB</div>
                </div>
                <button onClick={() => setFile(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6B7280' }}><IC.X /></button>
              </div>
            )}
          </div>

          {/* Prompt editor */}
          <div style={{ ...card, padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#0F1117' }}>System Prompt</h3>
                <p style={{ margin: '3px 0 0', fontSize: 12.5, color: '#9CA3AF' }}>This is the prompt that will be optimized</p>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <span style={{ fontSize: 12, color: '#9CA3AF', background: '#F0F1F5', padding: '3px 8px', borderRadius: 6 }}>
                  {prompt.split(' ').length} words
                </span>
              </div>
            </div>
            <textarea
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              rows={10}
              style={{
                ...inputStyle,
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12.5,
                lineHeight: 1.7,
                resize: 'vertical' as const,
              }}
            />
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Model selector */}
          <div style={{ ...card, padding: '24px' }}>
            <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 600, color: '#0F1117' }}>Model Configuration</h3>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Model</label>
              <select
                value={model} onChange={e => setModel(e.target.value)}
                style={{ ...inputStyle, cursor: 'pointer' }}
              >
                <optgroup label="OpenAI">
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="gpt-4o-mini">GPT-4o Mini</option>
                  <option value="gpt-4-turbo">GPT-4 Turbo</option>
                </optgroup>
                <optgroup label="Anthropic">
                  <option value="claude-sonnet-4-6">Claude Sonnet 4.6</option>
                  <option value="claude-haiku-4-5">Claude Haiku 4.5</option>
                  <option value="claude-opus-4-8">Claude Opus 4.8</option>
                </optgroup>
              </select>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[
                { label: 'Temperature', value: temperature, setter: setTemperature, hint: '0–2' },
                { label: 'Top P', value: topP, setter: setTopP, hint: '0–1' },
                { label: 'Max Tokens', value: maxTokens, setter: setMaxTokens, hint: '512–8192' },
                { label: 'Iterations', value: iterations, setter: setIterations, hint: '1–20' },
              ].map(({ label, value, setter, hint }) => (
                <div key={label}>
                  <label style={labelStyle}>{label}</label>
                  <input
                    value={value} onChange={e => setter(e.target.value)}
                    style={inputStyle} placeholder={hint}
                  />
                  <span style={{ fontSize: 11, color: '#9CA3AF', marginTop: 3, display: 'block' }}>{hint}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Optimization targets */}
          <div style={{ ...card, padding: '24px' }}>
            <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 600, color: '#0F1117' }}>Optimization Targets</h3>
            {[
              { label: 'Branch Coverage', target: '85%', priority: 'High' },
              { label: 'Statement Coverage', target: '90%', priority: 'High' },
              { label: 'Cost per Run', target: '< $0.05', priority: 'Medium' },
              { label: 'Latency', target: '< 3s', priority: 'Low' },
            ].map(({ label, target, priority }) => {
              const c = priority === 'High' ? { bg: '#FEF2F2', color: '#DC2626' } : priority === 'Medium' ? { bg: '#FFFBEB', color: '#D97706' } : { bg: '#F0F1F5', color: '#6B7280' }
              return (
                <div key={label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBlock: 9, borderBottom: '1px solid #F0F1F5' }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: '#374151' }}>{label}</div>
                    <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 2 }}>Target: {target}</div>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 6, background: c.bg, color: c.color }}>{priority}</span>
                </div>
              )
            })}
          </div>

          {/* Submit */}
          <button
            onClick={() => onNavigate('optimization')}
            style={{
              padding: '13px 24px',
              background: 'linear-gradient(135deg, #4F6EF7, #7C3AED)',
              color: '#fff', border: 'none', borderRadius: 12,
              fontSize: 14, fontWeight: 600, cursor: 'pointer',
              fontFamily: 'inherit',
              boxShadow: '0 4px 16px rgba(79,110,247,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            }}
          >
            <IC.Zap /> Launch Experiment
          </button>
          <button
            style={{
              padding: '11px 24px',
              background: '#fff', color: '#6B7280',
              border: '1px solid #E8EBF5', borderRadius: 12,
              fontSize: 13.5, fontWeight: 500, cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            Save as Draft
          </button>
        </div>
      </div>
    </div>
  )
}
