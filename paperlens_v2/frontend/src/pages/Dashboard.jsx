import { useState, useRef, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { uploadDocument, getHistory } from '../lib/api'
import { useAuth } from '../hooks/useAuth'
import Navbar from '../components/Navbar'
import { useEffect } from 'react'

export default function Dashboard() {
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [history, setHistory] = useState([])
  const [histLoading, setHistLoading] = useState(true)
  const fileRef = useRef()

  useEffect(() => {
    getHistory()
      .then((d) => setHistory(d.analyses || []))
      .catch(() => {})
      .finally(() => setHistLoading(false))
  }, [])

  const handleFile = useCallback(async (file) => {
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['pdf', 'docx', 'txt'].includes(ext)) {
      setError('Only PDF, DOCX, and TXT files are supported.')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('File must be under 10MB.')
      return
    }

    if (user.free_used && user.credits <= 0) {
      navigate('/credits')
      return
    }

    setError('')
    setUploading(true)
    try {
      const result = await uploadDocument(file)
      await refreshUser()
      navigate(`/results/${result.analysis_id}`)
    } catch (e) {
      const msg = e.response?.data?.detail || 'Upload failed. Please try again.'
      if (e.response?.status === 402) navigate('/credits')
      else setError(msg)
    } finally {
      setUploading(false)
    }
  }, [user, navigate, refreshUser])

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }

  const onDragOver = (e) => { e.preventDefault(); setDragging(true) }
  const onDragLeave = () => setDragging(false)

  const noCredits = user?.free_used && user?.credits <= 0

  return (
    <>
      <Navbar />
      <div className="page">
        {/* Header */}
        <div className="mb-6">
          <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 4 }}>
            Analyse a paper
          </h1>
          <p className="text-muted text-sm">
            {user?.free_used === 0
              ? 'Your first analysis is free — no credits needed.'
              : `You have ${user?.credits} credit${user?.credits !== 1 ? 's' : ''} remaining.`}
          </p>
        </div>

        {/* Upload zone */}
        {noCredits ? (
          <div style={{ background: 'var(--amber-bg)', border: '1px solid rgba(251,191,36,0.3)', borderRadius: 'var(--radius-lg)', padding: '40px 24px', textAlign: 'center' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>💳</div>
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>No credits remaining</h3>
            <p className="text-muted text-sm" style={{ marginBottom: 20 }}>Purchase credits to continue analysing papers.</p>
            <Link to="/credits" className="btn btn-primary">Buy credits</Link>
          </div>
        ) : (
          <div
            className={`upload-zone ${dragging ? 'dragover' : ''} ${uploading ? 'dragover' : ''}`}
            onClick={() => !uploading && fileRef.current?.click()}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt"
              style={{ display: 'none' }}
              onChange={(e) => handleFile(e.target.files[0])}
            />
            {uploading ? (
              <>
                <div className="spinner" style={{ margin: '0 auto 16px' }} />
                <h3>Uploading and analysing…</h3>
                <p>This takes 10–30 seconds. Don't close the tab.</p>
              </>
            ) : (
              <>
                <div className="upload-icon">📄</div>
                <h3>Drop your paper here</h3>
                <p>PDF, DOCX, or TXT · Max 10MB · Click to browse</p>
              </>
            )}
          </div>
        )}

        {error && (
          <div style={{ marginTop: 12, padding: '10px 14px', background: 'var(--red-bg)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 'var(--radius-sm)', fontSize: 13, color: 'var(--red)' }}>
            {error}
          </div>
        )}

        {/* History */}
        <div style={{ marginTop: 48 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20 }}>Recent analyses</h2>
          {histLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <div className="spinner" style={{ margin: '0 auto' }} />
            </div>
          ) : history.length === 0 ? (
            <div className="empty">
              <div className="empty-icon">📭</div>
              <h3>No analyses yet</h3>
              <p>Upload a paper above to get your first report.</p>
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Filename</th>
                      <th>AI Score</th>
                      <th>Plag Score</th>
                      <th>Words</th>
                      <th>Status</th>
                      <th>Date</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((a) => (
                      <tr key={a.id}>
                        <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text)' }}>
                          {a.filename}
                        </td>
                        <td>
                          {a.ai_score != null
                            ? <span style={{ fontFamily: 'var(--mono)', color: a.ai_score > 50 ? 'var(--red)' : 'var(--green)' }}>{a.ai_score}%</span>
                            : '—'}
                        </td>
                        <td>
                          {a.plag_score != null
                            ? <span style={{ fontFamily: 'var(--mono)', color: a.plag_score > 20 ? 'var(--amber)' : 'var(--green)' }}>{a.plag_score}%</span>
                            : '—'}
                        </td>
                        <td className="text-mono">{a.word_count?.toLocaleString() || '—'}</td>
                        <td>
                          <span className={`badge badge-${a.status}`}>
                            {a.status === 'processing' && '⏳ '}
                            {a.status === 'done' && '✓ '}
                            {a.status === 'error' && '✗ '}
                            {a.status}
                          </span>
                        </td>
                        <td className="text-xs">
                          {new Date(a.created_at).toLocaleDateString()}
                        </td>
                        <td>
                          {a.status === 'done' && (
                            <Link to={`/results/${a.id}`} className="btn btn-ghost btn-sm">View →</Link>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
