'use client';

import React from 'react';
import { User, ShieldCheck, Heart } from 'lucide-react';
import { Character } from '../../lib/api';

interface CharacterGalleryProps {
  characters: Character[];
  selectedCharacterId?: string;
  onSelectCharacter: (id: string) => void;
}

export function CharacterGallery({ characters, selectedCharacterId, onSelectCharacter }: CharacterGalleryProps) {
  return (
    <div className="p-4 rounded-xl border border-white/5 bg-[#0a0a14] space-y-3 text-xs text-gray-300">
      <div className="flex items-center space-x-1.5 border-b border-white/5 pb-2">
        <User className="text-primary" size={14} />
        <span className="font-bold text-gray-200 uppercase tracking-wider">Reference Character Bible Gallery</span>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        {characters.length === 0 ? (
          <div className="col-span-2 p-6 text-center text-gray-600">
            <span>No character cards found. Add to your bible to lock facial profiles.</span>
          </div>
        ) : (
          characters.map((char) => {
            const isSelected = selectedCharacterId === char.id;
            return (
              <div
                key={char.id}
                onClick={() => onSelectCharacter(char.id)}
                className={`p-2 rounded border transition-all cursor-pointer bg-[#0c0c16] flex flex-col space-y-1.5 relative ${
                  isSelected ? 'border-primary/80 ring-1 ring-primary/20 scale-[1.02]' : 'border-white/5 hover:border-white/10'
                }`}
              >
                <div className="aspect-[3/4] bg-black/40 rounded overflow-hidden flex items-center justify-center border border-white/5 relative">
                  {char.reference_image_url ? (
                    <img src={char.reference_image_url} alt={char.name} className="w-full h-full object-cover" />
                  ) : (
                    <User size={24} className="text-gray-700" />
                  )}
                  {isSelected && (
                    <div className="absolute bottom-1 right-1 p-0.5 rounded bg-black/75 text-emerald-400">
                      <ShieldCheck size={11} />
                    </div>
                  )}
                </div>
                <div className="space-y-0.5">
                  <span className="font-bold text-gray-200 block truncate">{char.name}</span>
                  <span className="text-[9px] text-gray-600 block truncate capitalize">{char.personality || "Actor"}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
export default CharacterGallery;
