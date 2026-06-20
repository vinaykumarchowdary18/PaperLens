import axios from 'axios'

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
})

// Attach JWT token to every request
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('pl_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
API.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('pl_token')
      localStorage.removeItem('pl_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const getGoogleLoginUrl = () =>
  `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/auth/google/login`

export const exchangeGoogleCode = (code, redirect_uri) =>
  API.post('/auth/google/callback', { code, redirect_uri }).then((r) => r.data)

export const getMe = () => API.get('/auth/me').then((r) => r.data)

// ── Analysis ──────────────────────────────────────────────────────────────────
export const uploadDocument = (file) => {
  const form = new FormData()
  form.append('file', file)
  return API.post('/analysis/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const getAnalysis = (id) =>
  API.get(`/analysis/${id}`).then((r) => r.data)

export const getHistory = () =>
  API.get('/analysis/history').then((r) => r.data)

// ── Payment ───────────────────────────────────────────────────────────────────
export const getPackages = () =>
  API.get('/payment/packages').then((r) => r.data)

export const createOrder = (pkg) =>
  API.post('/payment/create-order', { package: pkg }).then((r) => r.data)

export const verifyPayment = (order_id) =>
  API.post('/payment/verify', { order_id }).then((r) => r.data)

export const getTransactions = () =>
  API.get('/payment/transactions').then((r) => r.data)
