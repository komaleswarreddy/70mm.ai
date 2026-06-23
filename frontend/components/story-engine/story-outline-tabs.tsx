'use client';

import React, { useState } from 'react';
import { Project } from '../../lib/api';
import { Sparkles, BookOpen, Layers, Target, Clapperboard, Compass } from 'lucide-react';

interface StoryOutlineTabsProps {
  project?: Project;
}

export function StoryOutlineTabs({ project }: StoryOutlineTabsProps) {
  const [activeTab, setActiveTab] = useState<'premise' | 'synopsis' | 'themes' | 'conflicts' | 'endings'>('premise');

  const parseJSON = (str?: string, fallback: any = {}) => {
    if (!str) return fallback;
    try {
      return JSON.parse(str);
    } catch {
      return fallback;
    }
  };

  const themes = parseJSON(project?.themes, []);
  const conflicts = parseJSON(project?.conflicts, { external: '', internal: '' });
  const endings = parseJSON(project?.endings, { commercial: '', art_house: '' });

  const tabs = [
    { id: 'premise', label: 'Premise', icon: Sparkles },
    { id: 'synopsis', label: 'Synopsis', icon: BookOpen },
    { id: 'themes', label: 'Themes', icon: Layers },
    { id: 'conflicts', label: 'Conflicts', icon: Target },
    { id: 'endings', label: 'Endings', icon: Clapperboard },
  ] as const;

  return (
    <div className="w-full bg-[#0a0a0f]/60 border border-border/80 rounded-xl overflow-hidden shadow-xl backdrop-blur-md">
      {/* Tab headers */}
      <div className="flex border-b border-border bg-[#050508]/80 p-1 overflow-x-auto scrollbar-none">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-1.5 px-4 py-2 text-xs font-semibold rounded-lg cursor-pointer transition-all duration-200 whitespace-nowrap ${
                isActive
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/25 shadow-[0_0_15px_rgba(245,158,11,0.05)]'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-secondary/40 border border-transparent'
              }`}
            >
              <Icon size={13} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab contents */}
      <div className="p-4 min-h-[140px] text-left">
        {activeTab === 'premise' && (
          <div className="space-y-2 animate-fade-in">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-500">Core Premise & Logline</h4>
            {project?.premise ? (
              <p className="text-xs text-gray-200 leading-relaxed bg-[#0d0d15]/50 border border-border p-3 rounded-lg screenplay-font">
                "{project.premise}"
              </p>
            ) : (
              <p className="text-xs text-gray-500 italic py-2">No premise outline generated yet. Trigger the Story Engine to construct details.</p>
            )}
          </div>
        )}

        {activeTab === 'synopsis' && (
          <div className="space-y-2 animate-fade-in">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-500">Narrative Synopsis</h4>
            {project?.synopsis ? (
              <div className="text-xs text-gray-200 leading-relaxed bg-[#0d0d15]/50 border border-border p-3 rounded-lg max-h-[180px] overflow-y-auto space-y-2">
                {project.synopsis.split('\n\n').map((para, i) => (
                  <p key={i}>{para}</p>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-500 italic py-2">No synopsis details outlined yet.</p>
            )}
          </div>
        )}

        {activeTab === 'themes' && (
          <div className="space-y-3 animate-fade-in">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-500">Explored Motifs & Themes</h4>
            {themes.length > 0 ? (
              <div className="flex flex-wrap gap-2 py-1">
                {themes.map((theme: string, idx: number) => (
                  <span
                    key={idx}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#0e0e16] border border-border/80 text-xs text-gray-300 shadow-sm"
                  >
                    <Compass size={11} className="text-amber-500" />
                    <span>{theme}</span>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-500 italic py-2">No themes categorized yet.</p>
            )}
          </div>
        )}

        {activeTab === 'conflicts' && (
          <div className="space-y-3 animate-fade-in">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <h5 className="text-[9px] font-bold uppercase tracking-widest text-amber-500/70">External Friction</h5>
                <div className="text-xs text-gray-300 bg-[#0d0d15]/50 border border-border p-2.5 rounded-lg leading-relaxed min-h-[60px]">
                  {conflicts.external || 'No external conflict specified.'}
                </div>
              </div>
              <div className="space-y-1.5">
                <h5 className="text-[9px] font-bold uppercase tracking-widest text-blue-400/70">Internal Turmoil</h5>
                <div className="text-xs text-gray-300 bg-[#0d0d15]/50 border border-border p-2.5 rounded-lg leading-relaxed min-h-[60px]">
                  {conflicts.internal || 'No internal conflict specified.'}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'endings' && (
          <div className="space-y-3 animate-fade-in">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5 border-r border-border/20 pr-2">
                <h5 className="text-[9px] font-bold uppercase tracking-widest text-amber-500/80">Commercial Endings</h5>
                <p className="text-xs text-gray-300 bg-[#0d0d15]/30 p-2 rounded leading-relaxed min-h-[60px]">
                  {endings.commercial || 'Blockbuster resolution details not outlined.'}
                </p>
              </div>
              <div className="space-y-1.5">
                <h5 className="text-[9px] font-bold uppercase tracking-widest text-purple-400/80">Art-House Resolution</h5>
                <p className="text-xs text-gray-300 bg-[#0d0d15]/30 p-2 rounded leading-relaxed min-h-[60px]">
                  {endings.art_house || 'Artistic/open-ended resolution details not outlined.'}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
