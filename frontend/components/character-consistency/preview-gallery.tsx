'use client';

import React, { useState } from 'react';
import { Eye, RefreshCw, Layers } from 'lucide-react';

export function PreviewGallery() {
  const [activeCompare, setActiveCompare] = useState<'standard' | 'consistent'>('consistent');

  const beforeImage = "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&q=80"; // Standard face changes slightly
  const afterImage = "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&q=80";  // Locked consistent character look

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-[#0a0a14] space-y-4 text-xs text-gray-300">
      <div className="flex items-center justify-between border-b border-white/5 pb-2">
        <span className="font-bold text-gray-200 uppercase tracking-wider">Before / After Comparison</span>
        <div className="flex space-x-1 bg-black/40 p-0.5 rounded border border-white/5">
          <button 
            onClick={() => setActiveCompare('standard')}
            className={`px-2 py-0.5 rounded text-[10px] ${activeCompare === 'standard' ? 'bg-primary text-black font-semibold' : 'text-gray-400'}`}
          >
            Standard Flux
          </button>
          <button 
            onClick={() => setActiveCompare('consistent')}
            className={`px-2 py-0.5 rounded text-[10px] ${activeCompare === 'consistent' ? 'bg-primary text-black font-semibold' : 'text-gray-400'}`}
          >
            Consistent Locked
          </button>
        </div>
      </div>

      {/* Side-by-side or sliding comparison frames */}
      <div className="relative aspect-[16/9] bg-black rounded-lg overflow-hidden border border-white/10 flex items-center justify-center shadow-lg">
        <img 
          src={activeCompare === 'standard' ? beforeImage : afterImage} 
          alt="comparison print" 
          className="w-full h-full object-cover transition-all duration-300" 
        />
        
        {/* Glow badge indicatior */}
        <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-black/75 border border-white/5 text-[9px] font-mono flex items-center space-x-1">
          <Layers size={10} className="text-amber-500 animate-pulse" />
          <span>{activeCompare === 'standard' ? 'Variable Face Map' : 'InstantID Active (100%)'}</span>
        </div>
      </div>
    </div>
  );
}
export default PreviewGallery;
