import { NavLink } from 'react-router-dom';

const links = [
  { to: '/', label: 'Dashboard', icon: '~' },
  { to: '/review', label: 'Review', icon: '#' },
  { to: '/drews-mind', label: "Drew's Mind", icon: '!' },
  { to: '/products', label: 'Products', icon: '%' },
  { to: '/batches', label: 'Batches', icon: '@' },
  { to: '/settings', label: 'Settings', icon: '*' },
];

export default function Sidebar() {
  return (
    <aside className="w-56 min-h-screen bg-bg-secondary border-r border-border flex flex-col">
      <div className="p-5 border-b border-border">
        <h1 className="text-lg font-bold text-accent">MerchMind</h1>
        <p className="text-xs text-text-tertiary mt-0.5">AI Merch Pipeline</p>
      </div>
      <nav className="flex-1 p-3 space-y-1">
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
    </aside>
  );
}
