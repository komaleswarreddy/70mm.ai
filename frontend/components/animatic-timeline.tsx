'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, SkipForward, SkipBack, Video, Sparkles, Clock, Compass } from 'lucide-react';
import { Shot } from '../lib/api';

interface AnimaticTimelineProps {
  shots: Shot[];
}

export function AnimaticTimeline({ shots }: AnimaticTimelineProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [frameDurations, setFrameDurations] = useState<{ [shotId: string]: number }>({});
  const [cameraMovements, setCameraMovements] = useState<{ [shotId: string]: string }>({});
  
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const playTimerRef = useRef<NodeJS.Timeout | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Set up values
  const frames = shots.filter(s => s.storyboard_frames && s.storyboard_frames.length > 0);

  useEffect(() => {
    const durations: { [id: string]: number } = {};
    const movements: { [id: string]: string } = {};
    shots.forEach(s => {
      durations[s.id] = frameDurations[s.id] || 3; // default 3 seconds
      movements[s.id] = cameraMovements[s.id] || s.movement || 'Static';
    });
    setFrameDurations(durations);
    setCameraMovements(movements);
  }, [shots]);

  useEffect(() => {
    if (frames.length === 0 || currentFrameIndex >= frames.length) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const frame = frames[currentFrameIndex].storyboard_frames?.[0];
    const imageSrc = frame?.image_url || "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='450'><rect width='800' height='450' fill='%230b0b18'/><text x='50%' y='50%' font-size='20' fill='%23f59e0b' dominant-baseline='middle' text-anchor='middle'>STORYBOARD FRAME PLACEHOLDER</text></svg>";
    
    const img = new Image();
    img.src = imageSrc.startsWith('http') ? imageSrc : `http://localhost:8000${imageSrc}`;

    let startTime = Date.now();
    const durationMs = (frameDurations[frames[currentFrameIndex].id] || 3) * 1000;
    const movement = cameraMovements[frames[currentFrameIndex].id] || 'Static';

    const render = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / durationMs, 1.0);

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (img.complete) {
        ctx.save();
        
        let scale = 1.0;
        let dx = 0;
        let dy = 0;

        if (movement.toLowerCase().includes('zoom') || movement.toLowerCase().includes('track in')) {
          scale = 1.0 + (progress * 0.15);
        } else if (movement.toLowerCase().includes('pan left')) {
          dx = -progress * 40;
        } else if (movement.toLowerCase().includes('pan right')) {
          dx = progress * 40;
        } else if (movement.toLowerCase().includes('tilt up')) {
          dy = -progress * 25;
        } else if (movement.toLowerCase().includes('tilt down')) {
          dy = progress * 25;
        }

        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        ctx.translate(cx + dx, cy + dy);
        ctx.scale(scale, scale);
        ctx.translate(-cx, -cy);

        const imgRatio = img.width / img.height;
        const canvasRatio = canvas.width / canvas.height;
        let drawWidth = canvas.width;
        let drawHeight = canvas.height;
        let offsetX = 0;
        let offsetY = 0;

        if (imgRatio > canvasRatio) {
          drawHeight = canvas.width / imgRatio;
          offsetY = (canvas.height - drawHeight) / 2;
        } else {
          drawWidth = canvas.height * imgRatio;
          offsetX = (canvas.width - drawWidth) / 2;
        }

        ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);
        ctx.restore();
      } else {
        ctx.fillStyle = '#090912';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#f59e0b';
        ctx.font = 'bold 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText("LOADING CINE FRAME...", canvas.width / 2, canvas.height / 2);
      }

      ctx.strokeStyle = 'rgba(255,255,255,0.06)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(canvas.width / 3, 0); ctx.lineTo(canvas.width / 3, canvas.height);
      ctx.moveTo((canvas.width / 3) * 2, 0); ctx.lineTo((canvas.width / 3) * 2, canvas.height);
      ctx.moveTo(0, canvas.height / 3); ctx.lineTo(canvas.width, canvas.height / 3);
      ctx.moveTo(0, (canvas.height / 3) * 2); ctx.lineTo(canvas.width, (canvas.height / 3) * 2);
      ctx.stroke();

      ctx.fillStyle = 'rgba(0,0,0,0.85)';
      ctx.fillRect(0, 0, canvas.width, 25);
      ctx.fillRect(0, canvas.height - 25, canvas.width, 25);

      ctx.fillStyle = '#a1a1aa';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`FRAME: ${currentFrameIndex + 1}/${frames.length} | SHOT: ${frames[currentFrameIndex].shot_number}`, 15, 16);
      ctx.textAlign = 'right';
      ctx.fillText(`CINE: ${movement.toUpperCase()}`, canvas.width - 15, 16);

      if (isPlaying && progress < 1.0) {
        animationFrameRef.current = requestAnimationFrame(render);
      }
    };

    img.onload = () => {
      render();
    };
    render();

    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [currentFrameIndex, isPlaying, frames, frameDurations, cameraMovements]);

  useEffect(() => {
    if (!isPlaying || frames.length === 0) {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
      return;
    }

    const playNext = () => {
      setCurrentFrameIndex(prev => {
        if (prev >= frames.length - 1) {
          setIsPlaying(false);
          return 0;
        }
        return prev + 1;
      });
    };

    const currentDuration = (frameDurations[frames[currentFrameIndex]?.id] || 3) * 1000;
    playTimerRef.current = setTimeout(playNext, currentDuration);

    return () => {
      if (playTimerRef.current) clearTimeout(playTimerRef.current);
    };
  }, [isPlaying, currentFrameIndex, frames, frameDurations]);

  const togglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  const handlePrev = () => {
    setIsPlaying(false);
    setCurrentFrameIndex(prev => Math.max(0, prev - 1));
  };

  const handleNext = () => {
    setIsPlaying(false);
    setCurrentFrameIndex(prev => Math.min(frames.length - 1, prev + 1));
  };

  return (
    <div className="p-3 border-t border-border bg-[#07070c] text-xs text-gray-300">
      <div className="flex flex-col lg:flex-row gap-3">
        <div className="lg:w-1/2 flex flex-col bg-[#0b0b14] border border-white/5 rounded-lg overflow-hidden shadow-2xl relative">
          <canvas
            ref={canvasRef}
            width={600}
            height={337}
            className="w-full aspect-[16/9] object-contain bg-black"
          />
          <div className="p-2 border-t border-white/5 bg-black/40 flex items-center justify-between">
            <div className="flex items-center space-x-1.5">
              <button
                onClick={handlePrev}
                className="p-1.5 rounded hover:bg-white/5 text-gray-400 hover:text-white transition-colors cursor-pointer"
              >
                <SkipBack size={13} />
              </button>
              <button
                onClick={togglePlay}
                className="p-2 rounded-full bg-primary text-black hover:scale-105 transition-transform cursor-pointer"
              >
                {isPlaying ? <Pause size={13} fill="black" /> : <Play size={13} fill="black" />}
              </button>
              <button
                onClick={handleNext}
                className="p-1.5 rounded hover:bg-white/5 text-gray-400 hover:text-white transition-colors cursor-pointer"
              >
                <SkipForward size={13} />
              </button>
            </div>
            <div className="text-[10px] text-gray-500 font-mono flex items-center space-x-1.5">
              <Video size={12} className="text-amber-500" />
              <span>Wan 2.2 / Hunyuan Engine Sim</span>
            </div>
          </div>
        </div>

        <div className="lg:w-1/2 flex flex-col justify-between p-1 bg-[#090913] rounded border border-white/5 overflow-hidden">
          <div className="p-2 border-b border-white/5">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">Animatic Reel Filmstrip</span>
          </div>

          <div className="flex-1 overflow-x-auto py-3 px-2 flex space-x-3 items-center min-h-[140px]">
            {frames.length === 0 ? (
              <div className="flex-1 text-center py-6 text-gray-600">
                <span>No storyboards generated for this scene yet. Generate images to play the reel.</span>
              </div>
            ) : (
              frames.map((shot, idx) => (
                <div
                  key={shot.id}
                  onClick={() => {
                    setIsPlaying(false);
                    setCurrentFrameIndex(idx);
                  }}
                  className={`flex-shrink-0 w-24 border rounded bg-[#0d0d16] p-1 transition-all cursor-pointer ${
                    currentFrameIndex === idx ? 'border-primary shadow-lg ring-1 ring-primary/20 scale-105' : 'border-white/5 hover:border-white/10'
                  }`}
                >
                  <img
                    src={shot.storyboard_frames?.[0]?.image_url?.startsWith('http') ? shot.storyboard_frames?.[0]?.image_url : `http://localhost:8000${shot.storyboard_frames?.[0]?.image_url}`}
                    alt="shot strip"
                    className="w-full aspect-[16/9] object-cover bg-black rounded"
                  />
                  <div className="mt-1.5 space-y-1 text-[9px]">
                    <div className="flex justify-between font-mono font-bold text-gray-400">
                      <span>Shot #{shot.shot_number}</span>
                    </div>
                    <div className="flex items-center space-x-1 text-gray-500">
                      <Clock size={8} />
                      <input
                        type="number"
                        min={1}
                        max={10}
                        value={frameDurations[shot.id] || 3}
                        onChange={(e) => {
                          const val = parseInt(e.target.value) || 1;
                          setFrameDurations(prev => ({ ...prev, [shot.id]: val }));
                        }}
                        className="w-8 bg-black/40 border border-white/5 rounded text-center text-white outline-none font-mono py-0.5 text-[8px]"
                      />
                      <span>sec</span>
                    </div>
                    <div className="flex items-center space-x-1 text-gray-500">
                      <Compass size={8} />
                      <select
                        value={cameraMovements[shot.id] || 'Static'}
                        onChange={(e) => {
                          setCameraMovements(prev => ({ ...prev, [shot.id]: e.target.value }));
                        }}
                        className="bg-black/40 border border-white/5 rounded text-white outline-none text-[8px] py-0.5"
                      >
                        <option>Static</option>
                        <option>Zoom In</option>
                        <option>Pan Left</option>
                        <option>Pan Right</option>
                        <option>Tilt Up</option>
                        <option>Tilt Down</option>
                      </select>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
