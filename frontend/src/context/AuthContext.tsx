import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; phone?: string; role?: string }) => Promise<void>;
  logout: () => void;
  demoLogin: (role: 'citizen' | 'admin') => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(api.getCurrentUser());
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const verifyAuth = async () => {
      const token = localStorage.getItem('civicpulse_token');
      if (token) {
        try {
          const freshUser = await api.getMe();
          setUser(freshUser);
          localStorage.setItem('civicpulse_user', JSON.stringify(freshUser));
        } catch {
          api.logout();
          setUser(null);
        }
      }
      setLoading(false);
    };
    verifyAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password);
    setUser(res.user);
  };

  const register = async (data: { email: string; password: string; full_name: string; phone?: string; role?: string }) => {
    const res = await api.register(data);
    setUser(res.user);
  };

  const logout = () => {
    api.logout();
    setUser(null);
  };

  const demoLogin = async (role: 'citizen' | 'admin') => {
    if (role === 'admin') {
      await login('admin@civicpulse.gov.in', 'Admin@12345');
    } else {
      await login('citizen@example.com', 'Citizen@12345');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        isAdmin: user?.role === 'admin',
        login,
        register,
        logout,
        demoLogin,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
