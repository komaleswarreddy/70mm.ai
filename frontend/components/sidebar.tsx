'use client';

import React, { useState } from 'react';
import { Sparkles, Users, BookOpen, FileUp, ChevronDown, ChevronRight, Layers } from 'lucide-react';
import { Project, Character } from '../lib/api';
import { StoryOutlineTabs } from './story-engine/story-outline-tabs';
import { CharacterBible } from './character-bible/character-bible';
import { RelationshipGraph } from './relationship-graph/relationship-graph';

interface SidebarProps {
  project?: Project;
  onGenerateStory: (idea: string) => void;
  onUploadScript: (file: File) => void;
  isGeneratingStory: boolean;
  isUploadingScript: boolean;
  onRefreshProject?: () => void;
  onStructureProject?: () => Promise<void>;
  isStructuring?: boolean;
  onLockCharacterReference?: (characterId: string, files?: File[]) => Promise<Character | void>;
}

export function Sidebar({
  project,
  onGenerateStory,
  onUploadScript,
  isGeneratingStory,
  isUploadingScript,
  onRefreshProject = () => {},
  onStructureProject,
  isStructuring = false,
  onLockCharacterReference,
}: SidebarProps) {

  const [idea, setIdea] = useState('');
  const [expandedSection, setExpandedSection] = useState<'ai' | 'info' | 'characters' | null>('info');

  const toggleSection = (section: 'ai' | 'info' | 'characters') => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onUploadScript(e.target.files[0]);
    }
  };

  const parseJSON = (str?: string, fallback: any = []) => {
    if (!str) return fallback;
    try {
      return JSON.parse(str);
    } catch {
      return fallback;
    }
  };

  const beatSheet = parseJSON(project?.beat_sheet, []);

  return (
    <div className="w-80 bg-[#07070c] border-r border-border h-[calc(100vh-3.5rem)] flex flex-col z-40 overflow-y-auto">
      {/* Script Upload Section */}
      <div className="p-4 border-b border-border">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
          <BookOpen size={13} className="text-primary" />
          <span>Screenplay Source</span>
        </h3>
        
        <label className="flex flex-col items-center justify-center border border-dashed border-border hover:border-primary/50 bg-[#0d0d15]/50 rounded-lg p-6 cursor-pointer group transition-all duration-150">
          <FileUp size={24} className="text-gray-400 group-hover:text-primary group-hover:scale-105 transition-all mb-2" />
          <span className="text-xs font-semibold text-gray-300">
            {isUploadingScript ? "Parsing screenplay..." : "Upload Fountain / TXT / FDX"}
          </span>
          <span className="text-[10px] text-gray-500 mt-1">Single source of truth</span>
          <input
            type="file"
            accept=".txt,.fountain,.fdx"
            onChange={handleFileChange}
            disabled={isUploadingScript}
            className="hidden"
          />
        </label>

        {onStructureProject && (project?.scenes?.length || 0) > 0 && (
          <button
            onClick={onStructureProject}
            disabled={isStructuring}
            title="Stage 2: groups the parsed scenes into acts/sequences/beats"
            className="w-full mt-2 flex items-center justify-center space-x-1.5 py-2 bg-secondary hover:bg-muted disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed border border-border text-gray-300 hover:text-white font-bold text-xs rounded transition-colors cursor-pointer"
          >
            <Layers size={13} className={isStructuring ? "animate-pulse" : ""} />
            <span>{isStructuring ? "Structuring acts..." : "Structure Screenplay"}</span>
          </button>
        )}

        {(() => {
          const structure = parseJSON(project?.screenplay_structure, null);
          if (!structure?.acts?.length) return null;
          return (
            <div className="mt-3 space-y-2 max-h-56 overflow-y-auto pr-1">
              {structure.acts.map((act: any, actIdx: number) => (
                <div key={actIdx} className="bg-secondary/20 border border-border/50 rounded p-2">
                  <span className="text-[10px] font-bold text-primary">
                    Act {act.act_number}{act.title ? `: ${act.title}` : ''}
                  </span>
                  {(act.sequences || []).map((seq: any, seqIdx: number) => (
                    <div key={seqIdx} className="mt-1.5 pl-2 border-l border-border/60 space-y-1">
                      <p className="text-[9px] font-semibold text-gray-300">{seq.sequence_title}</p>
                      {(seq.beats || []).map((beat: any, beatIdx: number) => (
                        <p key={beatIdx} className="text-[9px] text-gray-500 leading-relaxed">
                          <span className="text-gray-400">{beat.beat_title}</span>
                          {beat.scene_numbers ? ` (Sc. ${beat.scene_numbers.join(', ')})` : ''}
                        </p>
                      ))}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          );
        })()}
      </div>

      {/* Accordion Panels */}
      
      {/* 1. Story Engine Panel */}
      <div className="border-b border-border">
        <button 
          onClick={() => toggleSection('ai')}
          className="w-full flex items-center justify-between p-4 font-semibold text-sm text-gray-200 hover:bg-secondary/40 transition-colors cursor-pointer"
        >
          <div className="flex items-center space-x-2">
            <Sparkles size={15} className="text-yellow-500" />
            <span>AI Story Engine</span>
          </div>
          {expandedSection === 'ai' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>

        {expandedSection === 'ai' && (
          <div className="p-4 pt-0 space-y-3">
            <textarea
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              placeholder="Enter a logline, premise or seed idea..."
              className="w-full h-24 bg-input border border-border rounded-md p-2.5 text-xs text-gray-200 focus:outline-none focus:border-primary placeholder-gray-600 resize-none"
            />
            <button
              onClick={() => {
                if (idea.trim()) onGenerateStory(idea);
              }}
              disabled={isGeneratingStory || !idea.trim()}
              className="w-full py-2 bg-yellow-600 hover:bg-yellow-500 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed text-black font-bold text-xs rounded transition-colors cursor-pointer"
            >
              {isGeneratingStory ? "Generating story outline..." : "Generate Story Details"}
            </button>
          </div>
        )}
      </div>

      {/* 2. Story Outline Info Panel */}
      <div className="border-b border-border">
        <button 
          onClick={() => toggleSection('info')}
          className="w-full flex items-center justify-between p-4 font-semibold text-sm text-gray-200 hover:bg-secondary/40 transition-colors cursor-pointer"
        >
          <div className="flex items-center space-x-2">
            <BookOpen size={15} className="text-blue-400" />
            <span>Story Outline</span>
          </div>
          {expandedSection === 'info' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>

        {expandedSection === 'info' && (
          <div className="p-4 pt-0 space-y-4">
            <StoryOutlineTabs project={project} />
            
            {beatSheet.length > 0 && (
              <div>
                <h4 className="text-[10px] uppercase tracking-wider text-gray-500 font-bold mb-2">Beat Sheet</h4>
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {beatSheet.map((beat: any, idx: number) => (
                    <div key={idx} className="bg-secondary/25 border border-border/50 p-2 rounded">
                      <span className="text-[9px] font-bold text-primary mr-1">#{beat.beat_number}</span>
                      <span className="text-[11px] font-bold text-gray-300">{beat.title}</span>
                      <p className="text-[10px] text-gray-400 mt-1">{beat.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

      </div>

      {/* 3. Cast & Characters Panel */}
      <div className="border-b border-border flex-1">
        <button 
          onClick={() => toggleSection('characters')}
          className="w-full flex items-center justify-between p-4 font-semibold text-sm text-gray-200 hover:bg-secondary/40 transition-colors cursor-pointer"
        >
          <div className="flex items-center space-x-2">
            <Users size={15} className="text-purple-400" />
            <span>Cast & Characters</span>
          </div>
          {expandedSection === 'characters' ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>

        {expandedSection === 'characters' && (
          <div className="p-4 pt-0">
            <CharacterBible
              projectId={project?.id || ''}
              characters={project?.characters || []}
              allCharacters={project?.characters || []}
              onRefresh={onRefreshProject}
              onLockReference={onLockCharacterReference}
            />
          </div>
        )}

      </div>
    </div>
  );
}
