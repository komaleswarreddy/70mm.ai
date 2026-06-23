'use client';

import React, { useState } from 'react';
import { Scene } from '../../lib/api';
import { ChevronDown, ChevronUp, Layers, Milestone } from 'lucide-react';

interface StoryTimelineProps {
  scenes: Scene[];
  selectedSceneId?: string;
  onSelectScene: (scene: Scene) => void;
}

export function StoryTimeline({ scenes = [], selectedSceneId, onSelectScene }: StoryTimelineProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (scenes.length === 0) return null;

  // Partition scenes into Acts based on index
  const act1Limit = Math.max(1, Math.floor(scenes.length * 0.25));
  const act2Limit = Math.max(act1Limit + 1, Math.floor(scenes.length * 0.75));

  const act1Scenes = scenes.slice(0, act1Limit);
  const act2Scenes = scenes.slice(act1Limit, act2Limit);
  const act3Scenes = scenes.slice(act2Limit);

  const actGroups = [
    { name: 'Act I: Setup', scenes: act1Scenes, color: 'border-blue-500/20 bg-blue-500/5 hover:border-blue-500/40 text-blue-400' },
    { name: 'Act II: Confrontation', scenes: act2Scenes, color: 'border-purple-500/20 bg-purple-500/5 hover:border-purple-500/40 text-purple-400' },
    { name: 'Act III: Resolution', scenes: act3Scenes, color: 'border-orange-500/20 bg-orange-500/5 hover:border-orange-500/40 text-orange-400' },
  ];

  return (
    <div className="bg-[#050508]/90 border-t border-border shadow-lg backdrop-blur-md transition-all duration-200">
      {/* Timeline Toggle Bar */}
      <div 
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="px-4 py-2 border-b border-border/40 flex items-center justify-between cursor-pointer hover:bg-secondary/20 transition-colors select-none"
      >
        <div className="flex items-center space-x-2">
          <Layers size={13} className="text-amber-500" />
          <span className="text-[10px] font-extrabold uppercase tracking-widest text-gray-400">Cinematic Act Timeline</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[9px] text-gray-500 uppercase font-medium">{scenes.length} Scenes mapped</span>
          {isCollapsed ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
        </div>
      </div>

      {/* Timeline Track (horizontal scrollable) */}
      {!isCollapsed && (
        <div className="p-4 overflow-x-auto flex space-x-6 min-h-[110px] scrollbar-thin select-none">
          {actGroups.map((group, gIdx) => {
            if (group.scenes.length === 0) return null;
            return (
              <div key={gIdx} className="flex flex-col space-y-2 shrink-0">
                <div className="flex items-center space-x-1.5 px-1">
                  <Milestone size={10} className={group.color.split(' ')[2]} />
                  <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">{group.name}</span>
                </div>
                
                <div className="flex space-x-3 items-stretch">
                  {group.scenes.map((scene) => {
                    const isSelected = scene.id === selectedSceneId;
                    return (
                      <div
                        key={scene.id}
                        onClick={() => onSelectScene(scene)}
                        className={`w-36 p-2.5 rounded-lg border text-left cursor-pointer transition-all duration-150 flex flex-col justify-between select-none ${
                          isSelected
                            ? 'bg-amber-500/10 border-amber-500 text-white shadow-[0_0_10px_rgba(245,158,11,0.1)]'
                            : `bg-[#0d0d15]/40 border-border/80 text-gray-300 hover:border-gray-700`
                        }`}
                      >
                        <div className="space-y-1">
                          <span className={`text-[8px] font-extrabold uppercase tracking-widest block ${isSelected ? 'text-amber-500' : 'text-gray-500'}`}>
                            Scene {scene.scene_number}
                          </span>
                          <h5 className="text-[10px] font-bold leading-tight line-clamp-2 screenplay-font text-gray-200">
                            {scene.heading}
                          </h5>
                        </div>
                        
                        <div className="flex items-center justify-between text-[8px] text-gray-500 pt-2 border-t border-border/10 mt-2">
                          <span>{scene.shots?.length || 0} Shots</span>
                          <span>Order {scene.order + 1}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
