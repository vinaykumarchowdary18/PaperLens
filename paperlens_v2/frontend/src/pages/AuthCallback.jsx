import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { exchangeGoogleCode } from '../lib/api'
import { useAuth } from '../hooks/useAuth'

export default function AuthCallback() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { login } = useAuth()
  const done = useRef(false)

  useEffect(() => {
    if (done.current) return
    done.current = true

    const code = params.get('code')
    const error = params.get('error')

    if (error || !code) {
      navigate('/login?error=cancelled', { replace: true })
      return
    }

    const redirect_uri = `${window.location.origin}/auth/callback`

    exchangeGoogleCode(code, redirect_uri)
      .then(({ token, user }) => {
        login(token, user)
        navigate('/dashboard', { replace: true })
      })
      .catch(() => navigate('/login?error=failed', { replace: true }))
  }, [])

  return (
    <div className="loading-screen" style={{ flexDirection: 'column', gap: 20 }}>
      <div className="spinner" />
      <p style={{ color: 'var(--text2)', fontSize: 14 }}>Signing you in…</p>
    </div>
  )
}
