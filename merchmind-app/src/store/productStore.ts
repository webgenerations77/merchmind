import { create } from 'zustand';
import type { Product } from '../types/api';
import { listProducts, updateProduct, unpublishProduct } from '../api/products';

type SortKey = 'revenue' | 'trend_score' | 'date';

interface ProductState {
  products: Product[];
  sortKey: SortKey;
  filterNiche: string | null;
  isLoading: boolean;
  error: string | null;

  fetchProducts: () => Promise<void>;
  setSortKey: (key: SortKey) => void;
  setFilterNiche: (niche: string | null) => void;
  updateProductPrice: (productId: string, price: number) => Promise<void>;
  unpublishProduct: (productId: string) => Promise<void>;
}

export const useProductStore = create<ProductState>((set, get) => ({
  products: [],
  sortKey: 'revenue',
  filterNiche: null,
  isLoading: false,
  error: null,

  fetchProducts: async () => {
    set({ isLoading: true, error: null });
    try {
      const products = await listProducts('published');
      set({ products, isLoading: false });
    } catch (e: unknown) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  setSortKey: (key: SortKey) => set({ sortKey: key }),
  setFilterNiche: (niche: string | null) => set({ filterNiche: niche }),

  updateProductPrice: async (productId: string, price: number) => {
    set(state => ({
      products: state.products.map(p =>
        p.id === productId ? { ...p, retail_price: price } : p,
      ),
    }));
    try {
      await updateProduct(productId, { retail_price: price });
    } catch {
      await get().fetchProducts();
      throw new Error('Failed to update price');
    }
  },

  unpublishProduct: async (productId: string) => {
    try {
      await unpublishProduct(productId);
      set(state => ({
        products: state.products.map(p =>
          p.id === productId ? { ...p, publish_status: 'unpublished' } : p,
        ),
      }));
    } catch (e: unknown) {
      throw new Error('Failed to unpublish product');
    }
  },
}));
