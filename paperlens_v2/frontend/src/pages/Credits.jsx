import { useState, useEffect } from 'react'
import { getPackages, createOrder, getTransactions } from '../lib/api'
import { useAuth } from '../hooks/useAuth'
import Navbar from '../components/Navbar'

export default function Credits() {
  const { user, refreshUser } = useAuth()
  const [packages, setPackages] = useState([])
  const [selected, setSelected] = useState('standard')
  const [paying, setPaying] = useState(false)
  const [error, setError] = useState('')
  const [transactions, setTransactions] = useState([])
  const [txnLoading, setTxnLoading] = useState(true)

  useEffect(() => {
    getPackages().then((d) => setPackages(d.packages || []))
    getTransactions()
      .then((d) => setTransactions(d.transactions || []))
      .catch(() => {})
      .finally(() => setTxnLoading(false))
  }, [])

  const handlePay = async () => {
    setError('')
    setPaying(true)
    try {
      const order = await createOrder(selected)

      // Load Cashfree SDK dynamically
      if (!window.Cashfree) {
        await new Promise((res, rej) => {
          const s = document.createElement('script')
          s.src = order.cashfree_env === 'sandbox'
            ? 'https://sdk.cashfree.com/js/ui/2.0.0/cashfree.sandbox.js'
            : 'https://sdk.cashfree.com/js/ui/2.0.0/cashfree.js'
          s.onload = res
          s.onerror = rej
          document.head.appendChild(s)
        })
      }

      const cf = window.Cashfree({ mode: order.cashfree_env === 'sandbox' ? 'sandbox' : 'production' })
      cf.checkout({
        paymentSessionId: order.payment_session_id,
        returnUrl: `${window.location.origin}/payment/success?order_id=${order.order_id}`,
      })
    } catch (e) {
      setError(e.response?.data?.detail || 'Payment initialisation failed. Check your Cashfree keys in .env')
    } finally {
      setPaying(false)
    }
  }

  return (
    <>
      <Navbar />
      <div className="page">
        <div className="mb-6">
          <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 4 }}>Buy credits</h1>
          <p className="text-muted text-sm">
            You have <strong style={{ color: 'var(--accent)' }}>{user?.credits} credit{user?.credits !== 1 ? 's' : ''}</strong> remaining.
            Each credit = one full document analysis.
          </p>
        </div>

        {/* Package selector */}
        <div className="packages-grid mb-6">
          {packages.map((p) => (
            <div
              key={p.id}
              className={`pkg-card ${selected === p.id ? 'selected' : ''}`}
              onClick={() => setSelected(p.id)}
            >
              <div className="pkg-price">₹{p.amount_rupees}</div>
              <div className="pkg-credits">{p.credits} analysis credit{p.credits !== 1 ? 's' : ''}</div>
              <div className="pkg-label">{p.label}</div>
            </div>
          ))}
        </div>

        {error && (
          <div style={{ marginBottom: 16, padding: '10px 14px', background: 'var(--red-bg)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 'var(--radius-sm)', fontSize: 13, color: 'var(--red)' }}>
            {error}
          </div>
        )}

        <button
          className="btn btn-primary btn-lg w-full"
          onClick={handlePay}
          disabled={paying || !selected}
        >
          {paying ? 'Opening payment…' : `Pay with Cashfree — ₹${packages.find(p => p.id === selected)?.amount_rupees || ''}`}
        </button>

        <p className="text-xs text-muted" style={{ marginTop: 10, textAlign: 'center' }}>
          UPI · Cards · NetBanking · Wallets · Secured by Cashfree
        </p>

        {/* Transaction history */}
        <div style={{ marginTop: 48 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20 }}>Transaction history</h2>
          {txnLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <div className="spinner" style={{ margin: '0 auto' }} />
            </div>
          ) : transactions.length === 0 ? (
            <div className="empty">
              <div className="empty-icon">🧾</div>
              <h3>No transactions yet</h3>
              <p>Your payment history will appear here.</p>
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Amount</th>
                      <th>Credits</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((t) => (
                      <tr key={t.id}>
                        <td className="text-xs">{new Date(t.created_at).toLocaleString()}</td>
                        <td className="text-mono">₹{t.amount_rupees}</td>
                        <td className="text-mono">{t.credits}</td>
                        <td>
                          <span className={`badge badge-${t.status === 'paid' ? 'done' : 'processing'}`}>
                            {t.status === 'paid' ? '✓ paid' : '⏳ pending'}
                          </span>
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
