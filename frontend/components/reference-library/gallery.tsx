'use client';

import React, { useState } from 'react';
import { Image as ImageIcon, Heart, FolderOpen, Tag } from 'lucide-react';
import { ReferenceCard } from './reference-card';

interface LibraryAsset {
  id: string;
  url: string;
  category: string;
  tags: string[];
  favorite: boolean;
}

export function Gallery() {
  const [assets, setAssets] = useState<LibraryAsset[]>([
    { id: "lib-1", url: "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=400&q=80", category: "Color Palettes", tags: ["neon", "cyberpunk"], favorite: true },
    { id: "lib-2", url: "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=400&q=80", category: "Lens References", tags: ["ots", "anamorphic"], favorite: false }
  ]);

  const toggleFav = (id: string) => {
    setAssets(prev => prev.map(a => a.id === id ? { ...a, favorite: !a.favorite } : a));
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center text-[10px] text-gray-500 uppercase tracking-wider border-b border-white/5 pb-1">
        <span>Asset References Gallery</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {assets.map((asset) => (
          <ReferenceCard 
            key={asset.id} 
            url={asset.url} 
            category={asset.category} 
            tags={asset.tags} 
            favorite={asset.favorite} 
            onToggleFavorite={() => toggleFav(asset.id)}
          />
        ))}
      </div>
    </div>
  );
}
export default Gallery;
