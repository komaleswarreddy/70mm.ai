'use client';

import React from 'react';
import { Bookmark, Sparkles } from 'lucide-react';

interface RAGReference {
  book: string;
  author: string;
  chapter: string;
  page: number;
  text: string;
  score: number;
}

interface SourceCardProps {
  reference: RAGReference;
}

export function SourceCard({ reference }: SourceCardProps) {
  return (
    <div className="p-3 rounded border border-white/5 bg-black/40 space-y-2 hover:border-amber-500/25 transition-all">
      <div className="flex justify-between items-start text-[10px]">
        <div>
          <h5 className="font-bold text-gray-200 flex items-center space-x-1">
            <Bookmark size={11} className="text-amber-500 shrink-0" />
            <span>{reference.book}</span>
          </h5>
          <span className="text-[9px] text-gray-500">by {reference.author} &mdash; {reference.chapter}</span>
        </div>
        <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 text-[8px] font-mono font-bold">
          Page {reference.page}
        </span>
      </div>

      <p className="text-gray-300 leading-relaxed text-[10px] font-sans bg-black/20 p-2 rounded border border-white/5">
        "{reference.text}"
      </p>

      <div className="flex items-center space-x-1 text-[8px] text-gray-600 font-mono">
        <Sparkles size={9} className="text-amber-500" />
        <span>Vector Overlap Match Score: {Math.round(reference.score * 100)}%</span>
      </div>
    </div>
  );
}
export default SourceCard;
