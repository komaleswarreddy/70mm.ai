'use client';

import React from 'react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, horizontalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Image as ImageIcon, Sparkles, RefreshCw, ShieldCheck, AlertTriangle, X, ZoomIn } from 'lucide-react';
import { Shot, ContinuityCheckResult } from '../lib/api';

interface StoryboardTimelineProps {
  shots: Shot[];
  onReorderShots: (ids: string[]) => void;
  onGenerateImage: (shotId: string) => void;
  isGeneratingImage: string | null;
  onCheckContinuity?: (shotId: string) => Promise<ContinuityCheckResult | void>;
}

interface SortableItemProps {
  shot: Shot;
  onGenerateImage: (shotId: string) => void;
  isGeneratingThisImage: boolean;
  onCheckContinuity?: (shotId: string) => Promise<ContinuityCheckResult | void>;
  onOpenLightbox: (shot: Shot) => void;
}

function SortableShotItem({ shot, onGenerateImage, isGeneratingThisImage, onCheckContinuity, onOpenLightbox }: SortableItemProps) {
  const [isChecking, setIsChecking] = React.useState(false);
  const [checkResult, setCheckResult] = React.useState<ContinuityCheckResult | null>(null);

  const handleCheckClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onCheckContinuity) return;
    setIsChecking(true);
    try {
      const result = await onCheckContinuity(shot.id);
      if (result) setCheckResult(result);
    } catch (err) {
      console.error(err);
    } finally {
      setIsChecking(false);
    }
  };
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: shot.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    zIndex: isDragging ? 10 : 1,
  };

  const frame = shot.storyboard_frames?.[0];
  const backendBaseUrl = 'http://localhost:8000';
  const imageUrl = frame?.image_url ? `${backendBaseUrl}${frame.image_url}` : null;
  const isCompleted = frame?.status === 'completed';
  const isPending = frame?.status === 'pending' || isGeneratingThisImage;

  return (
    <div 
      ref={setNodeRef} 
      style={style}
      className={`flex-shrink-0 w-64 bg-[#0a0a0f] border rounded-lg overflow-hidden group transition-all duration-150 ${
        isDragging ? "border-primary shadow-2xl" : "border-border hover:border-gray-700"
      }`}
    >
      <div
        {...attributes}
        {...listeners}
        onClick={() => { if (isCompleted && imageUrl) onOpenLightbox(shot); }}
        className={`h-32 bg-[#05050a] flex items-center justify-center relative overflow-hidden active:cursor-grabbing group-hover:opacity-95 transition-opacity ${isCompleted && imageUrl ? 'cursor-zoom-in' : 'cursor-grab'}`}
      >
        {isPending ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 space-y-2">
            <RefreshCw size={24} className="text-primary animate-spin" />
            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest animate-pulse">Generating...</span>
          </div>
        ) : imageUrl && isCompleted ? (
          <>
            <img
              src={imageUrl}
              alt={`Shot ${shot.shot_number}`}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/30 transition-colors pointer-events-none">
              <ZoomIn size={20} className="text-white opacity-0 group-hover:opacity-90 transition-opacity" />
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center text-gray-700 space-y-1">
            <ImageIcon size={28} />
            <span className="text-[10px] uppercase font-bold tracking-wider">No Visual Frame</span>
          </div>
        )}
        
        <div className="absolute top-2 left-2 flex items-center space-x-1">
          <span className="bg-black/80 backdrop-blur border border-border px-1.5 py-0.5 rounded text-[9px] font-bold text-primary">
            SHOT {shot.shot_number}
          </span>
          {!!shot.needs_review && (
            <span
              title={`Stage 9: flagged for continuity review${shot.continuity_score != null ? ` (score ${shot.continuity_score})` : ''}`}
              className="bg-amber-950/90 backdrop-blur border border-amber-500/40 p-0.5 rounded"
            >
              <AlertTriangle size={10} className="text-amber-500" />
            </span>
          )}
        </div>

        {!isPending && (
          <div className="absolute bottom-2 right-2 flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {onCheckContinuity && isCompleted && (
              <button
                onClick={handleCheckClick}
                disabled={isChecking}
                title="Stage 9: check this shot's character-identity/style-drift/color-grade continuity against the rest of the scene"
                className="flex items-center space-x-1 px-2 py-1 rounded bg-secondary border border-border text-gray-300 font-bold text-[10px] hover:text-white cursor-pointer shadow-lg disabled:opacity-50"
              >
                <ShieldCheck size={10} className={isChecking ? "animate-pulse" : ""} />
                <span>{isChecking ? "Checking..." : "Continuity"}</span>
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onGenerateImage(shot.id);
              }}
              className="flex items-center space-x-1 px-2 py-1 rounded bg-primary text-black font-bold text-[10px] cursor-pointer shadow-lg"
            >
              <Sparkles size={10} />
              <span>{imageUrl ? "Regen" : "Generate"}</span>
            </button>
          </div>
        )}
      </div>

      {checkResult && (
        <div className={`px-2 py-1 text-[9px] border-t ${checkResult.needs_review ? 'bg-amber-950/40 border-amber-500/30 text-amber-400' : 'bg-emerald-950/40 border-emerald-500/30 text-emerald-400'}`}>
          {checkResult.needs_review
            ? `Flagged: ${checkResult.flags.join(', ')}`
            : 'No continuity issues found'}
        </div>
      )}

      <div className="p-3 bg-[#0d0d15]/50 border-t border-border flex flex-col justify-between">
        <div className="flex justify-between items-center text-[10px] font-bold text-gray-300">
          <span className="text-primary">{shot.shot_size || "MS"}</span>
          <span className="text-gray-500 font-normal">{shot.lens || "50mm"}</span>
        </div>
        <p className="text-[10px] text-gray-400 mt-1 line-clamp-2 leading-relaxed min-h-[2.5rem]">
          {shot.notes || <span className="text-gray-700 italic">No notes written for this shot...</span>}
        </p>
      </div>
    </div>
  );
}

export function StoryboardTimeline({ shots, onReorderShots, onGenerateImage, isGeneratingImage, onCheckContinuity }: StoryboardTimelineProps) {
  const [lightboxShot, setLightboxShot] = React.useState<Shot | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    
    if (over && active.id !== over.id) {
      const oldIndex = shots.findIndex((s) => s.id === active.id);
      const newIndex = shots.findIndex((s) => s.id === over.id);
      
      const newShots = arrayMove(shots, oldIndex, newIndex);
      onReorderShots(newShots.map(s => s.id));
    }
  };

  return (
    <div className="glass-panel border-t border-border h-48 flex flex-col z-30 overflow-hidden">
      <div className="px-4 py-2 border-b border-border bg-[#0d0d15]/80 flex items-center justify-between">
        <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">
          Storyboard Timeline (Drag cards to reorder shots)
        </span>
      </div>

      <div className="flex-1 overflow-x-auto p-4 flex items-center space-x-4">
        {shots.length === 0 ? (
          <div className="flex-1 text-center text-xs text-gray-500 py-6">
            No storyboard timeline cards available. Create shots in the planner first.
          </div>
        ) : (
          <DndContext 
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext 
              items={shots.map(s => s.id)} 
              strategy={horizontalListSortingStrategy}
            >
              <div className="flex space-x-4">
                {shots.map((shot) => (
                  <SortableShotItem
                    key={shot.id}
                    shot={shot}
                    onGenerateImage={onGenerateImage}
                    isGeneratingThisImage={isGeneratingImage === shot.id}
                    onCheckContinuity={onCheckContinuity}
                    onOpenLightbox={setLightboxShot}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}
      </div>

      {lightboxShot && (
        <ShotLightbox shot={lightboxShot} onClose={() => setLightboxShot(null)} />
      )}
    </div>
  );
}

function ShotLightbox({ shot, onClose }: { shot: Shot; onClose: () => void }) {
  const backendBaseUrl = 'http://localhost:8000';
  const frame = shot.storyboard_frames?.[0];
  const imageUrl = frame?.image_url ? `${backendBaseUrl}${frame.image_url}` : null;

  React.useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 bg-black/90 flex items-center justify-center z-[200] p-6 backdrop-blur-md animate-fade-in"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="glass max-w-5xl w-full max-h-[90vh] rounded-2xl overflow-hidden shadow-2xl border border-primary/20 bg-[#07070a] flex flex-col"
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-[#0a0a0f] shrink-0">
          <span className="text-sm font-bold text-gray-200 uppercase tracking-wider">
            Shot {shot.shot_number} {shot.shot_type ? `-- ${shot.shot_type}` : ''}
          </span>
          <button onClick={onClose} className="text-gray-400 hover:text-white cursor-pointer p-1 rounded-full">
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto flex flex-col md:flex-row">
          <div className="flex-1 bg-black flex items-center justify-center min-h-[300px]">
            {imageUrl ? (
              <img src={imageUrl} alt={`Shot ${shot.shot_number}`} className="max-w-full max-h-[70vh] w-auto h-auto object-contain" />
            ) : (
              <span className="text-gray-600 text-xs">No image generated yet.</span>
            )}
          </div>

          <div className="w-full md:w-72 p-4 space-y-3 text-xs text-gray-300 border-t md:border-t-0 md:border-l border-border shrink-0 bg-[#0a0a0f]">
            <div className="grid grid-cols-2 gap-2">
              <div><span className="text-gray-500 block text-[9px] uppercase">Size</span>{shot.shot_size || '--'}</div>
              <div><span className="text-gray-500 block text-[9px] uppercase">Angle</span>{shot.angle || '--'}</div>
              <div><span className="text-gray-500 block text-[9px] uppercase">Lens</span>{shot.lens || '--'}</div>
              <div><span className="text-gray-500 block text-[9px] uppercase">Movement</span>{shot.movement || '--'}</div>
              <div><span className="text-gray-500 block text-[9px] uppercase">Lighting</span>{shot.lighting || '--'}</div>
              <div><span className="text-gray-500 block text-[9px] uppercase">Day/Night</span>{shot.day_night || '--'}</div>
            </div>
            {shot.reasoning && (
              <div>
                <span className="text-gray-500 block text-[9px] uppercase mb-1">Reasoning</span>
                <p className="leading-relaxed text-gray-400">{shot.reasoning}</p>
              </div>
            )}
            {shot.notes && (
              <div>
                <span className="text-gray-500 block text-[9px] uppercase mb-1">Notes</span>
                <p className="leading-relaxed text-gray-400">{shot.notes}</p>
              </div>
            )}
            {!!shot.needs_review && (
              <div className="bg-amber-950/40 border border-amber-500/30 rounded p-2 text-amber-400">
                Flagged for continuity review{shot.continuity_score != null ? ` (score ${shot.continuity_score})` : ''}.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
