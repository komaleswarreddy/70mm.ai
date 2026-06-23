'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { auth, googleProvider, hasFirebaseConfig } from '../lib/firebase';
import { signInWithPopup, signOut, onAuthStateChanged } from 'firebase/auth';

interface AuthUser {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
  token: string | null;
}

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  loginWithGoogle: () => Promise<void>;
  loginWithCredentials: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('70mm_firebase_user');
    if (stored) {
      try {
        setUser(JSON.parse(stored));
      } catch (e) {
        console.error("Failed to parse stored user", e);
      }
    }

    if (!hasFirebaseConfig || !auth) {
      setLoading(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, async (fbUser) => {
      if (fbUser) {
        const token = await fbUser.getIdToken();
        const authUser = {
          uid: fbUser.uid,
          email: fbUser.email,
          displayName: fbUser.displayName,
          photoURL: fbUser.photoURL,
          token,
        };
        setUser(authUser);
        localStorage.setItem('70mm_firebase_user', JSON.stringify(authUser));
      } else {
        const storedUser = localStorage.getItem('70mm_firebase_user');
        if (storedUser) {
          try {
            const parsed = JSON.parse(storedUser);
            if (parsed.token && !parsed.token.startsWith('mock_')) {
              setUser(null);
              localStorage.removeItem('70mm_firebase_user');
            }
          } catch {
            setUser(null);
            localStorage.removeItem('70mm_firebase_user');
          }
        } else {
          setUser(null);
        }
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const loginWithGoogle = async () => {
    if (!hasFirebaseConfig || !auth || !googleProvider) {
      alert("Google Sign-In is unavailable because Firebase is not configured. Please use the Demo Credentials.");
      return;
    }

    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      console.error("Google Sign-In failed", err);
    }
  };

  const loginWithCredentials = async (username: string, password: string): Promise<boolean> => {
    if (username === 'vasu' && password === 'vasu') {
      const demoUser: AuthUser = {
        uid: 'uid_vasu',
        email: 'vasu@70mm.ai',
        displayName: 'vasu',
        photoURL: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=facearea&facepad=2&w=256&h=256&q=80',
        token: 'mock_vasu_token_xyz',
      };
      setUser(demoUser);
      localStorage.setItem('70mm_firebase_user', JSON.stringify(demoUser));
      return true;
    }
    return false;
  };

  const logout = async () => {
    setUser(null);
    localStorage.removeItem('70mm_firebase_user');
    
    if (hasFirebaseConfig && auth) {
      try {
        await signOut(auth);
      } catch (err) {
        console.error("Logout failed", err);
      }
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, loginWithGoogle, loginWithCredentials, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
