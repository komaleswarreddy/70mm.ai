'use client';

import React from 'react';
import { Heart, Tag } from 'lucide-react';

interface ReferenceCardProps {
  url: string;
  category: string;
  tags: string[];
  favorite: boolean;
  onToggleFavorite: () => void;
}

export function ReferenceCard({ url, category, tags, favorite, onToggleFavorite }: ReferenceCardProps) {
  return (
    <div className="group relative rounded-md border border-white/5 overflow-hidden bg-[#0c0c16]">
      <img src={url} alt="Reference visual card" className="w-full aspect-[16/9] object-cover bg-black" />
      <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity p-2 flex flex-col justify-between">
        <div className="flex justify-between items-center">
          <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 text-[8px] font-mono">
            {category}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleFavorite();
            }}
            className="p-1 rounded bg-black/40 hover:bg-black/60 text-gray-400 hover:text-red-400 transition-colors cursor-pointer"
          >
            <Heart size={12} className={favorite ? 'fill-red-500 text-red-500' : ''} />
          </button>
        </div>
        <div className="flex flex-wrap gap-1">
          {tags.map(t => (
            <span key={t} className="px-1 rounded bg-white/10 text-[8px] text-gray-300 font-mono flex items-center space-x-0.5">
              <Tag size={7} />
              <span>{t}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
export default ReferenceCard;
