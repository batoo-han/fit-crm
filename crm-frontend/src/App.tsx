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
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
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
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App

