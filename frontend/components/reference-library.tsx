'use client';

import React, { useState } from 'react';
import { Upload, Mic, Image as ImageIcon, Heart, Folder, Palette, Play, Trash, Loader2 } from 'lucide-react';

interface VisualFrame {
  id: number;
  url: string;
  tags: string[];
  favorite: boolean;
  collection: string;
}

export function ReferenceLibrary() {
  const [activeTab, setActiveTab] = useState<'gallery' | 'multimodal'>('gallery');
  const [frames, setFrames] = useState<VisualFrame[]>([
    {
      id: 1,
      url: "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=400&q=80",
      tags: ["neon", "cyberpunk", "wide"],
      favorite: true,
      collection: "Sci-Fi Thriller"
    },
    {
      id: 2,
      url: "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=400&q=80",
      tags: ["vintage", "classic", "ots"],
      favorite: false,
      collection: "Noir Moodboard"
    }
  ]);

  // Multimodal states
  const [voiceText, setVoiceText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [extractedPalette, setExtractedPalette] = useState<string[]>([]);
  const [isExtractingPalette, setIsExtractingPalette] = useState(false);

  const startVoiceSim = () => {
    setIsRecording(true);
    setVoiceText('');
    setTimeout(() => {
      setIsRecording(false);
      setVoiceText("INT. BASEMENT - NIGHT\nVASU enters holding the old briefcase.\n\nVASU\nIt's all here. Every single file.");
    }, 2500);
  };

  const extractPaletteSim = () => {
    setIsExtractingPalette(true);
    setExtractedPalette([]);
    setTimeout(() => {
      setExtractedPalette(["#0d0d1e", "#f59e0b", "#022c22", "#111827"]);
      setIsExtractingPalette(false);
    }, 1200);
  };

  const toggleFavorite = (id: number) => {
    setFrames(prev => prev.map(f => f.id === id ? { ...f, favorite: !f.favorite } : f));
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07070c] border-l border-border overflow-hidden text-xs text-gray-300">
      {/* Tabs selectors */}
      <div className="p-3 border-b border-border bg-[#0d0d15]/80 flex items-center justify-between">
        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Visual Assets Library</span>
        <div className="flex space-x-1 bg-black/40 p-0.5 rounded border border-white/5">
          <button
            onClick={() => setActiveTab('gallery')}
            className={`flex items-center space-x-1 px-2.5 py-1 rounded transition-all cursor-pointer ${
              activeTab === 'gallery' ? 'bg-primary text-black font-semibold' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <ImageIcon size={11} />
            <span>Gallery</span>
          </button>
          <button
            onClick={() => setActiveTab('multimodal')}
            className={`flex items-center space-x-1 px-2.5 py-1 rounded transition-all cursor-pointer ${
              activeTab === 'multimodal' ? 'bg-primary text-black font-semibold' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Palette size={11} />
            <span>Multimodal Input</span>
          </button>
        </div>
      </div>

      <div className="flex-1 p-3 overflow-y-auto">
        {/* TAB 1: VISUAL REFERENCE GALLERY */}
        {activeTab === 'gallery' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center text-[10px] text-gray-500 uppercase tracking-wider border-b border-border pb-1">
              <span>Moodboards & Collections</span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {frames.map((frame) => (
                <div key={frame.id} className="group relative rounded-md border border-white/5 overflow-hidden bg-[#0c0c16]">
                  <img src={frame.url} alt="Reference Frame" className="w-full aspect-[16/9] object-cover bg-black" />
                  
                  {/* Overlay controls */}
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity p-2 flex flex-col justify-between">
                    <div className="flex justify-between items-center">
                      <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 text-[8px] font-mono">
                        {frame.collection}
                      </span>
                      <button
                        onClick={() => toggleFavorite(frame.id)}
                        className="p-1 rounded bg-black/40 hover:bg-black/60 text-gray-400 hover:text-red-400 transition-colors cursor-pointer"
                      >
                        <Heart size={12} className={frame.favorite ? 'fill-red-500 text-red-500' : ''} />
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {frame.tags.map(t => (
                        <span key={t} className="px-1 rounded bg-white/10 text-[8px] text-gray-300 font-mono">
                          #{t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 2: MULTIMODAL INPUT */}
        {activeTab === 'multimodal' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Voice note recorder section */}
            <div className="p-3 border border-white/5 bg-[#0d0d18] rounded-md space-y-3">
              <h4 className="font-bold text-gray-200 text-xs flex items-center space-x-1">
                <Mic size={13} className="text-red-500 animate-pulse" />
                <span>Voice to Screenplay Notes</span>
              </h4>
              <p className="text-[10px] text-gray-500 leading-normal">
                Record a voice memo explaining scene actions or dialogues. Antigravity AI translates to Fountain format.
              </p>
              
              <button
                onClick={startVoiceSim}
                disabled={isRecording}
                className={`w-full py-1.5 rounded flex items-center justify-center space-x-1.5 transition-all text-black font-bold shadow-md cursor-pointer ${
                  isRecording ? 'bg-red-600 animate-pulse text-white' : 'bg-red-500 hover:bg-red-600'
                }`}
              >
                {isRecording ? (
                  <>
                    <Loader2 className="animate-spin" size={12} />
                    <span>Listening & Parsing...</span>
                  </>
                ) : (
                  <>
                    <Mic size={12} fill="black" />
                    <span>Record Scene Memo</span>
                  </>
                )}
              </button>

              {voiceText && (
                <div className="p-2.5 rounded bg-black/40 border border-white/5 space-y-1.5">
                  <span className="text-[8px] font-mono text-gray-600 block uppercase">Parsed Fountain Output</span>
                  <pre className="font-mono text-[10px] text-emerald-400 whitespace-pre-wrap leading-relaxed">
                    {voiceText}
                  </pre>
                </div>
              )}
            </div>

            {/* Moodboard palette extractor */}
            <div className="p-3 border border-white/5 bg-[#0d0d18] rounded-md space-y-3">
              <h4 className="font-bold text-gray-200 text-xs flex items-center space-x-1">
                <Palette size={13} className="text-amber-500" />
                <span>Moodboard Palette Extractor</span>
              </h4>
              <p className="text-[10px] text-gray-500 leading-normal">
                Process reference imagery to generate dynamic hex color palettes matching the cinematography.
              </p>
              
              <button
                onClick={extractPaletteSim}
                disabled={isExtractingPalette}
                className="w-full py-1.5 rounded bg-amber-500 hover:bg-amber-600 text-black font-bold transition-all shadow-md cursor-pointer flex items-center justify-center space-x-1"
              >
                {isExtractingPalette ? (
                  <>
                    <Loader2 className="animate-spin" size={12} />
                    <span>Analyzing Image...</span>
                  </>
                ) : (
                  <>
                    <Palette size={12} />
                    <span>Extract Moodboard Colors</span>
                  </>
                )}
              </button>

              {extractedPalette.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[8px] font-mono text-gray-600 block uppercase">Extracted Palette Swatches</span>
                  <div className="flex space-x-2">
                    {extractedPalette.map((color, index) => (
                      <div key={index} className="flex-1 flex flex-col items-center space-y-1">
                        <div
                          style={{ backgroundColor: color }}
                          className="w-full aspect-[2/1] rounded border border-white/10"
                        />
                        <span className="font-mono text-[8px] text-gray-400">{color}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
export default ReferenceLibrary;
