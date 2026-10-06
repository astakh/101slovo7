import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import Onboarding from './pages/Onboarding';
import LessonPreview from './pages/LessonPreview';
import Lesson from './pages/Lesson';
import LessonSummary from './pages/LessonSummary';
import Settings from './pages/Settings';
import AdminPrompts from './pages/AdminPrompts';
import AdminDashboard from './pages/AdminDashboard';
import AdminDb from './pages/AdminDb';

// Настройка клиента кэширования
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // Данные считаются свежими 5 минут
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
            <Route path="/lesson-preview" element={<ProtectedRoute><LessonPreview /></ProtectedRoute>} />
            <Route path="/lesson" element={<ProtectedRoute><Lesson /></ProtectedRoute>} />
            <Route path="/lesson/:lessonId" element={<ProtectedRoute><Lesson /></ProtectedRoute>} />
            <Route path="/lesson/:lessonId/summary" element={<ProtectedRoute><LessonSummary /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
            <Route path="/admin" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />
            <Route path="/admin/prompts" element={<ProtectedRoute><AdminPrompts /></ProtectedRoute>} />
            <Route path="/admin/db" element={<ProtectedRoute><AdminDb /></ProtectedRoute>} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}