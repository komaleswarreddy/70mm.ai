'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
  Users, MessageSquare, ShieldAlert, Monitor, Wallet, BookOpen, 
  Layers, Shield, Undo, Redo, ZoomIn, ZoomOut, CheckCircle2, RefreshCw 
} from 'lucide-react';

import { Navbar } from '../../../components/navbar';
import { Sidebar } from '../../../components/sidebar';
import { ScriptEditor } from '../../../components/script-editor';
import { SceneCards } from '../../../components/scene-cards';
import { ShotPlanner } from '../../../components/shot-planner';
import { StoryboardTimeline } from '../../../components/storyboard-timeline';
import { api, Project, Scene, Shot } from '../../../lib/api';
import { useAuth } from '../../../components/auth-provider';
import { CinematicLoader } from '../../../components/progress-cards/cinematic-loader';
import { StoryTimeline } from '../../../components/story-timeline/story-timeline';

// Import newly created modular components
import { ContinuityPanel } from '../../../components/continuity-panel';
import { DirectorMonitor } from '../../../components/director-monitor';
import { ProductionPlanner } from '../../../components/production-planner';
import { AnimaticTimeline } from '../../../components/animatic-timeline';
import { RAGSearch } from '../../../components/rag-search';
import { QADashboard } from '../../../components/qa-dashboard';
import { CommentsSidebar } from '../../../components/comments-sidebar';
import { CollaborativeAgents } from '../../../components/collaborative-agents';
import { PluginsContainer } from '../../../components/plugins-container';
import { ReferenceLibrary } from '../../../components/reference-library';

export default function WorkspacePage() {
  const { user, loading: authLoading } = useAuth();
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [project, setProject] = useState<Project | undefined>(undefined);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [selectedScene, setSelectedScene] = useState<Scene | undefined>(undefined);
  const [shots, setShots] = useState<Shot[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [isGeneratingStory, setIsGeneratingStory] = useState(false);
  const [isUploadingScript, setIsUploadingScript] = useState(false);
  const [isSavingScript, setIsSavingScript] = useState(false);
  const [isGeneratingImage, setIsGeneratingImage] = useState<string | null>(null);

  // Tab configurations
  const [leftTab, setLeftTab] = useState<'outline' | 'comments' | 'agents'>('outline');
  const [rightTab, setRightTab] = useState<'shots' | 'continuity' | 'monitor' | 'planner' | 'rag' | 'plugins' | 'qa' | 'reference'>('shots');
  const [bottomTab, setBottomTab] = useState<'timeline' | 'storyboard' | 'animatic'>('storyboard');

  // Resizable sizes (width/height in px)
  const [leftWidth, setLeftWidth] = useState(250);
  const [rightWidth, setRightWidth] = useState(420);
  const [bottomHeight, setBottomHeight] = useState(190);

  // Undo/Redo & Zoom & Autosave states
  const [editorZoom, setEditorZoom] = useState(13); // base font size in px
  const [undoStack, setUndoStack] = useState<string[]>([]);
  const [redoStack, setRedoStack] = useState<string[]>([]);
  const [saveState, setSaveState] = useState<'saved' | 'saving' | 'unsaved'>('saved');

  const fetchProjectData = async () => {
    try {
      const proj = await api.getProject(projectId);
      setProject(proj);
      
      const sortedScenes = (proj.scenes || []).sort((a, b) => a.order - b.order);
      setScenes(sortedScenes);
      
      if (sortedScenes.length > 0) {
        if (!selectedScene) {
          setSelectedScene(sortedScenes[0]);
          setShots((sortedScenes[0].shots || []).sort((a, b) => a.order - b.order));
        } else {
          const current = sortedScenes.find(s => s.id === selectedScene.id);
          if (current) {
            setSelectedScene(current);
            setShots((current.shots || []).sort((a, b) => a.order - b.order));
          }
        }
      }
    } catch (err) {
      console.error("Error fetching project data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push('/');
      } else if (projectId) {
        fetchProjectData();
      }
    }
  }, [projectId, user, authLoading]);

  // Resizing event handlers
  const startResizeLeft = (mouseDownEvent: React.MouseEvent) => {
    mouseDownEvent.preventDefault();
    const startX = mouseDownEvent.clientX;
    const startWidth = leftWidth;

    const doDrag = (mouseMoveEvent: MouseEvent) => {
      const offset = mouseMoveEvent.clientX - startX;
      const nextWidth = Math.max(160, Math.min(400, startWidth + offset));
      setLeftWidth(nextWidth);
    };

    const stopDrag = () => {
      document.removeEventListener('mousemove', doDrag);
      document.removeEventListener('mouseup', stopDrag);
    };

    document.addEventListener('mousemove', doDrag);
    document.addEventListener('mouseup', stopDrag);
  };

  const startResizeRight = (mouseDownEvent: React.MouseEvent) => {
    mouseDownEvent.preventDefault();
    const startX = mouseDownEvent.clientX;
    const startWidth = rightWidth;

    const doDrag = (mouseMoveEvent: MouseEvent) => {
      const offset = startX - mouseMoveEvent.clientX;
      const nextWidth = Math.max(250, Math.min(600, startWidth + offset));
      setRightWidth(nextWidth);
    };

    const stopDrag = () => {
      document.removeEventListener('mousemove', doDrag);
      document.removeEventListener('mouseup', stopDrag);
    };

    document.addEventListener('mousemove', doDrag);
    document.addEventListener('mouseup', stopDrag);
  };

  const startResizeBottom = (mouseDownEvent: React.MouseEvent) => {
    mouseDownEvent.preventDefault();
    const startY = mouseDownEvent.clientY;
    const startHeight = bottomHeight;

    const doDrag = (mouseMoveEvent: MouseEvent) => {
      const offset = startY - mouseMoveEvent.clientY;
      const nextHeight = Math.max(120, Math.min(350, startHeight + offset));
      setBottomHeight(nextHeight);
    };

    const stopDrag = () => {
      document.removeEventListener('mousemove', doDrag);
      document.removeEventListener('mouseup', stopDrag);
    };

    document.addEventListener('mousemove', doDrag);
    document.addEventListener('mouseup', stopDrag);
  };

  const handleGenerateStory = async (idea: string) => {
    setIsGeneratingStory(true);
    try {
      await api.generateStory(projectId, idea);
      await fetchProjectData();
    } catch (err) {
      console.error(err);
    } finally {
      setIsGeneratingStory(false);
    }
  };

  const handleUploadScript = async (file: File) => {
    setIsUploadingScript(true);
    try {
      await api.uploadScript(projectId, file);
      setSelectedScene(undefined);
      await fetchProjectData();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUploadingScript(false);
    }
  };

  const handleSaveScript = async (content: string) => {
    if (!selectedScene) return;
    setSaveState('saving');
    setIsSavingScript(true);
    
    // Save state onto Undo Stack
    if (selectedScene.raw_content !== content) {
      setUndoStack(prev => [...prev, selectedScene.raw_content || '']);
      setRedoStack([]); // Clear Redo stack on new action
    }

    try {
      await api.updateScene(selectedScene.id, { raw_content: content });
      setSelectedScene(prev => prev ? { ...prev, raw_content: content } : undefined);
      setSaveState('saved');
    } catch (err) {
      console.error(err);
      setSaveState('unsaved');
    } finally {
      setIsSavingScript(false);
    }
  };

  const triggerUndo = async () => {
    if (undoStack.length === 0 || !selectedScene) return;
    const previous = undoStack[undoStack.length - 1];
    setUndoStack(prev => prev.slice(0, -1));
    setRedoStack(prev => [...prev, selectedScene.raw_content || '']);
    
    setSaveState('saving');
    try {
      await api.updateScene(selectedScene.id, { raw_content: previous });
      setSelectedScene(prev => prev ? { ...prev, raw_content: previous } : undefined);
      setSaveState('saved');
    } catch (err) {
      console.error(err);
      setSaveState('unsaved');
    }
  };

  const triggerRedo = async () => {
    if (redoStack.length === 0 || !selectedScene) return;
    const next = redoStack[redoStack.length - 1];
    setRedoStack(prev => prev.slice(0, -1));
    setUndoStack(prev => [...prev, selectedScene.raw_content || '']);
    
    setSaveState('saving');
    try {
      await api.updateScene(selectedScene.id, { raw_content: next });
      setSelectedScene(prev => prev ? { ...prev, raw_content: next } : undefined);
      setSaveState('saved');
    } catch (err) {
      console.error(err);
      setSaveState('unsaved');
    }
  };

  const handleSelectScene = (scene: Scene) => {
    setSelectedScene(scene);
    setShots((scene.shots || []).sort((a, b) => a.order - b.order));
  };

  const handleAddShot = async () => {
    if (!selectedScene) return;
    try {
      const nextNum = shots.length + 1;
      await api.createShot(selectedScene.id, nextNum, "A new shot notes");
      await fetchProjectData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpdateShot = async (id: string, updates: Partial<Shot>) => {
    try {
      await api.updateShot(id, updates);
      setShots(prev => prev.map(s => s.id === id ? { ...s, ...updates } : s));
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteShot = async (id: string) => {
    try {
      await api.deleteShot(id);
      await fetchProjectData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleReorderShots = async (ids: string[]) => {
    try {
      await api.reorderShots(ids);
      const reordered = [...shots].sort((a, b) => ids.indexOf(a.id) - ids.indexOf(b.id));
      setShots(reordered);
    } catch (err) {
      console.error(err);
    }
  };

  const handleReorderScenes = async (ids: string[]) => {
    try {
      await api.reorderScenes(ids);
      const reordered = [...scenes].sort((a, b) => ids.indexOf(a.id) - ids.indexOf(b.id));
      setScenes(reordered);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerateImage = async (shotId: string) => {
    setIsGeneratingImage(shotId);
    try {
      await api.generateStoryboard(shotId);
      await fetchProjectData();
    } catch (err) {
      console.error(err);
    } finally {
      setIsGeneratingImage(null);
    }
  };

  const handleExportPDF = () => {
    window.open(`http://localhost:8000/api/projects/${projectId}/export/pdf`, '_blank');
  };

  const handleExportCSV = () => {
    window.open(`http://localhost:8000/api/projects/${projectId}/export/csv`, '_blank');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm font-semibold text-gray-400">Loading film workspace...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col overflow-hidden relative select-none">
      {isGeneratingStory && (
        <div className="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-6 backdrop-blur-md">
          <CinematicLoader title="Developing Story Blueprint" />
        </div>
      )}

      <Navbar 
        projectTitle={project?.title} 
        projectId={projectId} 
        onExportPDF={handleExportPDF}
        onExportCSV={handleExportCSV}
      />
      
      {/* Dynamic resizable layout panels */}
      <div className="flex flex-1 overflow-hidden h-[calc(100vh-3.5rem)]">
        {/* LEFT COLUMN: Sidebar Outline + Comments + Collaboration Agents */}
        <div style={{ width: `${leftWidth}px` }} className="flex flex-col border-r border-border shrink-0 bg-[#07070c]">
          {/* Header tabs selector */}
          <div className="p-2 border-b border-border flex items-center justify-around bg-[#0a0a14]">
            <button 
              onClick={() => setLeftTab('outline')}
              className={`px-2 py-1 rounded text-[10px] font-bold ${leftTab === 'outline' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            >
              Outline
            </button>
            <button 
              onClick={() => setLeftTab('comments')}
              className={`px-2 py-1 rounded text-[10px] font-bold ${leftTab === 'comments' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            >
              Comments
            </button>
            <button 
              onClick={() => setLeftTab('agents')}
              className={`px-2 py-1 rounded text-[10px] font-bold ${leftTab === 'agents' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            >
              Agents
            </button>
          </div>

          <div className="flex-1 overflow-hidden flex flex-col">
            {leftTab === 'outline' && (
              <Sidebar 
                project={project}
                onGenerateStory={handleGenerateStory}
                onUploadScript={handleUploadScript}
                isGeneratingStory={isGeneratingStory}
                isUploadingScript={isUploadingScript}
                onRefreshProject={fetchProjectData}
              />
            )}
            {leftTab === 'comments' && (
              <CommentsSidebar projectId={projectId} sceneId={selectedScene?.id} />
            )}
            {leftTab === 'agents' && (
              <CollaborativeAgents />
            )}
          </div>
        </div>

        {/* LEFT RESIZER DIVIDER BAR */}
        <div 
          onMouseDown={startResizeLeft}
          className="w-1 bg-border/40 hover:bg-amber-500/60 transition-colors cursor-col-resize self-stretch shrink-0 z-10"
        />

        {/* CENTER COLUMN: Screenplay editor panel */}
        <div className="flex-1 flex flex-col overflow-hidden bg-background">
          {/* Editor Action utility bar */}
          <div className="p-2 border-b border-border bg-[#090911]/80 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {/* Undo/Redo */}
              <button 
                onClick={triggerUndo} 
                disabled={undoStack.length === 0} 
                className="p-1 rounded hover:bg-white/5 text-gray-400 disabled:opacity-30 transition-all cursor-pointer"
                title="Undo edit"
              >
                <Undo size={13} />
              </button>
              <button 
                onClick={triggerRedo} 
                disabled={redoStack.length === 0} 
                className="p-1 rounded hover:bg-white/5 text-gray-400 disabled:opacity-30 transition-all cursor-pointer"
                title="Redo edit"
              >
                <Redo size={13} />
              </button>
              
              {/* Font Zoom controls */}
              <div className="flex items-center space-x-1.5 border-l border-white/5 pl-3">
                <button onClick={() => setEditorZoom(z => Math.max(10, z - 1))} className="p-1 text-gray-500 hover:text-white cursor-pointer"><ZoomOut size={12} /></button>
                <span className="text-[9px] font-mono text-gray-500">{editorZoom}px</span>
                <button onClick={() => setEditorZoom(z => Math.min(22, z + 1))} className="p-1 text-gray-500 hover:text-white cursor-pointer"><ZoomIn size={12} /></button>
              </div>
            </div>

            {/* Autosave notifier */}
            <div className="flex items-center space-x-1.5 text-[9px] font-mono text-gray-500 pr-1">
              {saveState === 'saving' ? (
                <>
                  <RefreshCw className="animate-spin text-amber-500" size={10} />
                  <span>Syncing...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="text-emerald-500" size={10} />
                  <span>Autosaved</span>
                </>
              )}
            </div>
          </div>

          <div className="flex-1 flex overflow-hidden">
            {/* Scene navigation selector columns */}
            <SceneCards 
              scenes={scenes}
              selectedSceneId={selectedScene?.id}
              onSelectScene={handleSelectScene}
              onFormulateScene={api.formulateScene}
              onReorderScenes={handleReorderScenes}
            />
            
            {/* Screenplay layout editor */}
            <div className="flex-1 overflow-hidden" style={{ fontSize: `${editorZoom}px` }}>
              <ScriptEditor 
                scene={selectedScene}
                onSaveScript={handleSaveScript}
                isSaving={isSavingScript}
              />
            </div>
          </div>

          {/* BOTTOM STORYBOARD TIMELINE COLLAPSIBLE */}
          <div style={{ height: `${bottomHeight}px` }} className="border-t border-border bg-[#07070c] shrink-0 flex flex-col overflow-hidden">
            {/* Tabs selectors for bottom strip */}
            <div className="p-2 border-b border-border bg-[#0a0a14] flex items-center justify-start space-x-3">
              <button 
                onClick={() => setBottomTab('timeline')}
                className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${bottomTab === 'timeline' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
              >
                Act Track
              </button>
              <button 
                onClick={() => setBottomTab('storyboard')}
                className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${bottomTab === 'storyboard' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
              >
                Storyboard
              </button>
              <button 
                onClick={() => setBottomTab('animatic')}
                className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${bottomTab === 'animatic' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
              >
                Animatic Engine
              </button>
            </div>

            <div className="flex-1 overflow-hidden flex flex-col justify-center">
              {bottomTab === 'timeline' && (
                <StoryTimeline 
                  scenes={scenes}
                  selectedSceneId={selectedScene?.id}
                  onSelectScene={handleSelectScene}
                />
              )}
              {bottomTab === 'storyboard' && (
                <StoryboardTimeline 
                  shots={shots}
                  onReorderShots={handleReorderShots}
                  onGenerateImage={handleGenerateImage}
                  isGeneratingImage={isGeneratingImage}
                />
              )}
              {bottomTab === 'animatic' && (
                <AnimaticTimeline shots={shots} />
              )}
            </div>
          </div>

          {/* BOTTOM PANEL RESIZER HANDLE */}
          <div 
            onMouseDown={startResizeBottom}
            className="h-1 bg-border/40 hover:bg-amber-500/60 transition-colors cursor-row-resize shrink-0 z-10"
          />
        </div>

        {/* RIGHT RESIZER DIVIDER BAR */}
        <div 
          onMouseDown={startResizeRight}
          className="w-1 bg-border/40 hover:bg-amber-500/60 transition-colors cursor-col-resize self-stretch shrink-0 z-10"
        />

        {/* RIGHT COLUMN: Shot Planner V2 & advanced tools inspector */}
        <div style={{ width: `${rightWidth}px` }} className="flex flex-col border-l border-border shrink-0 bg-[#07070c]">
          {/* Tabs selector */}
          <div className="p-2 border-b border-border flex items-center space-x-1.5 overflow-x-auto bg-[#0a0a14] shrink-0">
            <button 
              onClick={() => setRightTab('shots')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${rightTab === 'shots' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            >
              Shot List
            </button>
            <button 
              onClick={() => setRightTab('continuity')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${rightTab === 'continuity' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            >
              Continuity
            </button>
            <button 
              onClick={() => setRightTab('monitor')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${rightTab === 'monitor' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            >
              Monitor
            </button>
            <button 
              onClick={() => setRightTab('planner')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${rightTab === 'planner' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            >
              Planner
            </button>
            <button 
              onClick={() => setRightTab('rag')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${rightTab === 'rag' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            >
              RAG Search
            </button>
            <button 
              onClick={() => setRightTab('reference')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${rightTab === 'reference' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            >
              Reference
            </button>
            <button 
              onClick={() => setRightTab('plugins')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${rightTab === 'plugins' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            >
              Plugins
            </button>
            <button 
              onClick={() => setRightTab('qa')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${rightTab === 'qa' ? 'text-primary bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            >
              QA
            </button>
          </div>

          {/* Right tab panel contents */}
          <div className="flex-grow overflow-hidden flex flex-col">
            {rightTab === 'shots' && (
              <ShotPlanner 
                sceneId={selectedScene?.id}
                shots={shots}
                onAddShot={handleAddShot}
                onUpdateShot={handleUpdateShot}
                onDeleteShot={handleDeleteShot}
                onTriggerMuse={api.directorsMuse}
              />
            )}
            {rightTab === 'continuity' && (
              <ContinuityPanel 
                sceneId={selectedScene?.id}
                onRefreshProject={fetchProjectData}
              />
            )}
            {rightTab === 'monitor' && (
              <DirectorMonitor 
                shot={shots.length > 0 ? shots[0] : undefined} // comparing alternatives for the first shot
                onApplyOption={(updates) => {
                  if (shots.length > 0) {
                    handleUpdateShot(shots[0].id, updates);
                  }
                }}
              />
            )}
            {rightTab === 'planner' && (
              <ProductionPlanner projectId={projectId} />
            )}
            {rightTab === 'rag' && (
              <RAGSearch projectId={projectId} />
            )}
            {rightTab === 'reference' && (
              <ReferenceLibrary />
            )}
            {rightTab === 'plugins' && (
              <PluginsContainer />
            )}
            {rightTab === 'qa' && (
              <QADashboard />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
