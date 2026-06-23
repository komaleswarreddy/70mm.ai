'use client';

import React from 'react';
import { Heart } from 'lucide-react';

export function FavoritesPanel() {
  const favorites = [
    { title: "Shot 1.2 symmetrical hallway Wide Shot", category: "Kubrick Style" },
    { title: "Dune silhouette profile lighting", category: "Villeneuve Preset" }
  ];

  return (
    <div className="space-y-3.5">
      <div className="text-[10px] text-gray-500 uppercase tracking-wider border-b border-white/5 pb-1">
        <span>Cinematic Favorites Panel</span>
      </div>

      <div className="space-y-2">
        {favorites.map((fav, idx) => (
          <div key={idx} className="p-3 border border-white/5 bg-black/40 rounded-md hover:border-amber-500/25 transition-all cursor-pointer flex items-center justify-between">
            <div className="space-y-0.5">
              <span className="font-semibold text-gray-200 block">{fav.title}</span>
              <span className="text-[9px] text-amber-500/80 font-mono">{fav.category}</span>
            </div>
            <Heart className="fill-amber-500 text-amber-500 shrink-0" size={12} />
          </div>
        ))}
      </div>
    </div>
  );
}
export default FavoritesPanel;
