'use client';

import React, { useState } from 'react';
import { Search, Book, Sparkles, HelpCircle, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import { SourceCard } from './source-card';

interface RAGReference {
  book: string;
  author: string;
  chapter: string;
  page: number;
  text: string;
  score: number;
}

export function SemanticSearch() {
  const [query, setQuery] = useState('');
  const [references, setReferences] = useState<RAGReference[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const triggerSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);
    try {
      const response = await api.queryRAG(query);
      setReferences(response.results || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-[#0a0a14] space-y-4 text-xs text-gray-300">
      <div className="flex items-center space-x-1.5 border-b border-white/5 pb-2">
        <Book className="text-amber-500" size={14} />
        <span className="font-bold text-gray-200 uppercase tracking-wider">Cinematic RAG Vector Search</span>
      </div>

      <form onSubmit={triggerSearch} className="flex space-x-2">
        <input 
          type="text" 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search Blake Snyder, McKee, Truby..." 
          className="flex-1 bg-black/60 border border-white/10 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
        />
        <button
          type="submit"
          disabled={isSearching}
          className="px-3 rounded bg-amber-500 hover:bg-amber-600 text-black font-bold flex items-center space-x-1 cursor-pointer disabled:opacity-40 transition-all"
        >
          {isSearching ? <Loader2 className="animate-spin" size={12} /> : <span>Search</span>}
        </button>
      </form>

      <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
        {references.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center text-gray-600 space-y-1">
            <HelpCircle size={20} className="opacity-25" />
            <span>Search topics like 'debate beat' or '180 degree rules'.</span>
          </div>
        ) : (
          references.map((ref, idx) => (
            <SourceCard key={idx} reference={ref} />
          ))
        )}
      </div>
    </div>
  );
}
export default SemanticSearch;
