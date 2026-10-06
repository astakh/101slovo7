import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiClient } from '../api/client';

interface User {
  id: number;
  email: string;
  is_onboarded: boolean;
  timezone?: string | null;
  is_admin: boolean;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isInitializing: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchUser(token);
    } else {
      setIsInitializing(false);
    }
  }, []);

  const fetchUser = async (token: string) => {
    try {
      const userData = await apiClient.getMe();
      setUser(userData);
    } catch (error) {
      console.error('Token validation failed:', error);
      localStorage.removeItem('access_token');
      setUser(null);
    } finally {
      setIsInitializing(false);
    }
  };

  const login = async (email: string, password: string) => {
    const data = await apiClient.login(email, password);
    localStorage.setItem('access_token', data.access_token);
    const userData = await apiClient.getMe();
    setUser(userData);
  };

  const register = async (email: string, password: string) => {
    const data = await apiClient.register(email, password);
    localStorage.setItem('access_token', data.access_token);
    const userData = await apiClient.getMe();
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isInitializing,
        login,
        register,
        logout,
        setUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}