import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from '@tanstack/react-query';
import { createLogger } from './lib/logger';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import HomePage from './pages/HomePage';
import BrowsePage from './pages/BrowsePage';
import SkillDetailPage from './pages/SkillDetailPage';
import McpDetailPage from './pages/McpDetailPage';
import MarketplacePage from './pages/MarketplacePage';
import MarketplaceDetailPage from './pages/MarketplaceDetailPage';
import NotFoundPage from './pages/NotFoundPage';

const log = createLogger('app');

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      log.error('Query failed', {
        queryKey: JSON.stringify(query.queryKey),
        error: error instanceof Error ? error.message : String(error),
      });
    },
  }),
  mutationCache: new MutationCache({
    onError: (error) => {
      log.error('Mutation failed', {
        error: error instanceof Error ? error.message : String(error),
      });
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col bg-[#FAF8F5]">
          <Header />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/browse" element={<BrowsePage />} />
              <Route path="/marketplace" element={<MarketplacePage />} />
              <Route path="/marketplace/:org/:repo/:slug" element={<MarketplaceDetailPage />} />
              <Route path="/skills/:slug" element={<SkillDetailPage />} />
              <Route path="/mcp/:slug" element={<McpDetailPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
