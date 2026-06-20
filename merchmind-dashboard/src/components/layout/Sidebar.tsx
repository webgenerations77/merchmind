import { NavLink, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { logout, type User } from '../../firebase';

const links = [
  { to: '/', label: 'Dashboard', icon: '~' },
  { to: '/review', label: 'Review', icon: '#' },
  { to: '/collections', label: 'Collections', icon: '&' },
  { to: '/drews-mind', label: "Drew's Mind", icon: '!' },
  { to: '/marketing', label: 'Marketing', icon: '^' },
  { to: '/products', label: 'Products', icon: '%' },
  { to: '/batches', label: 'Batches', icon: '@' },
  { to: '/api-usage', label: 'API Usage', icon: '$' },
  { to: '/settings', label: 'Settings', icon: '*' },
];

export default function Sidebar({ user }: { user: User }) {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  return (
    <>
      {/* Mobile header bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 bg-bg-secondary border-b border-border flex items-center justify-between px-4 h-14">
        <button
          onClick={() => setOpen(!open)}
          className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-bg-tertiary transition-colors"
          aria-label="Toggle menu"
        >
          <svg width="22" height="18" viewBox="0 0 22 18" fill="none" className="text-text-primary">
            {open ? (
              <path d="M2 2L20 16M2 16L20 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            ) : (
              <>
                <path d="M1 1H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <path d="M1 9H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <path d="M1 17H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </>
            )}
          </svg>
        </button>
        <h1 className="text-base font-bold text-accent">MerchMind</h1>
        <div className="w-10 h-10 flex items-center justify-center">
          {user.photoURL && (
            <img src={user.photoURL} alt="" className="w-7 h-7 rounded-full" />
          )}
        </div>
      </div>

      {/* Backdrop */}
      {open && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed md:sticky top-0 left-0 z-50 w-64 md:w-56 h-full md:h-auto min-h-screen
        bg-bg-secondary border-r border-border flex flex-col
        transition-transform duration-300 ease-in-out
        ${open ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        <div className="p-5 border-b border-border">
          <h1 className="text-lg font-bold text-accent">MerchMind</h1>
          <p className="text-xs text-text-tertiary mt-0.5">AI Merch Pipeline</p>
        </div>
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-accent/15 text-accent font-medium'
                    : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary'
                }`
              }
            >
              <span className="text-base font-mono">{link.icon}</span>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-2 px-3 py-2">
            {user.photoURL && (
              <img src={user.photoURL} alt="" className="w-6 h-6 rounded-full" />
            )}
            <span className="text-xs text-text-secondary truncate flex-1">
              {user.displayName || user.email}
            </span>
          </div>
          <button
            onClick={logout}
            className="w-full px-3 py-1.5 rounded-lg text-xs text-text-tertiary hover:text-text-primary hover:bg-bg-tertiary transition-colors text-left"
          >
            Sign out
          </button>
        </div>
      </aside>
    </>
  );
}
