'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '../components/auth-provider';
import { Film, Play, Sparkles, Video, ArrowRight, Layers, Layout, Share2, Plus } from 'lucide-react';

export default function Home() {
  const { user, loginWithGoogle, loginWithCredentials, logout } = useAuth();
  const router = useRouter();

  const [showLoginModal, setShowLoginModal] = React.useState(false);
  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [loginError, setLoginError] = React.useState('');
  const [isLoggingIn, setIsLoggingIn] = React.useState(false);

  const handleLaunch = () => {
    if (user) {
      router.push('/projects');
    } else {
      setShowLoginModal(true);
    }
  };

  const onSubmitCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    setIsLoggingIn(true);
    try {
      const success = await loginWithCredentials(username, password);
      if (success) {
        setShowLoginModal(false);
        router.push('/projects');
      } else {
        setLoginError('Invalid production credentials.');
      }
    } catch (err) {
      setLoginError('An error occurred during authentication.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col text-gray-200 overflow-hidden relative">
      {/* Cinematic Glowing Background Spotlights */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-yellow-600/10 rounded-full blur-[120px] pointer-events-none animate-pulse"></div>
      <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-purple-900/15 rounded-full blur-[160px] pointer-events-none"></div>

      {/* Header navbar */}
      <header className="glass h-16 flex items-center justify-between px-8 border-b border-border/80 sticky top-0 z-50">
        <div className="flex items-center space-x-2">
          <div className="bg-primary text-black p-1.5 rounded-md">
            <Film size={18} className="stroke-[2.5]" />
          </div>
          <span className="font-bold tracking-wider text-lg bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            70MM AI
          </span>
        </div>
        
        {user ? (
          <div className="flex items-center space-x-4">
            {user.photoURL && (
              <img 
                src={user.photoURL} 
                alt={user.displayName || "User"} 
                className="w-6 h-6 rounded-full border border-border"
              />
            )}
            <span className="text-xs text-gray-400">Hi, {user.displayName || 'Director'}</span>
            <button 
              onClick={logout}
              className="px-3 py-1.5 rounded bg-secondary hover:bg-muted border border-border text-[10px] font-bold text-gray-300 hover:text-white cursor-pointer transition-colors"
            >
              Sign Out
            </button>
            <Link 
              href="/projects"
              className="flex items-center space-x-1 px-4 py-2 rounded bg-primary text-black font-bold text-xs hover:bg-primary/95 transition-all shadow-[0_0_15px_rgba(234,179,8,0.25)] hover:shadow-primary/40 cursor-pointer"
            >
              <span>Dashboard</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        ) : (
          <button 
            onClick={() => setShowLoginModal(true)}
            className="flex items-center space-x-1 px-4 py-2 rounded bg-primary text-black font-bold text-xs hover:bg-primary/95 transition-all shadow-[0_0_15px_rgba(234,179,8,0.25)] hover:shadow-primary/40 cursor-pointer"
          >
            <span>Sign In / Launch</span>
            <ArrowRight size={13} />
          </button>
        )}
      </header>

      {/* Hero section */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-20 flex flex-col items-center justify-center text-center space-y-10 z-10">
        <div className="space-y-4">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-primary/10 border border-primary/25 text-primary text-[10px] font-bold tracking-wider uppercase animate-pulse">
            <Sparkles size={10} />
            <span>AI-Powered Filmmaking Workspace</span>
          </div>
          
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-white leading-tight">
            From Idea to <span className="bg-gradient-to-r from-yellow-500 to-amber-600 bg-clip-text text-transparent">Storyboard</span><br />
            in Minutes.
          </h1>
          
          <p className="max-w-xl mx-auto text-sm md:text-base text-gray-400 leading-relaxed">
            The elite workspace for directors, screenwriters, and creative producers. 
            Brainstorm outlines, parse screenplays, customize shots, and generate storyboards instantly.
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={handleLaunch}
            className="flex items-center space-x-2 px-8 py-3 bg-primary text-black font-bold text-sm rounded-lg hover:bg-primary/90 hover:scale-[1.02] transition-all cursor-pointer shadow-xl shadow-primary/10"
          >
            <Play size={15} fill="black" />
            <span>{user ? "Go to Dashboard" : "Start Free Production"}</span>
          </button>
          <a
            href="#features"
            className="px-8 py-3 bg-secondary hover:bg-muted border border-border text-xs font-semibold rounded-lg text-gray-300 hover:text-white transition-colors cursor-pointer"
          >
            Explore Features
          </a>
        </div>

        {/* Cinematic Mockup Frame */}
        <div className="w-full border border-border bg-[#0d0d15]/50 backdrop-blur rounded-2xl p-2.5 overflow-hidden shadow-2xl relative">
          <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent z-10 pointer-events-none"></div>
          <div className="aspect-video w-full rounded-xl bg-gradient-to-br from-[#0c0c14] to-[#161623] border border-border/40 relative flex items-center justify-center p-8 group">
            {/* Play Button Overlay */}
            <div className="absolute w-16 h-16 rounded-full bg-primary/10 border border-primary/45 backdrop-blur flex items-center justify-center text-primary group-hover:scale-110 group-hover:bg-primary group-hover:text-black transition-all cursor-pointer shadow-lg z-20">
              <Play size={20} fill="currentColor" className="ml-1" />
            </div>
            
            {/* Visual background lines mimicking layout */}
            <div className="w-full h-full flex justify-between space-x-4 opacity-15">
              <div className="w-1/4 border border-border rounded-lg p-2 flex flex-col space-y-2">
                <div className="w-1/2 h-2 bg-gray-500 rounded"></div>
                <div className="w-full h-4 bg-gray-500 rounded"></div>
                <div className="w-full h-4 bg-gray-500 rounded"></div>
              </div>
              <div className="flex-1 border border-border rounded-lg p-4 flex flex-col space-y-3">
                <div className="w-1/4 h-3 bg-gray-500 rounded"></div>
                <div className="w-full h-24 bg-gray-500 rounded"></div>
              </div>
              <div className="w-1/3 border border-border rounded-lg p-2 flex flex-col space-y-2">
                <div className="w-1/3 h-2 bg-gray-500 rounded"></div>
                <div className="w-full h-12 bg-gray-500 rounded"></div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Features List Section */}
      <section id="features" className="border-t border-border bg-[#07070c] py-20 px-6 z-10">
        <div className="max-w-5xl mx-auto space-y-12">
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold tracking-tight text-white">Full Cinematic Pipeline</h2>
            <p className="text-xs text-gray-500">Every phase of pre-production powered by robust engineering.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
            <div className="bg-[#0d0d15]/40 border border-border/50 p-6 rounded-2xl space-y-4 hover:border-border transition-colors">
              <div className="bg-primary/10 text-primary p-2.5 rounded-lg w-10 h-10 flex items-center justify-center border border-primary/20">
                <Layers size={18} />
              </div>
              <h3 className="font-bold text-gray-200">1. Story & Script Parser</h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                Translate a simple logline into acts, beats, and character cast via Gemini. Upload a screenplay to split scenes deterministically.
              </p>
            </div>

            <div className="bg-[#0d0d15]/40 border border-border/50 p-6 rounded-2xl space-y-4 hover:border-border transition-colors">
              <div className="bg-blue-500/10 text-blue-400 p-2.5 rounded-lg w-10 h-10 flex items-center justify-center border border-blue-500/20">
                <Layout size={18} />
              </div>
              <h3 className="font-bold text-gray-200">2. Shot Planner & Muse</h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                Draft shot numbers, sizes, lenses, lighting, and movement. Trigger Director's Muse AI to get 3 creative visual composition alternatives.
              </p>
            </div>

            <div className="bg-[#0d0d15]/40 border border-border/50 p-6 rounded-2xl space-y-4 hover:border-border transition-colors">
              <div className="bg-purple-500/10 text-purple-400 p-2.5 rounded-lg w-10 h-10 flex items-center justify-center border border-purple-500/20">
                <Share2 size={18} />
              </div>
              <h3 className="font-bold text-gray-200">3. Storyboard & Exports</h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                Generate storyboards automatically via Flux.1 Dev (or our premium fallback). Export a professional PDF script package or CSV sheet.
              </p>
            </div>
          </div>
        </div>
      </section>
      
      {/* Footer */}
      <footer className="border-t border-border bg-[#05050a] py-6 px-8 flex justify-between text-[10px] text-gray-600">
        <span>70MM AI - 48H MVP Challenge</span>
        <span>© 2026 70mm.ai. All rights reserved.</span>
      </footer>

      {/* Login Modal Overlay */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4 backdrop-blur-md animate-fade-in">
          <div className="relative max-w-sm w-full rounded-2xl overflow-hidden border border-amber-500/30 bg-[#07070c]/95 shadow-[0_0_50px_rgba(245,158,11,0.15)] flex flex-col">
            
            {/* Ambient Border Glow effect */}
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent"></div>
            
            <button 
              onClick={() => {
                setShowLoginModal(false);
                setLoginError('');
              }}
              className="absolute top-4 right-4 text-gray-500 hover:text-amber-500 transition-colors cursor-pointer"
              title="Close modal"
            >
              <Plus className="rotate-45" size={20} />
            </button>

            <div className="px-6 pt-8 pb-3 text-center">
              <div className="bg-amber-500/10 text-amber-500 p-3 rounded-xl w-12 h-12 flex items-center justify-center border border-amber-500/20 mx-auto mb-4 shadow-[0_0_15px_rgba(245,158,11,0.1)]">
                <Film size={24} className="stroke-[2]" />
              </div>
              <h3 className="font-bold text-lg text-white tracking-wide screenplay-font">Production Access</h3>
              <p className="text-[10px] text-gray-500 mt-1 uppercase tracking-widest">Authorized Directors Only</p>
            </div>

            <form onSubmit={onSubmitCredentials} className="p-6 pt-2 space-y-4 text-left">
              {loginError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-[11px] px-3 py-2 rounded-lg text-center font-medium">
                  {loginError}
                </div>
              )}
              
              <div className="space-y-1.5">
                <label className="text-[9px] font-bold text-gray-500 uppercase tracking-widest">Username</label>
                <input 
                  type="text" 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter production username (vasu)" 
                  required
                  className="w-full bg-[#0d0d15] border border-gray-800 rounded-lg px-3.5 py-2.5 text-xs text-gray-200 focus:outline-none focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/30 placeholder-gray-600 transition-all font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[9px] font-bold text-gray-500 uppercase tracking-widest">Password</label>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="•••••••• (vasu)" 
                  required
                  className="w-full bg-[#0d0d15] border border-gray-800 rounded-lg px-3.5 py-2.5 text-xs text-gray-200 focus:outline-none focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/30 placeholder-gray-600 transition-all"
                />
              </div>

              <button 
                type="submit"
                disabled={isLoggingIn}
                className="w-full py-2.5 bg-gradient-to-r from-amber-600 to-amber-500 text-black font-bold text-xs rounded-lg hover:from-amber-500 hover:to-amber-400 transition-all cursor-pointer flex items-center justify-center space-x-1 shadow-[0_0_20px_rgba(245,158,11,0.2)] hover:shadow-[0_0_25px_rgba(245,158,11,0.35)] disabled:opacity-50 mt-2"
              >
                {isLoggingIn ? (
                  <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <span className="uppercase tracking-wider font-extrabold text-[10px]">Initialize Session</span>
                )}
              </button>
            </form>

            <div className="px-6 pb-6 pt-2 flex flex-col space-y-3">
              <div className="relative flex items-center justify-center">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-800/80"></div>
                </div>
                <span className="relative px-3 bg-[#07070c] text-[9px] text-gray-500 uppercase tracking-widest">External Accounts</span>
              </div>

              <button 
                onClick={async () => {
                  try {
                    await loginWithGoogle();
                    setShowLoginModal(false);
                    router.push('/projects');
                  } catch (e) {
                    console.error(e);
                  }
                }}
                className="w-full py-2 border border-gray-800 hover:border-gray-700 bg-[#0d0d15]/50 text-gray-300 hover:text-white transition-colors cursor-pointer text-xs font-semibold rounded-lg flex items-center justify-center space-x-2"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fillRule="evenodd" />
                  <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                <span className="text-[10px] uppercase tracking-wider font-bold">Google Sign-In</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
