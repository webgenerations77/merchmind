import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import type { User } from '../../firebase';

export default function Layout({ user }: { user: User }) {
  return (
    <div className="flex min-h-screen bg-app-shell">
      <Sidebar user={user} />
      <main className="flex-1 p-4 md:p-6 overflow-auto pt-18 md:pt-6">
        <Outlet />
      </main>
    </div>
  );
}
