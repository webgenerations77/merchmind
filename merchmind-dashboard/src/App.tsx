import { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { auth, onAuthStateChanged, isAllowedUser, type User } from './firebase';
import Layout from './components/layout/Layout';
import LoginScreen from './components/auth/LoginScreen';
import DashboardPage from './pages/DashboardPage';
import ReviewPage from './pages/ReviewPage';
import ProductsPage from './pages/ProductsPage';
import BatchesPage from './pages/BatchesPage';
import SettingsPage from './pages/SettingsPage';
import CollectionsPage from './pages/CollectionsPage';
import DrewsMindPage from './pages/DrewsMindPage';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (u) => {
      setUser(u && isAllowedUser(u) ? u : null);
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  if (loading) {
    return <div className="min-h-screen bg-bg-primary flex items-center justify-center text-text-secondary">Loading...</div>;
  }

  if (!user) {
    return <LoginScreen />;
  }

  return (
    <Routes>
      <Route element={<Layout user={user} />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/collections" element={<CollectionsPage />} />
        <Route path="/drews-mind" element={<DrewsMindPage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/batches" element={<BatchesPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
