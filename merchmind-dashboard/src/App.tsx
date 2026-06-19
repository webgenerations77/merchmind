import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import DashboardPage from './pages/DashboardPage';
import ReviewPage from './pages/ReviewPage';
import ProductsPage from './pages/ProductsPage';
import BatchesPage from './pages/BatchesPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/batches" element={<BatchesPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
