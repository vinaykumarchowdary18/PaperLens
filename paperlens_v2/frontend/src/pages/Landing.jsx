import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Landing() {
  const { user } = useAuth()

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      {/* ── Nav ── */}
      <nav>
        <div className="nav-inner">
          <span className="nav-logo">🔬 Paper<span>Lens</span></span>
          <div className="nav-right">
            {user
              ? <Link to="/dashboard" className="btn btn-primary btn-sm">Go to Dashboard</Link>
              : <Link to="/login" className="btn btn-primary btn-sm">Get started free</Link>
            }
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section style={{ maxWidth: 780, margin: '0 auto', padding: '100px 24px 80px', textAlign: 'center' }}>
        <div style={{
          display: 'inline-block', fontSize: 12, fontWeight: 500,
          background: 'var(--accent-glow)', color: 'var(--accent)',
          border: '1px solid rgba(124,108,252,0.3)',
          padding: '4px 14px', borderRadius: 99, marginBottom: 28,
          letterSpacing: '.06em', textTransform: 'uppercase'
        }}>
          7-Agent Ensemble Detection
        </div>

        <h1 style={{ fontSize: 'clamp(36px, 6vw, 64px)', fontWeight: 800, lineHeight: 1.1, marginBottom: 24, letterSpacing: '-1px' }}>
          Know exactly what's{' '}
          <span style={{ color: 'var(--accent)' }}>AI-generated</span>{' '}
          in your paper
        </h1>

        <p style={{ fontSize: 18, color: 'var(--text2)', maxWidth: 560, margin: '0 auto 40px', lineHeight: 1.7 }}>
          Upload your PDF, DOCX, or TXT. PaperLens runs 7 detection agents in parallel
          and returns AI probability, plagiarism score, and a source-by-source breakdown.
          Results in under 30 seconds.
        </p>

        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link to={user ? '/dashboard' : '/login'} className="btn btn-primary btn-lg">
            Analyse your paper — first one free
          </Link>
          <a href="#how" className="btn btn-secondary btn-lg">See how it works</a>
        </div>

        <p style={{ fontSize: 13, color: 'var(--text3)', marginTop: 16 }}>
          No TOEFL or subscription required to start · 1 free analysis on signup
        </p>
      </section>

      {/* ── Stats ── */}
      <section style={{ background: 'var(--bg2)', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', padding: '40px 24px' }}>
        <div style={{ maxWidth: 820, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 32, textAlign: 'center' }}>
          {[
            { n: '7', label: 'Detection agents' },
            { n: '6', label: 'Plagiarism sources' },
            { n: '240M', label: 'Papers indexed' },
            { n: '<30s', label: 'Result time' },
          ].map((s) => (
            <div key={s.n}>
              <div style={{ fontSize: 36, fontWeight: 800, fontFamily: 'var(--mono)', color: 'var(--accent)' }}>{s.n}</div>
              <div style={{ fontSize: 13, color: 'var(--text2)', marginTop: 4 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how" style={{ maxWidth: 820, margin: '0 auto', padding: '80px 24px' }}>
        <h2 style={{ fontSize: 32, fontWeight: 700, textAlign: 'center', marginBottom: 12 }}>How it works</h2>
        <p style={{ textAlign: 'center', color: 'var(--text2)', marginBottom: 56 }}>
          Three steps from upload to full report
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20 }}>
          {[
            { icon: '📤', step: '01', title: 'Upload your document', desc: 'PDF, DOCX, or TXT up to 10MB. Text is extracted and sent to the detection pipeline.' },
            { icon: '⚙️', step: '02', title: 'Agents run in parallel', desc: 'GPTZero, Sapling, ZeroGPT, Writer.com plus 3 local linguistic models — all run simultaneously. Results are weighted and cross-validated.' },
            { icon: '📊', step: '03', title: 'Get a clear report', desc: 'AI probability score, plagiarism percentage, matching sources, and a per-agent breakdown so you know exactly where the signal comes from.' },
          ].map((s) => (
            <div key={s.step} style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>{s.icon}</div>
              <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text3)', marginBottom: 8 }}>{s.step}</div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>{s.title}</h3>
              <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.6 }}>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Detection agents ── */}
      <section style={{ background: 'var(--bg2)', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', padding: '80px 24px' }}>
        <div style={{ maxWidth: 820, margin: '0 auto' }}>
          <h2 style={{ fontSize: 32, fontWeight: 700, textAlign: 'center', marginBottom: 12 }}>AI Detection agents</h2>
          <p style={{ textAlign: 'center', color: 'var(--text2)', marginBottom: 48 }}>
            Multiple independent models vote. Disagreements are flagged, not hidden.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
            {[
              { name: 'GPTZero', type: 'API', desc: 'Best overall accuracy. 10,000 words/day free.' },
              { name: 'Sapling', type: 'API', desc: 'Sentence-level scores. Catches mixed AI/human.' },
              { name: 'ZeroGPT', type: 'API', desc: 'Independent model. Covers rate limit gaps.' },
              { name: 'Writer.com', type: 'API', desc: 'Academic-focused training data.' },
              { name: 'Burstiness', type: 'Local', desc: 'AI text has unnaturally consistent complexity.' },
              { name: 'Perplexity', type: 'Local', desc: 'AI picks high-probability next words.' },
              { name: 'Lexical Patterns', type: 'Local', desc: 'AI has characteristic phrase fingerprints.' },
            ].map((a) => (
              <div key={a.name} style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '14px 16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{a.name}</span>
                  <span style={{ fontSize: 10, padding: '2px 7px', borderRadius: 99, background: a.type === 'API' ? 'var(--accent-glow)' : 'var(--green-bg)', color: a.type === 'API' ? 'var(--accent)' : 'var(--green)', fontWeight: 500 }}>{a.type}</span>
                </div>
                <p style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.5 }}>{a.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section style={{ maxWidth: 780, margin: '0 auto', padding: '80px 24px', textAlign: 'center' }}>
        <h2 style={{ fontSize: 32, fontWeight: 700, marginBottom: 12 }}>Simple pricing</h2>
        <p style={{ color: 'var(--text2)', marginBottom: 48 }}>First analysis free. Buy credits when you need more.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 40 }}>
          {[
            { label: 'Starter', price: '₹25', credits: '1 analysis', highlight: false },
            { label: 'Standard', price: '₹150', credits: '5 analyses', sub: 'Save ₹25', highlight: true },
            { label: 'Pro', price: '₹500', credits: '20 analyses', sub: 'Save ₹500', highlight: false },
          ].map((p) => (
            <div key={p.label} style={{
              background: p.highlight ? 'var(--accent-glow)' : 'var(--bg2)',
              border: `1px solid ${p.highlight ? 'var(--accent)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-lg)', padding: '28px 20px'
            }}>
              <div style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 8 }}>{p.label}</div>
              <div style={{ fontSize: 40, fontWeight: 800, fontFamily: 'var(--mono)', color: p.highlight ? 'var(--accent)' : 'var(--text)' }}>{p.price}</div>
              <div style={{ fontSize: 14, color: 'var(--text2)', margin: '8px 0' }}>{p.credits}</div>
              {p.sub && <div style={{ fontSize: 12, color: 'var(--green)' }}>{p.sub}</div>}
            </div>
          ))}
        </div>
        <Link to={user ? '/credits' : '/login'} className="btn btn-primary btn-lg">
          Start with a free analysis
        </Link>
      </section>

      {/* ── Footer ── */}
      <footer style={{ borderTop: '1px solid var(--border)', padding: '32px 24px', textAlign: 'center' }}>
        <p style={{ fontSize: 13, color: 'var(--text3)' }}>
          🔬 PaperLens · Built for researchers · Payments by Cashfree
        </p>
      </footer>
    </div>
  )
}
