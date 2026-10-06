'use client';

import React, { useState } from 'react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Sparkles, X, ChevronRight, Brain } from 'lucide-react';
import { Scene } from '../lib/api';
import { SceneInspector } from './scene-inspector/scene-inspector';


interface SceneCardsProps {
  scenes: Scene[];
  selectedSceneId?: string;
  onSelectScene: (scene: Scene) => void;
  onFormulateScene: (sceneId: string, actionLine: string) => Promise<any>;
  onReorderScenes?: (ids: string[]) => void;
  onUnderstandScene?: (sceneId: string) => Promise<Scene | void>;
}

interface SortableSceneItemProps {
  scene: Scene;
  isSelected: boolean;
  isFormulating: boolean;
  isUnderstanding: boolean;
  onSelectScene: (scene: Scene) => void;
  onFormulateClick: (scene: Scene, e: React.MouseEvent) => void;
  onUnderstandClick?: (scene: Scene, e: React.MouseEvent) => void;
}

function SortableSceneItem({ scene, isSelected, isFormulating, isUnderstanding, onSelectScene, onFormulateClick, onUnderstandClick }: SortableSceneItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: scene.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    zIndex: isDragging ? 10 : 1,
  };

  const actionCount = scene.action_blocks?.length || 0;
  const dialogueCount = scene.dialogues?.length || 0;
  const shotCount = scene.shots?.length || 0;

  return (
    <div
      ref={setNodeRef}
      style={style}
      onClick={() => onSelectScene(scene)}
      className={`group border rounded-lg p-3 cursor-pointer transition-all duration-150 relative ${
        isSelected
          ? "bg-primary/10 border-primary text-white shadow-[0_0_15px_rgba(234,179,8,0.1)]"
          : "bg-[#0d0d15]/40 border-border text-gray-300 hover:border-gray-700 hover:bg-[#0d0d15]/80"
      }`}
    >
      <div 
        {...attributes} 
        {...listeners} 
        className="flex justify-between items-start mb-2 cursor-grab active:cursor-grabbing"
      >
        <span className="text-[10px] font-bold text-primary tracking-widest uppercase select-none">
          SCENE {scene.scene_number}
        </span>

        <div className="flex items-center space-x-1">
          {onUnderstandClick && (
            <button
              onClick={(e) => onUnderstandClick(scene, e)}
              disabled={isUnderstanding}
              title="Stage 3: analyze emotion, conflict, key objects, and continuity for this scene"
              className="flex items-center space-x-1 px-1.5 py-0.5 rounded text-[9px] font-bold border transition-colors cursor-pointer bg-blue-600/10 border-blue-600/30 text-blue-400 hover:bg-blue-600 hover:text-black hover:border-blue-600"
            >
              <Brain size={10} />
              <span>{isUnderstanding ? "Understanding..." : scene.emotion ? "Re-understand" : "Understand"}</span>
            </button>
          )}
          <button
            onClick={(e) => onFormulateClick(scene, e)}
            disabled={isFormulating}
            className="flex items-center space-x-1 px-1.5 py-0.5 rounded text-[9px] font-bold border transition-colors cursor-pointer bg-yellow-600/10 border-yellow-600/30 text-yellow-500 hover:bg-yellow-600 hover:text-black hover:border-yellow-600"
          >
            <Sparkles size={10} />
            <span>{isFormulating ? "Analyzing..." : "Formulate"}</span>
          </button>
        </div>
      </div>

      <h4 className="text-xs font-bold leading-tight line-clamp-2 screenplay-font mb-3 select-none">
        {scene.heading}
      </h4>

      {scene.emotion && (
        <p className="text-[9px] text-blue-400/80 italic mb-2 line-clamp-1 select-none">
          {scene.emotion}{scene.conflict ? ` · ${scene.conflict}` : ''}
        </p>
      )}

      <div className="flex items-center justify-between text-[9px] font-semibold text-gray-500 select-none">
        <div className="flex items-center space-x-2">
          <span>{actionCount} Actions</span>
          <span>•</span>
          <span>{dialogueCount} Dialogues</span>
        </div>
        <span className="bg-secondary px-1.5 py-0.5 rounded text-gray-400 font-bold border border-border/50">
          {shotCount} Shots
        </span>
      </div>
      
      <ChevronRight 
        size={14} 
        className={`absolute right-2 top-1/2 -translate-y-1/2 text-gray-600 group-hover:text-primary group-hover:translate-x-0.5 transition-all ${
          isSelected ? "text-primary translate-x-0" : "opacity-0 group-hover:opacity-100"
        }`} 
      />
    </div>
  );
}

export function SceneCards({ scenes, selectedSceneId, onSelectScene, onFormulateScene, onReorderScenes, onUnderstandScene }: SceneCardsProps) {
  const [formulationData, setFormulationData] = useState<any>(null);
  const [isFormulating, setIsFormulating] = useState<string | null>(null);
  const [isUnderstanding, setIsUnderstanding] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [formulatedSceneHeading, setFormulatedSceneHeading] = useState('');

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
    if (over && active.id !== over.id && onReorderScenes) {
      const oldIndex = scenes.findIndex((s) => s.id === active.id);
      const newIndex = scenes.findIndex((s) => s.id === over.id);
      const newScenes = arrayMove(scenes, oldIndex, newIndex);
      onReorderScenes(newScenes.map(s => s.id));
    }
  };

  const handleFormulateClick = async (scene: Scene, e: React.MouseEvent) => {
    e.stopPropagation();
    const contextText = scene.action_blocks?.[0]?.content || scene.heading;
    
    setIsFormulating(scene.id);
    setFormulatedSceneHeading(scene.heading);
    try {
      const data = await onFormulateScene(scene.id, contextText);
      setFormulationData(data);
      setShowModal(true);
    } catch (err) {
      console.error(err);
    } finally {
      setIsFormulating(null);
    }
  };

  const handleUnderstandClick = async (scene: Scene, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onUnderstandScene) return;
    setIsUnderstanding(scene.id);
    try {
      await onUnderstandScene(scene.id);
    } catch (err) {
      console.error(err);
    } finally {
      setIsUnderstanding(null);
    }
  };


  return (
    <div className="w-80 bg-[#07070c] border-r border-border h-full flex flex-col overflow-hidden">
      <div className="p-3 border-b border-border bg-[#0d0d15]/80 flex items-center justify-between">
        <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">
          Scenes List ({scenes.length})
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {scenes.length === 0 ? (
          <p className="text-xs text-gray-500 text-center py-8">No scenes found. Upload a screenplay script to parse.</p>
        ) : (
          <DndContext 
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext 
              items={scenes.map(s => s.id)} 
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {scenes.map((scene) => (
                  <SortableSceneItem
                    key={scene.id}
                    scene={scene}
                    isSelected={scene.id === selectedSceneId}
                    isFormulating={isFormulating === scene.id}
                    isUnderstanding={isUnderstanding === scene.id}
                    onSelectScene={onSelectScene}
                    onFormulateClick={handleFormulateClick}
                    onUnderstandClick={onUnderstandScene ? handleUnderstandClick : undefined}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}
      </div>

      {/* Scene Formulation Inspector Drawer */}
      <SceneInspector 
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        sceneHeading={formulatedSceneHeading}
        formulationData={formulationData}
      />
    </div>

  );
}
