'use client';

import React, { useState } from 'react';
import { Search, X } from 'lucide-react';
import { SearchResults } from './search-results';

export function GlobalSearch() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');

  return (
    <div className="relative text-xs text-gray-300">
      <button 
        onClick={() => setIsOpen(true)}
        className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-white/5 bg-[#0d0d15] hover:bg-white/5 transition-colors cursor-pointer text-gray-400 font-medium"
      >
        <Search size={12} />
        <span>Cross-Project Search...</span>
      </button>

      {isOpen && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="w-full max-w-2xl bg-[#07070c] rounded-xl border border-white/10 overflow-hidden flex flex-col max-h-[80vh] shadow-2xl relative">
            
            {/* Header search query input */}
            <div className="p-3 border-b border-border bg-[#0a0a14] flex items-center justify-between">
              <div className="flex items-center space-x-2 flex-1">
                <Search size={14} className="text-primary animate-pulse" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search scenes across all films (e.g. hospital scene)..."
                  className="bg-transparent border-0 outline-none text-white text-xs w-full"
                  autoFocus
                />
              </div>
              <button 
                onClick={() => {
                  setIsOpen(false);
                  setQuery('');
                }}
                className="text-gray-500 hover:text-white p-1 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Results Drawer */}
            <div className="flex-1 overflow-y-auto p-4">
              <SearchResults query={query} onClose={() => {
                setIsOpen(false);
                setQuery('');
              }} />
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
export default GlobalSearch;
