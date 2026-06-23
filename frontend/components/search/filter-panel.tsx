'use client';

import React from 'react';

interface FilterPanelProps {
  activeTag: string;
  onTagChange: (tag: string) => void;
}

export function FilterPanel({ activeTag, onTagChange }: FilterPanelProps) {
  const tags = ['All', 'Hospital', 'Fight', 'Dream', 'Flashback'];

  return (
    <div className="flex space-x-1.5 overflow-x-auto pb-1 text-[10px]">
      {tags.map((tag) => (
        <button
          key={tag}
          onClick={() => onTagChange(tag)}
          className={`px-2.5 py-0.5 rounded-full transition-all cursor-pointer border ${
            activeTag === tag
              ? 'bg-amber-500 text-black font-bold border-amber-500'
              : 'border-white/5 bg-white/5 text-gray-400 hover:text-gray-200'
          }`}
        >
          {tag}
        </button>
      ))}
    </div>
  );
}
export default FilterPanel;
