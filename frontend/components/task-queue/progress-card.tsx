'use client';

import React from 'react';

interface ProgressCardProps {
  progress: number;
  status: 'running' | 'completed' | 'failed';
}

export function ProgressCard({ progress, status }: ProgressCardProps) {
  const getProgressBarColor = () => {
    if (status === 'completed') return 'bg-emerald-500';
    if (status === 'failed') return 'bg-red-500';
    return 'bg-amber-500';
  };

  return (
    <div className="space-y-1 w-full">
      <div className="w-full bg-black/60 h-1.5 rounded-full overflow-hidden border border-white/5">
        <div 
          style={{ width: `${progress}%` }} 
          className={`h-full rounded-full transition-all duration-300 ${getProgressBarColor()}`}
        />
      </div>
      <div className="flex justify-between text-[8px] font-mono text-gray-500">
        <span>Progress</span>
        <span>{progress}%</span>
      </div>
    </div>
  );
}
export default ProgressCard;
