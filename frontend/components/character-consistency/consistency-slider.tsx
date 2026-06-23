'use client';

import React, { useState } from 'react';
import { Sparkles } from 'lucide-react';

interface ConsistencySliderProps {
  onStrengthChange: (val: number) => void;
}

export function ConsistencySlider({ onStrengthChange }: ConsistencySliderProps) {
  const [val, setVal] = useState(0.7);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const nextVal = parseFloat(e.target.value);
    setVal(nextVal);
    onStrengthChange(nextVal);
  };

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-[#0a0a14] space-y-3 text-xs text-gray-300">
      <div className="flex justify-between items-center">
        <span className="font-semibold text-gray-400">Lock Consistency Strength</span>
        <span className="font-mono text-amber-500 font-bold">{Math.round(val * 100)}%</span>
      </div>

      <div className="flex items-center space-x-3">
        <input 
          type="range"
          min="0.1"
          max="1.0"
          step="0.05"
          value={val}
          onChange={handleChange}
          className="flex-grow h-1.5 bg-black/60 rounded-lg appearance-none cursor-pointer accent-amber-500"
        />
      </div>

      <p className="text-[10px] text-gray-500 italic leading-normal">
        * Higher percentages lock landmarks closely to the reference image, but restrict prompt text creativity. Recommended: 0.70.
      </p>
    </div>
  );
}
export default ConsistencySlider;
