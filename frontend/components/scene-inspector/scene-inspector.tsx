'use client';

import React, { useState } from 'react';
import { X, Sparkles, Wand2, Eye, LayoutGrid } from 'lucide-react';

interface SceneInspectorProps {
  isOpen: boolean;
  onClose: () => void;
  sceneHeading: string;
  formulationData: {
    emotional_subtext: string;
    alternative_ideas: string[];
    visual_metaphors: string[];
    conflict_suggestions: string[];
    character_actions: string[];
  } | null;
}

export function SceneInspector({ isOpen, onClose, sceneHeading, formulationData }: SceneInspectorProps) {
  const [activeTab, setActiveTab] = useState<'variations' | 'metaphors' | 'subtext'>('variations');

  if (!isOpen || !formulationData) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-96 bg-[#07070c] border-l border-border/80 shadow-[0_0_35px_rgba(0,0,0,0.8)] flex flex-col animate-slide-in select-none">
      
      {/* Drawer Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-[#0a0a10]">
        <div className="flex items-center space-x-2">
          <Sparkles className="text-amber-500 animate-pulse" size={16} />
          <span className="font-bold text-gray-200 uppercase tracking-wider text-xs">Scene formulation</span>
        </div>
        <button 
          onClick={onClose}
          className="text-gray-400 hover:text-white p-1 rounded-full hover:bg-secondary transition-colors cursor-pointer"
          title="Close panel"
        >
          <X size={16} />
        </button>
      </div>

      {/* Target Scene Title info */}
      <div className="p-4 border-b border-border/40 bg-[#0d0d15]/30">
        <span className="text-[9px] font-bold text-amber-500 tracking-wider uppercase block">Target Heading</span>
        <h4 className="text-xs font-bold leading-tight text-white screenplay-font mt-0.5 line-clamp-1">{sceneHeading}</h4>
      </div>

      {/* Tab Selectors */}
      <div className="flex border-b border-border bg-[#050508]/80 p-1">
        <button
          onClick={() => setActiveTab('variations')}
          className={`flex-1 py-2 text-[10px] font-bold uppercase tracking-wider rounded-md cursor-pointer transition-colors ${
            activeTab === 'variations' ? 'bg-secondary text-white' : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          Variations
        </button>
        <button
          onClick={() => setActiveTab('metaphors')}
          className={`flex-1 py-2 text-[10px] font-bold uppercase tracking-wider rounded-md cursor-pointer transition-colors ${
            activeTab === 'metaphors' ? 'bg-secondary text-white' : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          Metaphors
        </button>
        <button
          onClick={() => setActiveTab('subtext')}
          className={`flex-1 py-2 text-[10px] font-bold uppercase tracking-wider rounded-md cursor-pointer transition-colors ${
            activeTab === 'subtext' ? 'bg-secondary text-white' : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          Subtext
        </button>
      </div>

      {/* Drawer Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-left">
        
        {activeTab === 'variations' && (
          <div className="space-y-4 animate-fade-in">
            <div className="space-y-2">
              <h5 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center space-x-1">
                <Wand2 size={11} className="text-blue-400" />
                <span>Creative Alternative Angles</span>
              </h5>
              <div className="space-y-2">
                {formulationData.alternative_ideas?.map((idea, idx) => (
                  <p key={idx} className="text-xs text-gray-300 bg-[#0d0d15]/50 border border-border/80 p-3 rounded-lg leading-relaxed shadow-sm">
                    {idea}
                  </p>
                ))}
              </div>
            </div>

            <div className="space-y-2 border-t border-border/30 pt-3">
              <h5 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center space-x-1">
                <LayoutGrid size={11} className="text-orange-400" />
                <span>Conflict Escalations</span>
              </h5>
              <div className="space-y-2">
                {formulationData.conflict_suggestions?.map((item, idx) => (
                  <p key={idx} className="text-xs text-gray-300 bg-[#0d0d15]/50 border border-border/80 p-3 rounded-lg leading-relaxed shadow-sm">
                    {item}
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'metaphors' && (
          <div className="space-y-4 animate-fade-in">
            <div className="space-y-2">
              <h5 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest flex items-center space-x-1">
                <Eye size={11} className="text-purple-400" />
                <span>Visual Motifs & Metaphors</span>
              </h5>
              <div className="space-y-2">
                {formulationData.visual_metaphors?.map((meta, idx) => (
                  <p key={idx} className="text-xs text-gray-300 bg-[#0d0d15]/50 border border-border/80 p-3 rounded-lg leading-relaxed shadow-sm">
                    {meta}
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'subtext' && (
          <div className="space-y-4 animate-fade-in">
            <div className="space-y-1.5">
              <h5 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Psychological Subtext</h5>
              <p className="text-xs text-gray-200 bg-amber-500/5 border border-amber-500/25 p-3.5 rounded-lg leading-relaxed shadow-sm">
                {formulationData.emotional_subtext}
              </p>
            </div>

            <div className="space-y-2 border-t border-border/30 pt-3">
              <h5 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Subtle Character Actions</h5>
              <div className="space-y-2">
                {formulationData.character_actions?.map((act, idx) => (
                  <p key={idx} className="text-xs text-gray-300 bg-[#0d0d15]/50 border border-border/80 p-3 rounded-lg leading-relaxed shadow-sm font-medium">
                    {act}
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Drawer Footer */}
      <div className="p-4 border-t border-border bg-[#0a0a10] flex justify-end">
        <button 
          onClick={onClose}
          className="w-full py-2 rounded-lg bg-secondary hover:bg-muted border border-border font-bold text-xs text-gray-300 hover:text-white transition-colors cursor-pointer"
        >
          Dismiss Inspector
        </button>
      </div>

    </div>
  );
}
