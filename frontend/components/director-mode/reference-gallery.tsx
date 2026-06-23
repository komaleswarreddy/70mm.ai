'use client';

import React, { useState } from 'react';
import { Film, Compass, Heart } from 'lucide-react';

interface StillRef {
  id: number;
  movie: string;
  url: string;
  director: string;
  notes: string;
}

export function ReferenceGallery() {
  const [stills, setStills] = useState<StillRef[]>([
    {
      id: 1,
      movie: "Dune",
      director: "Villeneuve",
      url: "https://images.unsplash.com/photo-1547483238-f400e65ccd56?w=400&q=80",
      notes: "High contrast profile silhouettes representing character isolation."
    },
    {
      id: 2,
      movie: "Oppenheimer",
      director: "Nolan",
      url: "https://images.unsplash.com/photo-1440404653325-ab127d49abc1?w=400&q=80",
      notes: "Extreme close up camera capturing detailed facial micro expressions."
    }
  ]);

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-[#0a0a14] space-y-3.5 text-xs text-gray-300">
      <div className="flex items-center space-x-1.5 border-b border-white/5 pb-2">
        <Film className="text-amber-500" size={14} />
        <span className="font-bold text-gray-200 uppercase tracking-wider">Cinematography Movie Stills</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {stills.map((still) => (
          <div key={still.id} className="group relative rounded-md border border-white/5 overflow-hidden bg-[#0c0c16]">
            <img src={still.url} alt={still.movie} className="w-full aspect-[16/9] object-cover bg-black" />
            <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity p-2 flex flex-col justify-between">
              <div>
                <span className="font-bold text-gray-200 block">{still.movie}</span>
                <span className="text-[9px] text-amber-500 font-mono">Dir: {still.director}</span>
              </div>
              <p className="text-[9px] text-gray-400 italic leading-tight">{still.notes}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
export default ReferenceGallery;
