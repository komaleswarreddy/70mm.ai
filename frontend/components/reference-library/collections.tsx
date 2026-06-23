'use client';

import React from 'react';
import { FolderOpen } from 'lucide-react';

export function Collections() {
  const folders = [
    { name: "Sci-Fi Cyberpunk Moodboard", count: 12 },
    { name: "Lenses & Aspect ratios reference", count: 6 },
    { name: "Fincher Style shadows LUTs", count: 8 }
  ];

  return (
    <div className="space-y-3.5">
      <div className="text-[10px] text-gray-500 uppercase tracking-wider border-b border-white/5 pb-1">
        <span>Visual Reference Collections</span>
      </div>

      <div className="space-y-2">
        {folders.map((f, idx) => (
          <div key={idx} className="p-3 border border-white/5 bg-black/40 rounded-md hover:border-amber-500/25 transition-all cursor-pointer flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <FolderOpen className="text-amber-500" size={13} />
              <span className="font-semibold text-gray-200">{f.name}</span>
            </div>
            <span className="px-2 py-0.5 rounded bg-black/60 text-[9px] font-mono text-gray-500">
              {f.count} items
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
export default Collections;
