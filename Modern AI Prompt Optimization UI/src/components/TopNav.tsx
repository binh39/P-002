import { IC } from './Icons'

export default function TopNav() {
  return (
    <header style={{
      height: 56, background: '#fff', borderBottom: '1px solid #E8EBF5',
      display: 'flex', alignItems: 'center', paddingInline: 24, gap: 16,
      position: 'sticky', top: 0, zIndex: 10,
    }}>
      {/* Search */}
      <div style={{
        flex: 1, maxWidth: 400, position: 'relative',
      }}>
        <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#9CA3AF' }}>
          <IC.Search />
        </span>
        <input
          placeholder="Search experiments, prompts..."
          style={{
            width: '100%', paddingLeft: 36, paddingRight: 16, paddingBlock: 7,
            border: '1px solid #E8EBF5', borderRadius: 8, fontSize: 13,
            background: '#F8F9FC', color: '#374151', outline: 'none',
            fontFamily: 'inherit',
          }}
        />
        <span style={{
          position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
          background: '#F0F1F5', borderRadius: 4, padding: '1px 5px', fontSize: 10,
          color: '#9CA3AF', fontWeight: 500, pointerEvents: 'none',
        }}>⌘K</span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Environment badge */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px',
        background: '#F0FDF4', borderRadius: 20, border: '1px solid #BBF7D0',
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
        <span style={{ fontSize: 12, color: '#059669', fontWeight: 500 }}>production</span>
      </div>

      {/* Notifications */}
      <button style={{
        position: 'relative', width: 36, height: 36, borderRadius: 8,
        border: '1px solid #E8EBF5', background: '#fff', display: 'flex',
        alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: '#6B7280',
      }}>
        <IC.Bell />
        <span style={{
          position: 'absolute', top: 6, right: 6, width: 7, height: 7,
          background: '#EF4444', borderRadius: '50%', border: '1.5px solid #fff',
        }} />
      </button>

      {/* Avatar */}
      <div style={{
        width: 32, height: 32, borderRadius: 8, cursor: 'pointer',
        background: 'linear-gradient(135deg, #4F6EF7, #7C3AED)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#fff', fontSize: 13, fontWeight: 600,
      }}>A</div>
    </header>
  )
}
