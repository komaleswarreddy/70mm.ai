'use client';

import React, { useState } from 'react';
import { Eye, HelpCircle } from 'lucide-react';

export function CompositionOverlay() {
  const [activeGuide, setActiveGuide] = useState<'thirds' | 'diagonals' | 'golden'>('thirds');

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-[#0a0a14] space-y-4 text-xs text-gray-300">
      <div className="flex items-center justify-between border-b border-white/5 pb-2">
        <span className="font-bold text-gray-200 uppercase tracking-wider">Composition Overlay Grid</span>
        <div className="flex space-x-1 bg-black/40 p-0.5 rounded border border-white/5">
          {['thirds', 'diagonals', 'golden'].map((guide) => (
            <button
              key={guide}
              onClick={() => setActiveGuide(guide as any)}
              className={`px-2 py-0.5 rounded text-[10px] capitalize cursor-pointer transition-all ${
                activeGuide === guide ? 'bg-primary text-black font-semibold' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {guide}
            </button>
          ))}
        </div>
      </div>

      {/* Grid simulator screen */}
      <div className="relative aspect-[16/9] bg-[#0c0c16] rounded-lg overflow-hidden border border-white/10 flex items-center justify-center">
        
        {/* Aspect ratio frame letterbox */}
        <div className="absolute inset-x-0 top-0 h-4 bg-black/80"></div>
        <div className="absolute inset-x-0 bottom-0 h-4 bg-black/80"></div>

        {/* Rule of Thirds Guide lines */}
        {activeGuide === 'thirds' && (
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute inset-y-0 left-1/3 border-r border-amber-500/35"></div>
            <div className="absolute inset-y-0 left-2/3 border-r border-amber-500/35"></div>
            <div className="absolute inset-x-0 top-1/3 border-b border-amber-500/35"></div>
            <div className="absolute inset-x-0 top-2/3 border-b border-amber-500/35"></div>
          </div>
        )}

        {/* Diagonals Guide lines */}
        {activeGuide === 'diagonals' && (
          <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-40" xmlns="http://www.w3.org/2000/svg">
            <line x1="0" y1="0" x2="100%" y2="100%" stroke="#f59e0b" strokeWidth="1" />
            <line x1="100%" y1="0" x2="0" y2="100%" stroke="#f59e0b" strokeWidth="1" />
          </svg>
        )}

        {/* Golden spiral approximation */}
        {activeGuide === 'golden' && (
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center opacity-30">
            <div className="w-24 h-24 rounded-full border border-amber-500"></div>
            <div className="w-12 h-12 rounded-full border border-amber-500"></div>
          </div>
        )}

        <span className="text-[10px] text-gray-500">Camera Composition Simulator</span>
      </div>
    </div>
  );
}
export default CompositionOverlay;
