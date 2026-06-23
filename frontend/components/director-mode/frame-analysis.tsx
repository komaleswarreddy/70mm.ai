'use client';

import React, { useState } from 'react';
import { Camera, Compass, Layers } from 'lucide-react';

export function FrameAnalysis() {
  const [aspectRatio, setAspectRatio] = useState('2.35:1 Anamorphic');

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-[#0a0a14] space-y-3.5 text-xs text-gray-300">
      <div className="flex items-center space-x-1.5 border-b border-white/5 pb-2">
        <Camera className="text-amber-500" size={14} />
        <span className="font-bold text-gray-200 uppercase tracking-wider">Depth & Frame Analysis</span>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between items-center text-[10px]">
          <span className="text-gray-500 uppercase">Target Aspect Ratio</span>
          <select 
            value={aspectRatio}
            onChange={(e) => setAspectRatio(e.target.value)}
            className="bg-black/50 border border-white/5 rounded px-2 py-0.5 text-amber-500 font-mono focus:outline-none cursor-pointer"
          >
            <option>2.35:1 Anamorphic</option>
            <option>1.85:1 Academy Flat</option>
            <option>1.33:1 IMAX Classic</option>
          </select>
        </div>

        <div className="p-2.5 rounded bg-black/40 border border-white/5 space-y-1">
          <span className="font-bold text-gray-200 block">Foreground Depth Cue</span>
          <p className="text-gray-400 text-[10px] leading-normal">
            Position a blurry silhouette object (e.g. lamp, door frame) in the front third quadrant to establish volumetric depth layers.
          </p>
        </div>

        <div className="p-2.5 rounded bg-black/40 border border-white/5 space-y-1">
          <span className="font-bold text-gray-200 block">Leading Lines Suggestion</span>
          <p className="text-gray-400 text-[10px] leading-normal">
            Use ceiling struts or floor tracks converging towards the center right quadrant. Emphasizes character path.
          </p>
        </div>
      </div>
    </div>
  );
}
export default FrameAnalysis;
