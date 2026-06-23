'use client';

import React, { useState } from 'react';
import { Upload, Shield, ShieldCheck, HelpCircle } from 'lucide-react';

interface ReferencePanelProps {
  onConfigChange: (config: any) => void;
}

export function ReferencePanel({ onConfigChange }: ReferencePanelProps) {
  const [faceLock, setFaceLock] = useState(true);
  const [hairLock, setHairLock] = useState(false);
  const [costumeLock, setCostumeLock] = useState(false);
  const [refImage, setRefImage] = useState<string | null>(null);

  const updateConfig = (face: boolean, hair: boolean, costume: boolean, image: string | null) => {
    onConfigChange({
      face_lock: face,
      hair_lock: hair,
      costume_lock: costume,
      reference_image: image
    });
  };

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setRefImage(url);
      updateConfig(faceLock, hairLock, costumeLock, url);
    }
  };

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-[#0a0a14] space-y-4 text-xs text-gray-300">
      <div className="flex items-center space-x-1.5 border-b border-white/5 pb-2">
        <Shield className="text-amber-500 animate-pulse" size={14} />
        <span className="font-bold text-gray-200 uppercase tracking-wider">Character Lock Config</span>
      </div>

      {/* Upload area */}
      <div className="space-y-2">
        <span className="text-[10px] text-gray-500 uppercase tracking-wide block">Actor Reference Photo</span>
        {refImage ? (
          <div className="relative rounded overflow-hidden aspect-[3/4] border border-white/10 bg-black flex items-center justify-center">
            <img src={refImage} alt="Ref actor" className="w-full h-full object-cover" />
            <button 
              onClick={() => {
                setRefImage(null);
                updateConfig(faceLock, hairLock, costumeLock, null);
              }}
              className="absolute top-2 right-2 p-1 rounded bg-black/75 hover:bg-black text-gray-400 hover:text-white"
            >
              Clear
            </button>
          </div>
        ) : (
          <label className="flex flex-col items-center justify-center border border-dashed border-white/15 bg-black/40 hover:bg-black/60 rounded-lg p-6 cursor-pointer transition-colors text-center space-y-1">
            <Upload size={18} className="text-amber-500" />
            <span className="font-semibold text-gray-300">Select Image File</span>
            <span className="text-[9px] text-gray-600">Supports JPG, PNG</span>
            <input type="file" onChange={handleUpload} className="hidden" accept="image/*" />
          </label>
        )}
      </div>

      {/* Locks checkboxes */}
      <div className="space-y-2">
        <span className="text-[10px] text-gray-500 uppercase tracking-wide block">Consistency Locks</span>
        <div className="space-y-2">
          <label className="flex items-center justify-between p-2 rounded bg-black/40 border border-white/5 cursor-pointer hover:border-amber-500/25 transition-all">
            <div className="flex items-center space-x-2">
              <input 
                type="checkbox" 
                checked={faceLock}
                onChange={(e) => {
                  setFaceLock(e.target.checked);
                  updateConfig(e.target.checked, hairLock, costumeLock, refImage);
                }}
                className="accent-amber-500"
              />
              <span className="font-semibold text-gray-200">InstantID Face Lock</span>
            </div>
            <span className="text-[9px] text-gray-600">Landmarks</span>
          </label>

          <label className="flex items-center justify-between p-2 rounded bg-black/40 border border-white/5 cursor-pointer hover:border-amber-500/25 transition-all">
            <div className="flex items-center space-x-2">
              <input 
                type="checkbox" 
                checked={hairLock}
                onChange={(e) => {
                  setHairLock(e.target.checked);
                  updateConfig(faceLock, e.target.checked, costumeLock, refImage);
                }}
                className="accent-amber-500"
              />
              <span className="font-semibold text-gray-200">Preserve Hairstyle</span>
            </div>
            <span className="text-[9px] text-gray-600">IPAdapter</span>
          </label>

          <label className="flex items-center justify-between p-2 rounded bg-black/40 border border-white/5 cursor-pointer hover:border-amber-500/25 transition-all">
            <div className="flex items-center space-x-2">
              <input 
                type="checkbox" 
                checked={costumeLock}
                onChange={(e) => {
                  setCostumeLock(e.target.checked);
                  updateConfig(faceLock, hairLock, e.target.checked, refImage);
                }}
                className="accent-amber-500"
              />
              <span className="font-semibold text-gray-200">Costume / Wardrobe Lock</span>
            </div>
            <span className="text-[9px] text-gray-600">Unified Style</span>
          </label>
        </div>
      </div>
    </div>
  );
}
