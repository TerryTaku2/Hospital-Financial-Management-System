import type { ReactNode } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/patients', label: 'Patients' },
  { to: '/opd', label: 'OPD' },
  { to: '/ipd', label: 'IPD' },
  { to: '/appointments', label: 'Appointments' },
  { to: '/setup', label: 'Branches & Beds' },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">Hospital ERP</div>
        <nav>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <span>
            {user?.first_name || user?.username}{' '}
            <span className="role-badge">{user?.role.replace('_', ' ')}</span>
          </span>
          <button onClick={handleLogout} className="btn-link">
            Log out
          </button>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
