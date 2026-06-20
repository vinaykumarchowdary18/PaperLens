import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/') }

  return (
    <nav>
      <div className="nav-inner">
        <Link to={user ? '/dashboard' : '/'} className="nav-logo">
          🔬 Paper<span>Lens</span>
        </Link>
        <div className="nav-right">
          {user ? (
            <>
              <span className="nav-credits">
                {user.credits} credit{user.credits !== 1 ? 's' : ''}
              </span>
              <Link to="/dashboard" className="nav-link">Analyse</Link>
              <Link to="/credits" className="nav-link">Buy Credits</Link>
              <button className="nav-btn" onClick={handleLogout}>Sign out</button>
            </>
          ) : (
            <Link to="/login" className="btn btn-primary btn-sm">Get started</Link>
          )}
        </div>
      </div>
    </nav>
  )
}
