import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './contexts/AuthContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Clients from './pages/Clients'
import ClientDetail from './pages/ClientDetail'
import Pipeline from './pages/Pipeline'
import PipelineSettings from './pages/PipelineSettings'
import Programs from './pages/Programs'
import ProgramView from './pages/ProgramView'
import Progress from './pages/Progress'
import Analytics from './pages/Analytics'
import WebsiteSettings from './pages/WebsiteSettings'
import Pipelines from './pages/Pipelines'
import AIAgentSettings from './pages/AIAgentSettings'
import Marketing from './pages/Marketing'
import Integrations from './pages/Integrations'
import SocialPosts from './pages/SocialPosts'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import ScrollToTop from './components/ScrollToTop'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  // Базовый путь из конфигурации Vite (автоматически устанавливается из base в vite.config.ts)
  // Для production: /admin/, для development: /
  const basename = import.meta.env.BASE_URL || '/'
  
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter basename={basename}>
          <ScrollToTop />
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="clients" element={<Clients />} />
              <Route path="clients/:id" element={<ClientDetail />} />
              <Route path="pipeline" element={<Pipeline />} />
              <Route path="pipeline/settings" element={<PipelineSettings />} />
              <Route path="programs" element={<Programs />} />
              <Route path="programs/:id" element={<ProgramView />} />
              <Route path="progress/:clientId" element={<Progress />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="website-settings" element={<WebsiteSettings />} />
              <Route path="pipelines" element={<Pipelines />} />
              <Route path="marketing" element={<Marketing />} />
              <Route path="social-posts" element={<SocialPosts />} />
              <Route path="integrations" element={<Integrations />} />
              <Route path="ai-agent" element={<AIAgentSettings />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App

