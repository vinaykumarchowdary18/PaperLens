import { createContext, useContext, useState, useEffect } from 'react'
import { getMe } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const u = localStorage.getItem('pl_user')
      return u ? JSON.parse(u) : null
    } catch { return null }
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('pl_token')
    if (!token) { setLoading(false); return }
    getMe()
      .then((u) => { setUser(u); localStorage.setItem('pl_user', JSON.stringify(u)) })
      .catch(() => { localStorage.removeItem('pl_token'); localStorage.removeItem('pl_user'); setUser(null) })
      .finally(() => setLoading(false))
  }, [])

  const login = (token, userData) => {
    localStorage.setItem('pl_token', token)
    localStorage.setItem('pl_user', JSON.stringify(userData))
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('pl_token')
    localStorage.removeItem('pl_user')
    setUser(null)
  }

  const refreshUser = () =>
    getMe().then((u) => { setUser(u); localStorage.setItem('pl_user', JSON.stringify(u)) })

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
