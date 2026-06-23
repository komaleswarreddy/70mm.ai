'use client';

import React, { useEffect, useState } from 'react';
import { FileText, Save } from 'lucide-react';
import { Scene } from '../lib/api';

interface ScriptEditorProps {
  scene?: Scene;
  onSaveScript: (content: string) => void;
  isSaving: boolean;
}

export function ScriptEditor({ scene, onSaveScript, isSaving }: ScriptEditorProps) {
  const [content, setContent] = useState('');

  useEffect(() => {
    if (scene) {
      setContent(scene.raw_content || '');
    } else {
      setContent('');
    }
  }, [scene]);

  if (!scene) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-500 bg-[#0b0b12] p-6 h-full">
        <FileText size={40} className="mb-3 text-gray-700" />
        <p className="text-sm font-semibold">Select a scene to view script</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0b0b12] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-[#0d0d15]/80">
        <span className="text-xs font-bold text-gray-300 uppercase screenplay-font">
          Scene {scene.scene_number} - Script Editor
        </span>
        <button
          onClick={() => onSaveScript(content)}
          disabled={isSaving}
          className="flex items-center space-x-1 px-2.5 py-1 rounded bg-primary text-black font-semibold text-xs hover:bg-primary/90 transition-colors cursor-pointer"
        >
          <Save size={12} />
          <span>{isSaving ? "Saving..." : "Save"}</span>
        </button>
      </div>

      {/* Editor Body */}
      <div className="flex-1 p-4 overflow-y-auto flex justify-center">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="INT. KITCHEN - DAY&#10;&#10;JOHN stands over the sink. He sighs deeply.&#10;&#10;JOHN&#10;It's over."
          className="w-full max-w-[7.5in] min-h-[9in] bg-white text-black p-10 screenplay-font text-sm leading-relaxed border border-border shadow-xl focus:outline-none resize-none overflow-y-visible"
        />
      </div>
    </div>
  );
}
