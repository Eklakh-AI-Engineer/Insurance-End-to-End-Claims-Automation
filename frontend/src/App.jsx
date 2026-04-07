import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import ClaimForm from './components/ClaimForm'
import AdminDashboard from './components/AdminDashboard'

function Navbar() {
    const loc = useLocation()
    return (
        <nav className="navbar">
            <div className="navbar-inner">
                <NavLink to="/" className="navbar-brand">
                    <div className="brand-icon">⚡</div>
                    ClaimAI
                </NavLink>
                <div className="navbar-links">
                    <NavLink to="/" className={({ isActive }) => `nav-link ${isActive && loc.pathname === '/' ? 'active' : ''}`}>
                        📝 File Claim
                    </NavLink>
                    <NavLink to="/admin" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        🏛️ Admin
                    </NavLink>
                    <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="nav-link">
                        📖 API Docs
                    </a>
                </div>
            </div>
        </nav>
    )
}

export default function App() {
    return (
        <>
            <Navbar />
            <Routes>
                <Route path="/" element={<ClaimForm />} />
                <Route path="/admin" element={<AdminDashboard />} />
            </Routes>
        </>
    )
}
