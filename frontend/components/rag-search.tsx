'use client';

import React, { useState } from 'react';
import { Search, BookOpen, Upload, FileText, Sparkles, HelpCircle, Loader2 } from 'lucide-react';
import { api } from '../lib/api';

interface RAGResult {
  title: string;
  author: string;
  content: string;
  category: string;
  score: number;
}

interface RAGSearchProps {
  projectId: string;
}

export function RAGSearch({ projectId }: RAGSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<RAGResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);
    try {
      const response = await api.queryRAG(query, projectId);
      setResults(response.results || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setUploadMessage('');
    try {
      await api.uploadRAGDocument(projectId, file);
      setUploadMessage(`Indexed "${file.name}" successfully!`);
    } catch (err) {
      console.error(err);
      setUploadMessage('Failed indexing document.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07070c] border-l border-border overflow-hidden text-xs text-gray-300">
      {/* Header */}
      <div className="p-3 border-b border-border bg-[#0d0d15]/80 flex items-center justify-between">
        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center space-x-1">
          <BookOpen size={12} className="text-amber-500" />
          <span>Cinematic RAG Engine</span>
        </span>
        
        {/* Quick upload input */}
        <label className="flex items-center space-x-1 px-2.5 py-1 rounded border border-white/5 bg-white/5 hover:bg-white/10 transition-colors cursor-pointer">
          {isUploading ? (
            <Loader2 className="animate-spin text-amber-500" size={11} />
          ) : (
            <Upload size={11} className="text-amber-500" />
          )}
          <span>{isUploading ? 'Uploading...' : 'Upload Reference'}</span>
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={handleFileUpload}
            className="hidden"
            disabled={isUploading}
          />
        </label>
      </div>

      {/* Main Search Panel */}
      <div className="p-3 border-b border-border bg-black/20">
        <form onSubmit={handleSearch} className="flex space-x-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Query McKee, Save The Cat, Truby, or uploaded notes..."
              className="w-full bg-[#0d0d18] border border-border rounded px-2.5 py-1.5 pl-8 text-xs text-white focus:outline-none focus:border-amber-500 placeholder-gray-600"
            />
            <Search className="absolute left-2.5 top-2.5 text-gray-600" size={12} />
          </div>
          <button
            type="submit"
            disabled={isSearching}
            className="px-3 rounded bg-amber-500 hover:bg-amber-600 text-black font-bold transition-all flex items-center space-x-1 disabled:opacity-40 cursor-pointer"
          >
            {isSearching ? <Loader2 className="animate-spin" size={12} /> : <span>Ask Muse</span>}
          </button>
        </form>
        {uploadMessage && (
          <p className="text-[10px] text-amber-500 font-semibold mt-1.5">{uploadMessage}</p>
        )}
      </div>

      {/* RAG references results stream */}
      <div className="flex-1 p-3 overflow-y-auto space-y-3">
        {results.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 space-y-2 text-gray-500 text-center">
            <HelpCircle size={28} className="text-amber-500/20" />
            <p className="font-semibold text-gray-400">Ask screenplay structure questions</p>
            <p className="text-[10px] text-gray-600 max-w-[220px]">
              Query topics like: "How do I build tension in Act II?", "Catalyst beat sheet description", or "180 degree camera rules".
            </p>
          </div>
        ) : (
          results.map((res, idx) => (
            <div key={idx} className="p-3 rounded border border-white/5 bg-[#0d0d18] space-y-2 hover:border-amber-500/25 transition-all">
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-bold text-gray-200 text-xs">{res.title}</h4>
                  <span className="text-[10px] text-gray-500">by {res.author} &mdash; {res.category}</span>
                </div>
                <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 text-[9px] font-mono font-bold">
                  {Math.round(res.score * 100)}% Match
                </span>
              </div>
              <p className="text-gray-300 leading-relaxed text-[11px] font-sans bg-black/20 p-2.5 rounded border border-white/5">
                {res.content}
              </p>
              <div className="flex items-center space-x-1.5 text-[9px] text-gray-600">
                <Sparkles size={10} className="text-amber-500" />
                <span>Reference Source Verified</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
