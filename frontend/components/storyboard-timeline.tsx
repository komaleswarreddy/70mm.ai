'use client';

import React from 'react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, horizontalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Image as ImageIcon, Sparkles, RefreshCw } from 'lucide-react';
import { Shot } from '../lib/api';

interface StoryboardTimelineProps {
  shots: Shot[];
  onReorderShots: (ids: string[]) => void;
  onGenerateImage: (shotId: string) => void;
  isGeneratingImage: string | null;
}

interface SortableItemProps {
  shot: Shot;
  onGenerateImage: (shotId: string) => void;
  isGeneratingThisImage: boolean;
}

function SortableShotItem({ shot, onGenerateImage, isGeneratingThisImage }: SortableItemProps) {
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
        className="h-32 bg-[#05050a] flex items-center justify-center relative overflow-hidden cursor-grab active:cursor-grabbing group-hover:opacity-95 transition-opacity"
      >
        {isPending ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 space-y-2">
            <RefreshCw size={24} className="text-primary animate-spin" />
            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest animate-pulse">Generating...</span>
          </div>
        ) : imageUrl && isCompleted ? (
          <img 
            src={imageUrl} 
            alt={`Shot ${shot.shot_number}`}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-gray-700 space-y-1">
            <ImageIcon size={28} />
            <span className="text-[10px] uppercase font-bold tracking-wider">No Visual Frame</span>
          </div>
        )}
        
        <div className="absolute top-2 left-2 bg-black/80 backdrop-blur border border-border px-1.5 py-0.5 rounded text-[9px] font-bold text-primary">
          SHOT {shot.shot_number}
        </div>

        {!isPending && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onGenerateImage(shot.id);
            }}
            className="absolute bottom-2 right-2 flex items-center space-x-1 px-2 py-1 rounded bg-primary text-black font-bold text-[10px] opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer shadow-lg"
          >
            <Sparkles size={10} />
            <span>{imageUrl ? "Regen" : "Generate"}</span>
          </button>
        )}
      </div>

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

export function StoryboardTimeline({ shots, onReorderShots, onGenerateImage, isGeneratingImage }: StoryboardTimelineProps) {
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
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}
      </div>
    </div>
  );
}
