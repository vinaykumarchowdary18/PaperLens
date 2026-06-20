import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getAnalysis } from '../lib/api'
import Navbar from '../components/Navbar'

function ScoreRing({ score, label, color }) {
  const r = 50, cx = 60, cy = 60
  const circ = 2 * Math.PI * r
  const pct = Math.min(100, Math.max(0, score || 0))
  const dash = (pct / 100) * circ

  return (
    <div className="score-ring-wrap">
      <div className="score-ring" style={{ width: 120, height: 120 }}>
        <svg width="120" height="120" viewBox="0 0 120 120">
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--bg3)" strokeWidth="10" />
          <circle
            cx={cx} cy={cy} r={r} fill="none"
            stroke={color} strokeWidth="10"
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 0.8s ease' }}
          />
        </svg>
        <div className="score-ring-label">
          <span className="score-ring-pct" style={{ color }}>{pct}%</span>
          <span className="score-ring-name">{label}</span>
        </div>
      </div>
    </div>
  )
}

function AgentRow({ name, score, type }) {
  const color = score > 70 ? 'var(--red)' : score > 40 ? 'var(--amber)' : 'var(--green)'
  return (
    <div className="agent-row">
      <span className="agent-name">{name}</span>
      <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 99, marginRight: 8, flexShrink: 0, background: type === 'api' ? 'var(--accent-glow)' : 'var(--green-bg)', color: type === 'api' ? 'var(--accent)' : 'var(--green)' }}>
        {type === 'api' ? 'API' : 'Local'}
      </span>
      <div className="agent-bar-wrap">
        <div className="agent-bar" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="agent-pct text-mono" style={{ color }}>{score}%</span>
    </div>
  )
}

export default function Results() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const pollRef = useRef()

  const load = () =>
    getAnalysis(id)
      .then((d) => {
        setData(d)
        if (d.status === 'processing') {
          pollRef.current = setTimeout(load, 3000)
        }
      })
      .catch(() => setError('Could not load results.'))
      .finally(() => setLoading(false))

  useEffect(() => {
    load()
    return () => clearTimeout(pollRef.current)
  }, [id])

  const ai = data?.result?.ai
  const plag = data?.result?.plagiarism

  const aiColor = (ai?.ai_score || 0) > 70 ? 'var(--red)' : (ai?.ai_score || 0) > 40 ? 'var(--amber)' : 'var(--green)'
  const plagColor = (plag?.plag_score || 0) > 20 ? 'var(--amber)' : 'var(--green)'

  return (
    <>
      <Navbar />
      <div className="page">
        {/* Back */}
        <Link to="/dashboard" className="btn btn-ghost btn-sm" style={{ marginBottom: 24, paddingLeft: 0 }}>
          ← Back to Dashboard
        </Link>

        {loading && (
          <div style={{ textAlign: 'center', padding: 80 }}>
            <div className="spinner" style={{ margin: '0 auto 16px' }} />
            <p className="text-muted">Loading results…</p>
          </div>
        )}

        {error && (
          <div style={{ padding: '14px 18px', background: 'var(--red-bg)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 'var(--radius-sm)', color: 'var(--red)' }}>
            {error}
          </div>
        )}

        {data?.status === 'processing' && (
          <div style={{ textAlign: 'center', padding: 80 }}>
            <div className="spinner" style={{ margin: '0 auto 16px' }} />
            <h3 style={{ marginBottom: 8 }}>Agents are running…</h3>
            <p className="text-muted text-sm">This takes 10–30 seconds. Page updates automatically.</p>
          </div>
        )}

        {data?.status === 'error' && (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
            <h3 style={{ marginBottom: 8 }}>Analysis failed</h3>
            <p className="text-muted text-sm">The document could not be processed. Try a different file format.</p>
          </div>
        )}

        {data?.status === 'done' && ai && plag && (
          <>
            {/* Title */}
            <div className="mb-6">
              <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4, wordBreak: 'break-all' }}>{data.filename}</h1>
              <p className="text-muted text-sm">
                {data.word_count?.toLocaleString()} words · Analysed {new Date(data.created_at).toLocaleString()}
              </p>
            </div>

            {/* Score rings */}
            <div className="card mb-4" style={{ display: 'flex', justifyContent: 'center', gap: 60, flexWrap: 'wrap', padding: '40px 24px' }}>
              <ScoreRing score={ai.ai_score} label="AI Content" color={aiColor} />
              <ScoreRing score={plag.plag_score} label="Plagiarism" color={plagColor} />
            </div>

            {/* Summary banners */}
            <div className="grid-2 mb-4">
              <div style={{ background: ai.ai_score > 70 ? 'var(--red-bg)' : ai.ai_score > 40 ? 'var(--amber-bg)' : 'var(--green-bg)', border: `1px solid ${ai.ai_score > 70 ? 'rgba(248,113,113,0.3)' : ai.ai_score > 40 ? 'rgba(251,191,36,0.3)' : 'rgba(52,211,153,0.3)'}`, borderRadius: 'var(--radius)', padding: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 4, color: aiColor }}>AI Detection</div>
                <div style={{ fontSize: 14, color: 'var(--text)', lineHeight: 1.5 }}>
                  {ai.ai_score > 70 ? 'High AI probability. Review this document carefully before submission.' : ai.ai_score > 40 ? 'Mixed signal. Some sections may be AI-generated.' : 'Mostly human-written. Low AI probability detected.'}
                </div>
                {ai.confidence && <div style={{ fontSize: 12, color: 'var(--text2)', marginTop: 6 }}>Confidence: {ai.confidence}%</div>}
              </div>
              <div style={{ background: plag.plag_score > 20 ? 'var(--amber-bg)' : 'var(--green-bg)', border: `1px solid ${plag.plag_score > 20 ? 'rgba(251,191,36,0.3)' : 'rgba(52,211,153,0.3)'}`, borderRadius: 'var(--radius)', padding: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 4, color: plagColor }}>Plagiarism Check</div>
                <div style={{ fontSize: 14, color: 'var(--text)', lineHeight: 1.5 }}>
                  {plag.plag_score > 20 ? 'Possible similarity found. Review matched sources below.' : 'No significant plagiarism detected across 240M+ academic papers.'}
                </div>
                {plag.sources_checked && <div style={{ fontSize: 12, color: 'var(--text2)', marginTop: 6 }}>{plag.sources_checked} sources searched</div>}
              </div>
            </div>

            {/* AI agent breakdown */}
            {ai.agents && ai.agents.length > 0 && (
              <div className="card mb-4">
                <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>AI Detection — Agent breakdown</h2>
                {ai.agents.map((a) => (
                  <AgentRow key={a.name} name={a.name} score={Math.round(a.score * 100)} type={a.type || 'api'} />
                ))}
                {ai.disagreement && (
                  <div style={{ marginTop: 16, padding: '10px 14px', background: 'var(--amber-bg)', borderRadius: 'var(--radius-sm)', fontSize: 13, color: 'var(--amber)' }}>
                    ⚠️ API agents and local agents disagree significantly. Treat score with caution.
                  </div>
                )}
              </div>
            )}

            {/* Plagiarism sources */}
            {plag.matches && plag.matches.length > 0 && (
              <div className="card mb-4">
                <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>Matching sources</h2>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Source</th>
                        <th>Database</th>
                        <th>Similarity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {plag.matches.map((m, i) => (
                        <tr key={i}>
                          <td>
                            {m.url
                              ? <a href={m.url} target="_blank" rel="noopener noreferrer">{m.title || m.url}</a>
                              : (m.title || '—')}
                          </td>
                          <td className="text-xs">{m.source || '—'}</td>
                          <td><span className="text-mono" style={{ color: 'var(--amber)' }}>{Math.round((m.similarity || 0) * 100)}%</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <Link to="/dashboard" className="btn btn-secondary">Analyse another paper</Link>
              <Link to="/credits" className="btn btn-ghost">Buy credits</Link>
            </div>
          </>
        )}
      </div>
    </>
  )
}
