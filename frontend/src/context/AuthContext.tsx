import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, Profile } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  profile: Profile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, user: User) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('cp_token'));
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('cp_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchProfile = async () => {
    try {
      const data = await api.get<Profile>('/profile/me');
      setProfile(data);
    } catch {
      // Profile may not exist yet or token expired
    }
  };

  const login = async (newToken: string, newUser: User) => {
    localStorage.setItem('cp_token', newToken);
    localStorage.setItem('cp_user', JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
    await fetchProfile();
  };

  const logout = () => {
    localStorage.removeItem('cp_token');
    localStorage.removeItem('cp_user');
    setToken(null);
    setUser(null);
    setProfile(null);
  };

  const refreshProfile = async () => {
    if (token) {
      await fetchProfile();
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const currentUser = await api.get<User>('/auth/me');
          setUser(currentUser);
          localStorage.setItem('cp_user', JSON.stringify(currentUser));
          await fetchProfile();
        } catch {
          logout();
        }
      }
      setIsLoading(false);
    };

    initAuth();

    const handleAuthChange = () => {
      setToken(null);
      setUser(null);
      setProfile(null);
    };

    window.addEventListener('cp_auth_change', handleAuthChange);
    return () => window.removeEventListener('cp_auth_change', handleAuthChange);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
        refreshProfile,
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
