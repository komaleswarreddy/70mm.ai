'use client';

import React, { useState } from 'react';
import { Monitor, Heart, Star, Sparkles, Check, ChevronRight, Eye, Film } from 'lucide-react';
import { Shot } from '../lib/api';

interface OptionAlternative {
  id: number;
  label: string;
  shot_size: string;
  angle: string;
  movement: string;
  lens: string;
  lighting: string;
  emotion: string;
  color_palette: string;
  visual_tip: string;
  thumbnail_placeholder: string;
}

interface DirectorMonitorProps {
  shot?: Shot;
  onApplyOption: (option: any) => void;
}

export function DirectorMonitor({ shot, onApplyOption }: DirectorMonitorProps) {
  const [favorites, setFavorites] = useState<number[]>([]);
  const [activeCompareOption, setActiveCompareOption] = useState<number | null>(null);

  // Generate 3 cinematic options dynamically based on shot details
  const alternatives: OptionAlternative[] = [
    {
      id: 1,
      label: "Option A: Classic Fincher Shadows",
      shot_size: "MCU (Medium Close Up)",
      angle: "Low Angle",
      movement: "Slow Track In",
      lens: "50mm Prime",
      lighting: "Low Key / High Contrast Chiaroscuro",
      emotion: "Paranoia / Tension",
      color_palette: "Cold Steel Blue & Warm Tungsten glows",
      visual_tip: "Frame key subject slightly off-center, letting deep shadows swallow the background details.",
      thumbnail_placeholder: "linear-gradient(135deg, #0d0d1e 0%, #1a102f 100%)"
    },
    {
      id: 2,
      label: "Option B: Dynamic Kubrick Symmetry",
      shot_size: "WS (Wide Shot)",
      angle: "Eye Level Centered",
      movement: "Static / Locked",
      lens: "24mm Wide Prime",
      lighting: "Symmetrical High Key / Soft Diffused ceiling panels",
      emotion: "Detachment / Isolation",
      color_palette: "Sterile white with single primary red highlight",
      visual_tip: "Employ strict one-point perspective converging perfectly on the center subject.",
      thumbnail_placeholder: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)"
    },
    {
      id: 3,
      label: "Option C: Scorsese Tracker",
      shot_size: "OTS (Over The Shoulder)",
      angle: "Dutch Tilt / Dynamic",
      movement: "Fast Steadicam Track",
      lens: "35mm Cine",
      lighting: "Volumetric neon backlighting, high fill shadows",
      emotion: "Exhilaration / Anxiety",
      color_palette: "Saturated emerald greens and neon magenta",
      visual_tip: "Incorporate foreground element depth blurring rapidly as camera tracks past.",
      thumbnail_placeholder: "linear-gradient(135deg, #022c22 0%, #111827 100%)"
    }
  ];

  const toggleFavorite = (id: number) => {
    setFavorites(prev =>
      prev.includes(id) ? prev.filter(fId => fId !== id) : [...prev, id]
    );
  };

  if (!shot) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-gray-500 h-full text-center">
        <Film size={24} className="text-gray-700 mb-2" />
        <p className="text-xs font-semibold">Select a shot to launch Director Monitor</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-[#05050a] text-xs text-gray-300 overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-border bg-[#0a0a14] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Monitor className="text-amber-500" size={14} />
          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
            Director Monitor (Shot #{shot.shot_number})
          </span>
        </div>
        <div className="flex items-center space-x-2 text-[9px] bg-white/5 px-2 py-0.5 rounded border border-white/5 text-amber-500 font-mono font-bold">
          <span>Compare Mode Active</span>
        </div>
      </div>

      {/* Main Grid comparing 3 alternatives */}
      <div className="flex-1 p-3 overflow-y-auto grid grid-cols-1 md:grid-cols-3 gap-3">
        {alternatives.map((opt) => (
          <div
            key={opt.id}
            onClick={() => setActiveCompareOption(opt.id)}
            className={`flex flex-col rounded-lg border transition-all duration-300 overflow-hidden cursor-pointer bg-[#0c0c16]/90 backdrop-blur-md relative ${
              activeCompareOption === opt.id
                ? 'border-amber-500/80 shadow-[0_0_15px_rgba(245,158,11,0.15)] scale-[1.01]'
                : 'border-white/5 hover:border-white/10 shadow-lg'
            }`}
          >
            {/* Aspect Ratio Screen Simulator */}
            <div
              style={{ background: opt.thumbnail_placeholder }}
              className="aspect-[2.35/1] relative flex items-center justify-center overflow-hidden border-b border-white/5"
            >
              {/* Rule of Thirds Guide lines */}
              <div className="absolute inset-0 grid grid-cols-3 pointer-events-none opacity-20">
                <div className="border-r border-white"></div>
                <div className="border-r border-white"></div>
              </div>
              <div className="absolute inset-0 grid grid-rows-3 pointer-events-none opacity-20">
                <div className="border-b border-white"></div>
                <div className="border-b border-white"></div>
              </div>

              {/* Glowing camera lens circle simulation */}
              <div className="w-10 h-10 rounded-full border border-amber-500/40 bg-amber-500/10 flex items-center justify-center animate-pulse">
                <Film size={14} className="text-amber-500/70" />
              </div>

              <span className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-black/60 text-[8px] font-bold text-gray-400 font-mono">
                {opt.lens}
              </span>
              <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/60 text-[8px] font-bold text-amber-500 font-mono">
                2.35:1
              </span>
            </div>

            {/* Content Details */}
            <div className="p-3 flex-1 flex flex-col justify-between space-y-3">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-gray-200 text-[11px] truncate max-w-[150px]">{opt.label}</h4>
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFavorite(opt.id);
                      }}
                      className="p-1 rounded hover:bg-white/5 text-gray-500 hover:text-red-400 transition-colors"
                    >
                      <Heart
                        size={12}
                        className={favorites.includes(opt.id) ? 'fill-red-500 text-red-500' : ''}
                      />
                    </button>
                  </div>
                </div>

                <div className="space-y-1 text-[10px] text-gray-400 leading-relaxed font-sans">
                  <div>
                    <span className="text-gray-600 font-mono text-[9px] uppercase tracking-wider block">Shot Size & Angle</span>
                    <span className="text-gray-300 font-semibold">{opt.shot_size} &mdash; {opt.angle}</span>
                  </div>
                  <div>
                    <span className="text-gray-600 font-mono text-[9px] uppercase tracking-wider block">Camera Movement</span>
                    <span className="text-gray-300">{opt.movement}</span>
                  </div>
                  <div>
                    <span className="text-gray-600 font-mono text-[9px] uppercase tracking-wider block">Lighting Atmosphere</span>
                    <span className="text-gray-300 text-amber-200/80">{opt.lighting}</span>
                  </div>
                  <div>
                    <span className="text-gray-600 font-mono text-[9px] uppercase tracking-wider block">Color Palette</span>
                    <span className="text-gray-300 font-mono text-[9px]">{opt.color_palette}</span>
                  </div>
                  <div className="bg-black/30 p-2 rounded border border-white/5 mt-1">
                    <span className="text-gray-600 font-mono text-[9px] uppercase tracking-wider block mb-0.5">Visual Tip</span>
                    <span className="text-[10px] text-gray-300 leading-normal italic">{opt.visual_tip}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onApplyOption({
                    shot_size: opt.shot_size,
                    angle: opt.angle,
                    movement: opt.movement,
                    lens: opt.lens,
                    lighting: opt.lighting,
                    emotion: opt.emotion,
                    color_palette: opt.color_palette,
                    visual_tip: opt.visual_tip
                  });
                }}
                className="w-full mt-2 flex items-center justify-center space-x-1 py-1.5 px-3 rounded bg-amber-500 hover:bg-amber-600 text-black font-bold transition-all shadow-md hover:scale-[1.02] cursor-pointer"
              >
                <Check size={11} />
                <span>Apply to Shot</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
