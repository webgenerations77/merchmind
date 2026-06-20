import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import type { User } from '../../firebase';

export default function Layout({ user }: { user: User }) {
  return (
    <div className="flex min-h-screen bg-bg-primary">
      <Sidebar user={user} />
      <main className="flex-1 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
