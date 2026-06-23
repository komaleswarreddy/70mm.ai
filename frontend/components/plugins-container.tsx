'use client';

import React, { useState } from 'react';
import { Layers, Shield, Settings, Info, Loader2 } from 'lucide-react';

interface PluginMetadata {
  id: string;
  name: string;
  category: string;
  developer: string;
  description: string;
  sandboxUrl: string;
}

export function PluginsContainer() {
  const [activePlugin, setActivePlugin] = useState<PluginMetadata | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const pluginsList: PluginMetadata[] = [
    {
      id: "audio-mixer",
      name: "Dolby Atmos Sound Mixer Pro",
      category: "Audio",
      developer: "Dolby Labs",
      description: "Direct control over multitrack ambient film audio and spatial dialogues positioning.",
      sandboxUrl: "data:text/html;charset=utf-8," + encodeURIComponent(`
        <html>
          <style>
            body { background: #07070d; color: #a1a1aa; font-family: monospace; font-size: 11px; padding: 15px; margin: 0; }
            h2 { color: #f59e0b; font-size: 13px; margin-top: 0; }
            .mixer-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
            .slider { flex-grow: 1; margin: 0 10px; accent-color: #f59e0b; }
          </style>
          <body>
            <h2>Dolby Atmos Mixer</h2>
            <div class="mixer-row"><span>DIALOGUE</span><input type="range" class="slider" min="0" max="100" value="85"/><span>85%</span></div>
            <div class="mixer-row"><span>AMBIENT</span><input type="range" class="slider" min="0" max="100" value="40"/><span>40%</span></div>
            <div class="mixer-row"><span>MUSIC</span><input type="range" class="slider" min="0" max="100" value="65"/><span>65%</span></div>
            <div class="mixer-row"><span>LFE SUB</span><input type="range" class="slider" min="0" max="100" value="50"/><span>50%</span></div>
          </body>
        </html>
      `)
    },
    {
      id: "color-grader",
      name: "ACES Color Grading LUT Loader",
      category: "Color",
      developer: "Academy LUTs",
      description: "Applies cinematic LUT profiles directly into your storyboard thumbnails generation pipelines.",
      sandboxUrl: "data:text/html;charset=utf-8," + encodeURIComponent(`
        <html>
          <style>
            body { background: #07070d; color: #a1a1aa; font-family: monospace; font-size: 11px; padding: 15px; margin: 0; }
            h2 { color: #f59e0b; font-size: 13px; margin-top: 0; }
            .grade-btn { background: #1f2937; border: 1px solid #374151; color: white; padding: 5px 8px; border-radius: 4px; margin-right: 5px; cursor: pointer; }
            .grade-btn:hover { background: #f59e0b; color: black; }
          </style>
          <body>
            <h2>ACES LUT Importer</h2>
            <button class="grade-btn">Rec.709 Standard</button>
            <button class="grade-btn">Arri LogC Film</button>
            <button class="grade-btn">Teal & Orange</button>
          </body>
        </html>
      `)
    }
  ];

  const loadPlugin = (plugin: PluginMetadata) => {
    setIsLoading(true);
    setActivePlugin(plugin);
    setTimeout(() => {
      setIsLoading(false);
    }, 800);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07070c] border-l border-border overflow-hidden text-xs text-gray-300">
      {/* Header */}
      <div className="p-3 border-b border-border bg-[#0d0d15]/80 flex items-center justify-between">
        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center space-x-1.5">
          <Layers size={12} className="text-amber-500" />
          <span>Safe Plugin Ecosystem</span>
        </span>
      </div>

      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Left Side: Installed Plugins list */}
        <div className="w-full md:w-1/3 border-r border-border bg-black/10 overflow-y-auto p-3 space-y-2">
          <span className="text-[9px] text-gray-600 uppercase font-mono block mb-1">Available Extensions</span>
          {pluginsList.map((plug) => (
            <div
              key={plug.id}
              onClick={() => loadPlugin(plug)}
              className={`p-2.5 rounded border transition-all cursor-pointer ${
                activePlugin?.id === plug.id ? 'bg-[#0d0d18] border-amber-500/80 shadow' : 'border-white/5 bg-[#0c0c16]/70 hover:border-white/10'
              }`}
            >
              <div className="flex justify-between items-center mb-1">
                <span className="font-bold text-gray-200">{plug.name}</span>
              </div>
              <p className="text-[10px] text-gray-500 leading-normal mb-1">{plug.description}</p>
              <div className="flex justify-between text-[8px] text-gray-600 font-mono">
                <span>By {plug.developer}</span>
                <span className="text-amber-500">{plug.category}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Right Side: Isolated Sandboxed Iframe Container */}
        <div className="flex-grow flex flex-col bg-[#050508] relative">
          {!activePlugin ? (
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-gray-600 text-center space-y-2">
              <Shield size={28} className="opacity-10" />
              <span>Select a plugin from the list to launch in safe sandbox mode.</span>
            </div>
          ) : isLoading ? (
            <div className="flex-grow flex items-center justify-center bg-black/40">
              <Loader2 className="animate-spin text-primary" size={24} />
            </div>
          ) : (
            <div className="flex-grow flex flex-col overflow-hidden h-full">
              {/* Plugin Sandboxed sandbox stats bar */}
              <div className="p-2 border-b border-white/5 bg-black/30 flex items-center justify-between text-[9px] font-mono text-gray-500">
                <div className="flex items-center space-x-1.5">
                  <Shield size={10} className="text-emerald-500 animate-pulse" />
                  <span>Iframe Sandbox Isolated (allow-scripts)</span>
                </div>
                <span>Dev: {activePlugin.developer}</span>
              </div>
              <iframe
                sandbox="allow-scripts"
                src={activePlugin.sandboxUrl}
                className="flex-grow border-0 w-full h-full bg-[#07070d]"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
export default PluginsContainer;
