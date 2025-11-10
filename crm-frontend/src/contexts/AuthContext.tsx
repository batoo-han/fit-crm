import React, { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../services/api'

interface User {
  id: number
  username: string
  email: string | null
  role: string
  is_active: boolean
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))

  const logout = () => {
    setToken(null)
    setUser(null)
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
  }

  const fetchUser = async () => {
    try {
      const response = await api.get('/auth/me')
      setUser(response.data)
    } catch (error) {
      console.error('Failed to fetch user:', error)
      logout()
    }
  }

  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      fetchUser()
    } else {
      setUser(null)
    }
  }, [token])

  const login = async (username: string, password: string) => {
    try {
      const response = await api.post('/auth/login', { username, password })
      const { access_token, user: userData } = response.data
      
      if (!access_token) {
        throw new Error('No access token received')
      }
      
      setToken(access_token)
      setUser(userData)
      localStorage.setItem('token', access_token)
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
    } catch (error: any) {
      console.error('Login error:', error)
      throw error
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        logout,
        isAuthenticated: !!token && !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

