'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Navbar } from '../../components/navbar';
import { api, Project } from '../../lib/api';
import { Film, Plus, Trash2, Video, Calendar, Sparkles, Copy, Edit2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../components/auth-provider';

export default function Dashboard() {
  const { user, loading: authLoading } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState('');
  const [logline, setLogline] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [renamingProject, setRenamingProject] = useState<{ id: string; title: string } | null>(null);

  const router = useRouter();

  const fetchProjects = async () => {
    try {
      const projs = await api.getProjects();
      setProjects(projs);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push('/');
      } else {
        fetchProjects();
      }
    }
  }, [user, authLoading]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    
    setIsCreating(true);
    try {
      const newProj = await api.createProject(title, logline);
      setShowModal(false);
      setTitle('');
      setLogline('');
      router.push(`/workspace/${newProj.id}`);
    } catch (err) {
      console.error(err);
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    if (confirm("Are you sure you want to delete this project? This will permanently erase all screenplay, shot lists, and storyboards.")) {
      try {
        await api.deleteProject(id);
        setProjects(prev => prev.filter(p => p.id !== id));
      } catch (err) {
        console.error(err);
      }
    }
  };

  const handleRenameProject = (id: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setRenamingProject({ id, title: currentTitle });
  };

  const handleSaveRename = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renamingProject || !renamingProject.title.trim()) return;
    try {
      await api.updateProject(renamingProject.id, { title: renamingProject.title.trim() });
      setProjects(prev => prev.map(p => p.id === renamingProject.id ? { ...p, title: renamingProject.title.trim() } : p));
      setRenamingProject(null);
    } catch (err) {
      console.error(err);
    }
  };


  const handleDuplicateProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    try {
      const duplicated = await api.duplicateProject(id);
      setProjects(prev => [duplicated, ...prev]);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col text-gray-200">
      <Navbar />
      
      <div className="flex-1 max-w-6xl w-full mx-auto px-6 py-10 space-y-8">
        <div className="flex items-center justify-between border-b border-border/60 pb-6">
          <div className="text-left">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center space-x-2">
              <Video className="text-primary" size={24} />
              <span>Filmmaking Workspaces</span>
            </h1>
            <p className="text-xs text-gray-400 mt-1">Manage, outline, storyboard, and plan your cinema productions.</p>
          </div>
          
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center space-x-1.5 px-4 py-2 bg-primary text-black font-bold text-xs rounded hover:bg-primary/90 transition-colors cursor-pointer shadow-lg"
          >
            <Plus size={14} className="stroke-[2.5]" />
            <span>Create Workspace</span>
          </button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-44 bg-[#0d0d15]/40 border border-border/50 rounded-xl p-5 space-y-4 animate-pulse">
                <div className="w-1/3 h-4 bg-gray-800 rounded"></div>
                <div className="w-full h-8 bg-gray-800 rounded"></div>
                <div className="w-1/2 h-3 bg-gray-800 rounded"></div>
              </div>
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 border border-dashed border-border rounded-2xl bg-[#0d0d15]/10 space-y-4">
            <Film size={48} className="text-gray-700" />
            <div className="text-center">
              <h3 className="font-bold text-gray-300">No projects found</h3>
              <p className="text-xs text-gray-500 mt-1">Create your first workspace to start writing, planning, and storyboarding.</p>
            </div>
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 bg-secondary hover:bg-muted border border-border text-xs font-semibold rounded text-gray-300 hover:text-white transition-colors cursor-pointer animate-pulse"
            >
              Get Started
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {projects.map((proj) => {
              const formattedDate = new Date(proj.created_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
              });
              
              return (
                <Link
                  key={proj.id}
                  href={`/workspace/${proj.id}`}
                  className="group bg-[#0d0d15]/40 hover:bg-[#0d0d15]/80 border border-border/60 hover:border-primary/50 p-5 rounded-xl transition-all duration-150 flex flex-col text-left justify-between h-44 shadow-lg hover:shadow-primary/5"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between">
                      <h3 className="font-bold text-lg text-white group-hover:text-primary transition-colors line-clamp-1 screenplay-font">
                        {proj.title}
                      </h3>
                      
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={(e) => handleRenameProject(proj.id, proj.title, e)}
                          className="p-1 text-gray-600 hover:text-primary rounded hover:bg-primary/10 cursor-pointer transition-colors"
                          title="Rename project"
                        >
                          <Edit2 size={12} />
                        </button>
                        
                        <button
                          onClick={(e) => handleDuplicateProject(proj.id, e)}
                          className="p-1 text-gray-600 hover:text-green-500 rounded hover:bg-green-500/10 cursor-pointer transition-colors"
                          title="Duplicate project"
                        >
                          <Copy size={12} />
                        </button>

                        <button
                          onClick={(e) => handleDeleteProject(proj.id, e)}
                          className="p-1 text-gray-600 hover:text-red-500 rounded hover:bg-red-500/10 cursor-pointer transition-colors"
                          title="Delete project"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                    
                    <p className="text-xs text-gray-400 line-clamp-2 leading-relaxed">
                      {proj.logline || "No logline specified. Generate story outline using Gemini inside."}
                    </p>
                  </div>
                  
                  <div className="flex items-center justify-between text-[10px] text-gray-500 pt-4 border-t border-border/20">
                    <span className="flex items-center space-x-1">
                      <Calendar size={10} />
                      <span>{formattedDate}</span>
                    </span>
                    
                    {proj.premise && (
                      <span className="flex items-center space-x-0.5 px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 text-[9px] font-bold">
                        <Sparkles size={8} />
                        <span>OUTLINED</span>
                      </span>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/85 flex items-center justify-center z-50 p-4 backdrop-blur-sm animate-fade-in">
          <form 
            onSubmit={handleCreateProject}
            className="glass max-w-md w-full rounded-xl overflow-hidden shadow-2xl border border-border flex flex-col"
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-[#0a0a0f]">
              <h3 className="font-bold text-gray-200 text-sm uppercase tracking-wider">New Filmmaking Workspace</h3>
              <button 
                type="button"
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-white cursor-pointer"
              >
                <Plus className="rotate-45" size={18} />
              </button>
            </div>
            
            <div className="p-6 space-y-4 text-left">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Project Title</label>
                <input 
                  type="text" 
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. The Quantum Paradox" 
                  required
                  className="w-full bg-input border border-border rounded-md px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-primary placeholder-gray-600"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Logline / Concept</label>
                <textarea 
                  value={logline}
                  onChange={(e) => setLogline(e.target.value)}
                  placeholder="A brief one-sentence summary of the story's core hook..." 
                  className="w-full bg-input border border-border rounded-md px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-primary placeholder-gray-600 h-20 resize-none"
                />
              </div>
            </div>

            <div className="px-6 py-3 border-t border-border bg-[#0a0a0f] flex justify-end space-x-2">
              <button 
                type="button"
                onClick={() => setShowModal(false)}
                className="px-4 py-1.5 rounded bg-secondary hover:bg-muted border border-border text-gray-300 hover:text-white font-semibold text-xs transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button 
                type="submit"
                disabled={isCreating || !title.trim()}
                className="px-4 py-1.5 rounded bg-primary text-black font-bold text-xs hover:bg-primary/95 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed transition-colors cursor-pointer"
              >
                {isCreating ? "Initializing..." : "Create Workspace"}
              </button>
            </div>
          </form>
        </div>
      )}

      {renamingProject && (
        <div className="fixed inset-0 bg-black/85 flex items-center justify-center z-50 p-4 backdrop-blur-sm animate-fade-in">
          <form 
            onSubmit={handleSaveRename}
            className="glass max-w-sm w-full rounded-xl overflow-hidden shadow-2xl border border-border flex flex-col bg-background/90"
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-[#0a0a0f]">
              <h3 className="font-bold text-gray-200 text-xs uppercase tracking-wider">Rename Workspace</h3>
              <button 
                type="button"
                onClick={() => setRenamingProject(null)}
                className="text-gray-400 hover:text-white cursor-pointer"
              >
                <Plus className="rotate-45" size={18} />
              </button>
            </div>
            
            <div className="p-6 space-y-4 text-left">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">New Project Title</label>
                <input 
                  type="text" 
                  value={renamingProject.title}
                  onChange={(e) => setRenamingProject({ ...renamingProject, title: e.target.value })}
                  placeholder="Enter new workspace title..." 
                  required
                  className="w-full bg-input border border-border rounded-md px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-primary placeholder-gray-600"
                />
              </div>
            </div>

            <div className="px-6 py-3 border-t border-border bg-[#0a0a0f] flex justify-end space-x-2">
              <button 
                type="button"
                onClick={() => setRenamingProject(null)}
                className="px-4 py-1.5 rounded bg-secondary hover:bg-muted border border-border text-gray-300 hover:text-white font-semibold text-xs transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button 
                type="submit"
                disabled={!renamingProject.title.trim()}
                className="px-4 py-1.5 rounded bg-primary text-black font-bold text-xs hover:bg-primary/95 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed transition-colors cursor-pointer"
              >
                Save Title
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

