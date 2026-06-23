'use client';

import React, { useState } from 'react';
import { Palette, RefreshCw } from 'lucide-react';

export function Moodboard() {
  const [palette, setPalette] = useState<string[]>(["#0d0d1e", "#f59e0b", "#022c22", "#111827"]);

  const randomizePalette = () => {
    // Generate cinematic shades
    const colors = [
      ["#0a0a0f", "#3b82f6", "#1e3a8a", "#0f172a"], // Cold Sci-Fi
      ["#180808", "#ef4444", "#7f1d1d", "#111827"], // Noir Tension
      ["#052e16", "#10b981", "#064e3b", "#0f172a"], // Matrix Green
      ["#2d1500", "#f59e0b", "#78350f", "#0c0a09"]  // Warm Kubrick
    ];
    const pick = colors[Math.floor(Math.random() * colors.length)];
    setPalette(pick);
  };

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-[#0a0a14] space-y-3.5 text-xs text-gray-300">
      <div className="flex justify-between items-center border-b border-white/5 pb-2">
        <div className="flex items-center space-x-1.5">
          <Palette className="text-amber-500" size={14} />
          <span className="font-bold text-gray-200 uppercase tracking-wider">Cinematic Color Swatches</span>
        </div>
        <button
          onClick={randomizePalette}
          className="p-1 rounded hover:bg-white/5 text-gray-500 hover:text-white transition-colors cursor-pointer"
        >
          <RefreshCw size={11} />
        </button>
      </div>

      <div className="flex space-x-2">
        {palette.map((color, idx) => (
          <div key={idx} className="flex-1 flex flex-col items-center space-y-1">
            <div
              style={{ backgroundColor: color }}
              className="w-full aspect-[2/1] rounded border border-white/10"
            />
            <span className="font-mono text-[8px] text-gray-400">{color}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
export default Moodboard;
