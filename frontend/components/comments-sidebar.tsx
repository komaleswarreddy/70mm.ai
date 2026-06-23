'use client';

import React, { useState, useEffect } from 'react';
import { MessageSquare, Plus, Trash, User, Sparkles, Loader2 } from 'lucide-react';
import { api, CollaboratorComment } from '../lib/api';

interface CommentsSidebarProps {
  projectId: string;
  sceneId?: string;
}

export function CommentsSidebar({ projectId, sceneId }: CommentsSidebarProps) {
  const [comments, setComments] = useState<CollaboratorComment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [selectedUser, setSelectedUser] = useState('Vasu (Director)');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (projectId) {
      loadComments();
    }
  }, [projectId]);

  const loadComments = async () => {
    setIsLoading(true);
    try {
      const list = await api.getComments(projectId);
      setComments(list || []);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePostComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    
    // Parse role and name from dropdown value
    const parts = selectedUser.split(' (');
    const name = parts[0];
    const role = parts[1].replace(')', '');

    try {
      await api.createComment(projectId, {
        scene_id: sceneId,
        user_name: name,
        role: role,
        content: newComment
      });
      setNewComment('');
      await loadComments();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteComment = async (id: string) => {
    try {
      await api.deleteComment(id);
      await loadComments();
    } catch (err) {
      console.error(err);
    }
  };

  // Filter comments for active scene if present
  const displayedComments = sceneId 
    ? comments.filter(c => !c.scene_id || c.scene_id === sceneId)
    : comments;

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07070c] border-l border-border overflow-hidden text-xs text-gray-300">
      {/* Header */}
      <div className="p-3 border-b border-border bg-[#0d0d15]/80 flex items-center justify-between">
        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center space-x-1">
          <MessageSquare size={12} className="text-primary" />
          <span>Comments & Collaboration</span>
        </span>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="animate-spin text-primary" size={24} />
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-between overflow-hidden">
          {/* Comments Stream */}
          <div className="flex-1 p-3 overflow-y-auto space-y-3">
            {displayedComments.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 space-y-1.5 text-gray-600 text-center">
                <MessageSquare size={24} className="opacity-10" />
                <span>No comments posted. Start the conversation.</span>
              </div>
            ) : (
              displayedComments.map((c) => (
                <div key={c.id} className="p-2.5 rounded border border-white/5 bg-[#0c0c16] space-y-1.5 hover:border-white/10 transition-all relative group">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center space-x-2">
                      <div className="w-5 h-5 rounded-full bg-white/5 flex items-center justify-center">
                        <User size={10} className="text-gray-400" />
                      </div>
                      <div>
                        <span className="font-bold text-gray-200">{c.user_name}</span>
                        <span className="text-[8px] bg-white/5 text-amber-500 font-mono px-1 rounded ml-1.5">
                          {c.role}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteComment(c.id)}
                      className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-gray-600 hover:text-red-400 transition-opacity cursor-pointer absolute top-2 right-2"
                    >
                      <Trash size={11} />
                    </button>
                  </div>
                  <p className="text-gray-300 pl-7 text-[11px] leading-normal font-sans">{c.content}</p>
                </div>
              ))
            )}
          </div>

          {/* Post Comment Input Panel */}
          <div className="p-3 border-t border-border bg-[#0d0d15]/50">
            <form onSubmit={handlePostComment} className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[9px] text-gray-500 uppercase">Comment As:</span>
                <select
                  value={selectedUser}
                  onChange={(e) => setSelectedUser(e.target.value)}
                  className="bg-black/50 border border-border rounded px-1.5 py-0.5 text-[9px] text-amber-500 font-mono focus:outline-none"
                >
                  <option>Vasu (Director)</option>
                  <option>Sarah (Writer)</option>
                  <option>James (Cinematographer)</option>
                  <option>Elena (Producer)</option>
                </select>
              </div>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Post comment, use @name to mention..."
                  className="flex-1 bg-[#0d0d18] border border-border rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-primary placeholder-gray-600"
                />
                <button
                  type="submit"
                  className="px-3 rounded bg-primary text-black font-bold hover:bg-primary/90 transition-all flex items-center justify-center cursor-pointer"
                >
                  <Plus size={13} />
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
