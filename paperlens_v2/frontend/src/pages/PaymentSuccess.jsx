import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { verifyPayment } from '../lib/api'
import { useAuth } from '../hooks/useAuth'
import Navbar from '../components/Navbar'

export default function PaymentSuccess() {
  const [params] = useSearchParams()
  const { refreshUser } = useAuth()
  const [state, setState] = useState('verifying') // verifying | success | failed
  const [credits, setCredits] = useState(0)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    const order_id = params.get('order_id')
    if (!order_id) { setState('failed'); return }

    verifyPayment(order_id)
      .then((res) => {
        if (res.success) {
          setCredits(res.credits_added || 0)
          setTotal(res.total_credits || 0)
          setState('success')
          refreshUser()
        } else {
          setState('failed')
        }
      })
      .catch(() => setState('failed'))
  }, [])

  return (
    <>
      <Navbar />
      <div className="page" style={{ textAlign: 'center', paddingTop: 100 }}>
        {state === 'verifying' && (
          <>
            <div className="spinner" style={{ margin: '0 auto 20px' }} />
            <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>Verifying payment…</h2>
            <p className="text-muted text-sm">Please wait, this takes a few seconds.</p>
          </>
        )}

        {state === 'success' && (
          <>
            <div style={{ fontSize: 64, marginBottom: 20 }}>✅</div>
            <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Payment successful</h2>
            <p className="text-muted" style={{ marginBottom: 6 }}>
              {credits} credit{credits !== 1 ? 's' : ''} added to your account.
            </p>
            <p style={{ fontSize: 28, fontWeight: 700, fontFamily: 'var(--mono)', color: 'var(--accent)', marginBottom: 32 }}>
              {total} credits total
            </p>
            <Link to="/dashboard" className="btn btn-primary btn-lg">Analyse a paper</Link>
          </>
        )}

        {state === 'failed' && (
          <>
            <div style={{ fontSize: 64, marginBottom: 20 }}>❌</div>
            <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Payment not confirmed</h2>
            <p className="text-muted" style={{ marginBottom: 32 }}>
              If money was deducted, credits will be added automatically via webhook within a few minutes.
              Check your credits balance before trying again.
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
              <Link to="/credits" className="btn btn-primary">Try again</Link>
              <Link to="/dashboard" className="btn btn-secondary">Go to Dashboard</Link>
            </div>
          </>
        )}
      </div>
    </>
  )
}
