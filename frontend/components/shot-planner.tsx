'use client';

import React, { useState } from 'react';
import { Plus, Trash, Sparkles, Wand2, ArrowUpDown, X, CheckSquare, Square, Palette, Layers, Clock, MessageSquareText, AlertTriangle } from 'lucide-react';
import { Shot, api } from '../lib/api';

interface ShotPlannerProps {
  sceneId?: string;
  shots: Shot[];
  onAddShot: () => void;
  onUpdateShot: (id: string, updates: Partial<Shot>) => void;
  onDeleteShot: (id: string) => void;
  onTriggerMuse: (shotId: string, notes: string, style?: string) => Promise<any>;
  onGenerateShotPlan?: (sceneId: string) => Promise<void>;
  onEditShot?: (shotId: string, instruction: string) => Promise<void>;
}

type SortField = 'shot_number' | 'shooting_order' | 'duration' | 'shot_size' | 'lens' | 'lighting';
type SortOrder = 'asc' | 'desc';
type GroupingField = 'none' | 'location_order' | 'day_night';

export function ShotPlanner({ sceneId, shots, onAddShot, onUpdateShot, onDeleteShot, onTriggerMuse, onGenerateShotPlan, onEditShot }: ShotPlannerProps) {
  const [editingCell, setEditingCell] = useState<{ id: string; field: keyof Shot } | null>(null);
  const [editValue, setEditValue] = useState('');
  const [filterText, setFilterText] = useState('');
  const [sortField, setSortField] = useState<SortField>('shot_number');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [groupField, setGroupField] = useState<GroupingField>('none');
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);

  // Stage 10: natural-language edit
  const [nlEditShotId, setNlEditShotId] = useState<string | null>(null);
  const [nlInstruction, setNlInstruction] = useState('');
  const [isApplyingEdit, setIsApplyingEdit] = useState(false);

  // Selection
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  
  // Director's muse modal
  const [selectedStyle, setSelectedStyle] = useState('Standard');
  const [museData, setMuseData] = useState<any>(null);
  const [historyData, setHistoryData] = useState<any[]>([]);
  const [isMusing, setIsMusing] = useState<string | null>(null);
  const [selectedMuseShotId, setSelectedMuseShotId] = useState<string | null>(null);
  const [showMuseModal, setShowMuseModal] = useState(false);

  const startEditing = (shot: Shot, field: keyof Shot) => {
    setEditingCell({ id: shot.id, field });
    setEditValue((shot[field] as string || '').toString());
  };

  const saveEdit = (id: string, field: keyof Shot) => {
    if (editingCell) {
      let finalVal: any = editValue;
      if (field === 'shot_number' || field === 'shooting_order' || field === 'duration') {
        finalVal = parseInt(editValue) || 0;
      }
      onUpdateShot(id, { [field]: finalVal });
      setEditingCell(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, id: string, field: keyof Shot) => {
    if (e.key === 'Enter') {
      saveEdit(id, field);
    } else if (e.key === 'Escape') {
      setEditingCell(null);
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === sortedShots.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(sortedShots.map(s => s.id));
    }
  };

  const toggleSelectRow = (id: string) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(rowId => rowId !== id) : [...prev, id]
    );
  };

  const handleBatchUpdate = async (updates: Partial<Shot>) => {
    if (selectedIds.length === 0) return;
    try {
      await api.batchUpdateShots(selectedIds, updates);
      selectedIds.forEach(id => {
        onUpdateShot(id, updates);
      });
      setSelectedIds([]);
    } catch (err) {
      console.error("Batch update failed", err);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.length === 0) return;
    try {
      for (const id of selectedIds) {
        await api.deleteShot(id);
        onDeleteShot(id);
      }
      setSelectedIds([]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGeneratePlanClick = async () => {
    if (!sceneId || !onGenerateShotPlan) return;
    if (shots.length > 0 && !confirm(`This replaces all ${shots.length} existing shot(s) in this scene with a freshly generated plan. Continue?`)) {
      return;
    }
    setIsGeneratingPlan(true);
    try {
      await onGenerateShotPlan(sceneId);
    } catch (err) {
      console.error(err);
    } finally {
      setIsGeneratingPlan(false);
    }
  };

  const handleApplyNlEdit = async () => {
    if (!nlEditShotId || !nlInstruction.trim() || !onEditShot) return;
    setIsApplyingEdit(true);
    try {
      await onEditShot(nlEditShotId, nlInstruction.trim());
      setNlEditShotId(null);
      setNlInstruction('');
    } catch (err) {
      console.error(err);
    } finally {
      setIsApplyingEdit(false);
    }
  };

  const loadHistory = async (shotId: string) => {
    try {
      const hist = await api.getMuseHistory(shotId);
      setHistoryData(hist || []);
    } catch (e) {
      console.error("Failed loading muse history", e);
    }
  };

  const handleMuseClick = async (shot: Shot) => {
    setIsMusing(shot.id);
    setSelectedMuseShotId(shot.id);
    try {
      const data = await onTriggerMuse(shot.id, shot.notes || "A dramatic film scene.", selectedStyle);
      setMuseData(data.alternatives);
      setShowMuseModal(true);
      await loadHistory(shot.id);
    } catch (err) {
      console.error(err);
    } finally {
      setIsMusing(null);
    }
  };

  const applyMuseOption = (option: any) => {
    if (selectedMuseShotId) {
      onUpdateShot(selectedMuseShotId, {
        shot_size: option.shot_size,
        angle: option.angle,
        movement: option.movement,
        lens: option.lens,
        lighting: option.lighting,
        emotion: option.emotion,
        color_palette: option.color_palette,
        visual_tip: option.visual_tip
      });
      setShowMuseModal(false);
    }
  };

  // Filter and sort logic
  const filteredShots = shots.filter(shot => {
    const text = filterText.toLowerCase();
    return (
      (shot.notes || '').toLowerCase().includes(text) ||
      (shot.shot_size || '').toLowerCase().includes(text) ||
      (shot.lens || '').toLowerCase().includes(text) ||
      (shot.lighting || '').toLowerCase().includes(text) ||
      (shot.location_order || '').toLowerCase().includes(text)
    );
  });

  const sortedShots = [...filteredShots].sort((a, b) => {
    let valA = a[sortField];
    let valB = b[sortField];

    if (typeof valA === 'number' && typeof valB === 'number') {
      return sortOrder === 'asc' ? valA - valB : valB - valA;
    }

    valA = (valA || '').toString().toLowerCase();
    valB = (valB || '').toString().toLowerCase();

    if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
    if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  // Calculate Total Duration
  const totalDuration = shots.reduce((acc, shot) => acc + (shot.duration || 0), 0);
  const formatDuration = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  // Group shots logic
  const groupedShots: { [key: string]: Shot[] } = {};
  if (groupField !== 'none') {
    sortedShots.forEach(shot => {
      const val = (shot[groupField] as string) || "Not Defined";
      if (!groupedShots[val]) groupedShots[val] = [];
      groupedShots[val].push(shot);
    });
  }

  if (!sceneId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-500 bg-[#07070c] p-6 h-full border-l border-border">
        <p className="text-sm font-semibold text-center">Select a scene to see shot list</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07070c] border-l border-border overflow-hidden select-none relative">
      {/* Top Header */}
      <div className="p-3 border-b border-border bg-[#0d0d15]/80 flex flex-col space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
              Shot Planner V2 ({shots.length})
            </span>
            <select
              value={selectedStyle}
              onChange={(e) => setSelectedStyle(e.target.value)}
              className="bg-[#0c0c14] border border-border/80 rounded px-2.5 py-1 text-[10px] text-amber-500 font-bold focus:outline-none focus:border-amber-500 cursor-pointer"
            >
              <option value="Standard">Standard Style</option>
              <option value="Kubrick">Kubrick Preset</option>
              <option value="Fincher">Fincher Preset</option>
              <option value="Tarantino">Tarantino Preset</option>
              <option value="Scorsese">Scorsese Preset</option>
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-1 text-[9px] bg-black/40 px-2 py-1 rounded border border-white/5 font-mono text-amber-500 font-bold">
              <Clock size={11} />
              <span>Reel: {formatDuration(totalDuration)}</span>
            </div>
            {onGenerateShotPlan && (
              <button
                onClick={handleGeneratePlanClick}
                disabled={isGeneratingPlan}
                title="Stage 4/5: auto-divides this scene into shots with a full cinematography plan (replaces existing shots)"
                className="flex items-center space-x-1 px-2 py-1 rounded bg-blue-600 text-white font-semibold text-[10px] hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed transition-all cursor-pointer"
              >
                <Layers size={11} className={isGeneratingPlan ? "animate-pulse" : ""} />
                <span>{isGeneratingPlan ? "Generating plan..." : "Generate Shot Plan"}</span>
              </button>
            )}
            <button
              onClick={onAddShot}
              className="flex items-center space-x-1 px-2 py-1 rounded bg-primary text-black font-semibold text-[10px] hover:bg-primary/90 transition-all cursor-pointer"
            >
              <Plus size={11} />
              <span>Add Shot</span>
            </button>
          </div>
        </div>

        {/* Sorting & Grouping Filter Bar */}
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="Search notes, lens, locations..."
            className="flex-1 bg-input border border-border rounded px-2.5 py-1 text-[10px] text-gray-200 focus:outline-none focus:border-primary placeholder-gray-600 font-sans"
          />
          
          <select
            value={groupField}
            onChange={(e) => setGroupField(e.target.value as GroupingField)}
            className="bg-[#0c0c14] border border-border/80 rounded px-2 py-1 text-[10px] text-gray-400 focus:outline-none cursor-pointer"
          >
            <option value="none">Group: None</option>
            <option value="location_order">Group: Location</option>
            <option value="day_night">Group: Day/Night</option>
          </select>
        </div>
      </div>

      {/* Spreadsheet grid */}
      <div className="flex-1 overflow-auto pb-16">
        <table className="w-full text-left border-collapse text-[11px] font-sans">
          <thead>
            <tr className="bg-secondary/40 border-b border-border text-gray-400 uppercase font-semibold text-[9px]">
              <th className="p-2 border-r border-border/40 w-8 text-center">
                <button onClick={toggleSelectAll} className="p-0.5 rounded text-gray-400 hover:text-white cursor-pointer">
                  {selectedIds.length === sortedShots.length && sortedShots.length > 0 ? (
                    <CheckSquare size={12} className="text-primary" />
                  ) : (
                    <Square size={12} />
                  )}
                </button>
              </th>
              <th className="p-2 border-r border-border/40 w-12 text-center cursor-pointer hover:bg-secondary" onClick={() => handleSort('shot_number')}>
                <div className="flex items-center justify-center space-x-0.5">
                  <span>#</span>
                  <ArrowUpDown size={8} />
                </div>
              </th>
              <th className="p-2 border-r border-border/40 w-12 text-center cursor-pointer hover:bg-secondary" onClick={() => handleSort('shooting_order')}>
                <div className="flex items-center justify-center space-x-0.5">
                  <span>Shoot</span>
                  <ArrowUpDown size={8} />
                </div>
              </th>
              <th className="p-2 border-r border-border/40 w-24">Location</th>
              <th className="p-2 border-r border-border/40 w-20">Day/Night</th>
              <th className="p-2 border-r border-border/40 w-14 text-center cursor-pointer hover:bg-secondary" onClick={() => handleSort('duration')}>
                <div className="flex items-center justify-center space-x-0.5">
                  <span>Time</span>
                  <ArrowUpDown size={8} />
                </div>
              </th>
              <th className="p-2 border-r border-border/40 w-16 cursor-pointer hover:bg-secondary" onClick={() => handleSort('shot_size')}>
                <div className="flex items-center space-x-0.5">
                  <span>Size</span>
                  <ArrowUpDown size={8} />
                </div>
              </th>
              <th className="p-2 border-r border-border/40 w-20">Lens</th>
              <th className="p-2 border-r border-border/40 w-20">Lighting</th>
              <th className="p-2 border-r border-border/40 w-16 text-center">Status</th>
              <th className="p-2 border-r border-border/40">Notes</th>
              <th className="p-2 w-14 text-center">Muse</th>
            </tr>
          </thead>

          {groupField === 'none' ? (
            <tbody>
              {sortedShots.length === 0 ? (
                <tr>
                  <td colSpan={12} className="p-8 text-center text-gray-500">
                    No shots defined for this scene. Click "Add Shot" above to begin.
                  </td>
                </tr>
              ) : (
                sortedShots.map((shot) => renderRow(shot))
              )}
            </tbody>
          ) : (
            Object.keys(groupedShots).map(groupName => (
              <React.Fragment key={groupName}>
                <tbody>
                  <tr className="bg-black/30 border-b border-border/60">
                    <td colSpan={12} className="p-1.5 px-3 font-bold text-amber-500/80 font-mono text-[9px] uppercase tracking-wider">
                      {groupName} ({groupedShots[groupName].length} Shots)
                    </td>
                  </tr>
                  {groupedShots[groupName].map(shot => renderRow(shot))}
                </tbody>
              </React.Fragment>
            ))
          )}
        </table>
      </div>

      {/* Floating Action Batch Edit Toolbar */}
      {selectedIds.length > 0 && (
        <div className="absolute bottom-3 left-3 right-3 p-2 bg-[#0c0c16] rounded-lg border border-primary/20 shadow-2xl flex items-center justify-between z-40 animate-slide-up">
          <div className="flex items-center space-x-2 text-[10px]">
            <span className="bg-primary/10 text-primary font-bold px-2 py-0.5 rounded font-mono">
              {selectedIds.length} Selected
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <select
              onChange={(e) => handleBatchUpdate({ day_night: e.target.value })}
              className="bg-black/40 border border-white/5 rounded px-2 py-1 text-[9px] text-gray-300 outline-none"
              defaultValue=""
            >
              <option value="" disabled>Set Time</option>
              <option value="Day">Day</option>
              <option value="Night">Night</option>
              <option value="Dusk">Dusk</option>
              <option value="Dawn">Dawn</option>
            </select>

            <select
              onChange={(e) => handleBatchUpdate({ status: e.target.value })}
              className="bg-black/40 border border-white/5 rounded px-2 py-1 text-[9px] text-gray-300 outline-none"
              defaultValue=""
            >
              <option value="" disabled>Set Status</option>
              <option value="Pending">Pending</option>
              <option value="Filming">Filming</option>
              <option value="Completed">Completed</option>
            </select>

            <select
              onChange={(e) => handleBatchUpdate({ lens: e.target.value })}
              className="bg-black/40 border border-white/5 rounded px-2 py-1 text-[9px] text-gray-300 outline-none"
              defaultValue=""
            >
              <option value="" disabled>Set Lens</option>
              <option value="50mm">50mm</option>
              <option value="24mm">24mm</option>
              <option value="85mm">85mm</option>
            </select>

            {/* Color labeling */}
            <div className="flex items-center space-x-1 bg-black/40 px-1.5 py-0.5 rounded border border-white/5">
              {["#ef4444", "#3b82f6", "#10b981", "#f59e0b"].map(color => (
                <button
                  key={color}
                  onClick={() => handleBatchUpdate({ color_label: color })}
                  style={{ backgroundColor: color }}
                  className="w-3.5 h-3.5 rounded-full hover:scale-110 active:scale-95 transition-transform border border-white/5 cursor-pointer"
                />
              ))}
            </div>

            <button
              onClick={handleBatchDelete}
              className="flex items-center space-x-0.5 px-2 py-1 rounded bg-red-600/90 text-white font-bold text-[9px] hover:bg-red-700 cursor-pointer"
            >
              <Trash size={10} />
              <span>Delete</span>
            </button>

            <button
              onClick={() => setSelectedIds([])}
              className="p-1 rounded text-gray-500 hover:text-white transition-colors cursor-pointer"
            >
              <X size={12} />
            </button>
          </div>
        </div>
      )}

      {/* Row Renderer helper function */}
      {showMuseModal && museData && renderMuseModal()}
    </div>
  );

  function renderRow(shot: Shot) {
    const isSelected = selectedIds.includes(shot.id);
    return (
      <tr key={shot.id} className={`border-b border-border hover:bg-secondary/15 transition-colors group ${isSelected ? 'bg-primary/5' : ''}`}>
        {/* Selection Checkbox */}
        <td className="p-2 border-r border-border/40 text-center">
          <button onClick={() => toggleSelectRow(shot.id)} className="p-0.5 rounded text-gray-500 hover:text-white cursor-pointer">
            {isSelected ? (
              <CheckSquare size={12} className="text-primary" />
            ) : (
              <Square size={12} />
            )}
          </button>
        </td>

        {/* # Shot number */}
        <td className="p-2 border-r border-border/40 text-center font-bold text-primary flex items-center justify-center space-x-1.5 min-h-[2.2rem]">
          {shot.color_label && (
            <div style={{ backgroundColor: shot.color_label }} className="w-1.5 h-1.5 rounded-full shrink-0" />
          )}
          {!!shot.needs_review && (
            <span title="Stage 9: flagged for continuity review" className="shrink-0"><AlertTriangle size={9} className="text-amber-500" /></span>
          )}
          {editingCell?.id === shot.id && editingCell?.field === 'shot_number' ? (
            <input
              type="number"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => saveEdit(shot.id, 'shot_number')}
              onKeyDown={(e) => handleKeyDown(e, shot.id, 'shot_number')}
              className="w-10 bg-input text-center text-xs text-white border border-primary outline-none py-0.5 rounded"
              autoFocus
            />
          ) : (
            <span onClick={() => startEditing(shot, 'shot_number')} className="cursor-pointer select-none">
              {shot.shot_number}
            </span>
          )}
        </td>

        {/* Shooting Order */}
        <td className="p-2 border-r border-border/40 text-center font-semibold text-gray-300">
          {editingCell?.id === shot.id && editingCell?.field === 'shooting_order' ? (
            <input
              type="number"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => saveEdit(shot.id, 'shooting_order')}
              onKeyDown={(e) => handleKeyDown(e, shot.id, 'shooting_order')}
              className="w-10 bg-input text-center text-xs text-white border border-primary outline-none py-0.5 rounded"
              autoFocus
            />
          ) : (
            <span onClick={() => startEditing(shot, 'shooting_order')} className="cursor-pointer select-none">
              {shot.shooting_order || 0}
            </span>
          )}
        </td>

        {/* Location Order */}
        <td className="p-2 border-r border-border/40 text-gray-300">
          {editingCell?.id === shot.id && editingCell?.field === 'location_order' ? (
            <input
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => saveEdit(shot.id, 'location_order')}
              onKeyDown={(e) => handleKeyDown(e, shot.id, 'location_order')}
              className="w-full bg-input text-xs text-white border border-primary outline-none px-1.5 py-0.5 rounded"
              autoFocus
            />
          ) : (
            <span onClick={() => startEditing(shot, 'location_order')} className="cursor-pointer block min-h-[1rem] select-none truncate">
              {shot.location_order || <span className="text-gray-700 italic">Location TBD</span>}
            </span>
          )}
        </td>

        {/* Day / Night */}
        <td className="p-2 border-r border-border/40 text-gray-300">
          {editingCell?.id === shot.id && editingCell?.field === 'day_night' ? (
            <select
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => {
                onUpdateShot(shot.id, { day_night: editValue });
                setEditingCell(null);
              }}
              className="w-full bg-input text-xs text-white border border-primary outline-none py-0.5 rounded"
              autoFocus
            >
              <option value="Day">Day</option>
              <option value="Night">Night</option>
              <option value="Dusk">Dusk</option>
              <option value="Dawn">Dawn</option>
            </select>
          ) : (
            <span onClick={() => {
              setEditingCell({ id: shot.id, field: 'day_night' });
              setEditValue(shot.day_night || 'Day');
            }} className="cursor-pointer block min-h-[1rem] select-none font-semibold">
              {shot.day_night || 'Day'}
            </span>
          )}
        </td>

        {/* Duration */}
        <td className="p-2 border-r border-border/40 text-center font-mono text-gray-400">
          {editingCell?.id === shot.id && editingCell?.field === 'duration' ? (
            <input
              type="number"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => saveEdit(shot.id, 'duration')}
              onKeyDown={(e) => handleKeyDown(e, shot.id, 'duration')}
              className="w-12 bg-input text-center text-xs text-white border border-primary outline-none py-0.5 rounded font-mono"
              autoFocus
            />
          ) : (
            <span onClick={() => startEditing(shot, 'duration')} className="cursor-pointer block select-none">
              {shot.duration || 0}s
            </span>
          )}
        </td>

        {/* Size */}
        <td className="p-2 border-r border-border/40 text-gray-300">
          {editingCell?.id === shot.id && editingCell?.field === 'shot_size' ? (
            <input
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => saveEdit(shot.id, 'shot_size')}
              onKeyDown={(e) => handleKeyDown(e, shot.id, 'shot_size')}
              className="w-full bg-input text-xs text-white border border-primary outline-none px-1 py-0.5 rounded"
              autoFocus
            />
          ) : (
            <span onClick={() => startEditing(shot, 'shot_size')} className="cursor-pointer block min-h-[1rem] select-none">
              {shot.shot_size || <span className="text-gray-700 italic">MS</span>}
            </span>
          )}
        </td>

        {/* Lens */}
        <td className="p-2 border-r border-border/40 text-gray-300">
          {editingCell?.id === shot.id && editingCell?.field === 'lens' ? (
            <input
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => saveEdit(shot.id, 'lens')}
              onKeyDown={(e) => handleKeyDown(e, shot.id, 'lens')}
              className="w-full bg-input text-xs text-white border border-primary outline-none px-1 py-0.5 rounded"
              autoFocus
            />
          ) : (
            <span onClick={() => startEditing(shot, 'lens')} className="cursor-pointer block min-h-[1rem] select-none">
              {shot.lens || <span className="text-gray-700 italic">50mm</span>}
            </span>
          )}
        </td>

        {/* Lighting */}
        <td className="p-2 border-r border-border/40 text-gray-300">
          {editingCell?.id === shot.id && editingCell?.field === 'lighting' ? (
            <input
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => saveEdit(shot.id, 'lighting')}
              onKeyDown={(e) => handleKeyDown(e, shot.id, 'lighting')}
              className="w-full bg-input text-xs text-white border border-primary outline-none px-1 py-0.5 rounded"
              autoFocus
            />
          ) : (
            <span onClick={() => startEditing(shot, 'lighting')} className="cursor-pointer block min-h-[1rem] select-none">
              {shot.lighting || <span className="text-gray-700 italic">Natural</span>}
            </span>
          )}
        </td>

        {/* Status */}
        <td className="p-2 border-r border-border/40 text-center">
          {editingCell?.id === shot.id && editingCell?.field === 'status' ? (
            <select
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => {
                onUpdateShot(shot.id, { status: editValue });
                setEditingCell(null);
              }}
              className="bg-input text-white text-[10px] outline-none border border-primary rounded"
              autoFocus
            >
              <option value="Pending">Pending</option>
              <option value="Filming">Filming</option>
              <option value="Completed">Completed</option>
            </select>
          ) : (
            <span
              onClick={() => {
                setEditingCell({ id: shot.id, field: 'status' });
                setEditValue(shot.status || 'Pending');
              }}
              className={`px-1.5 py-0.5 rounded text-[8px] font-bold cursor-pointer inline-block ${
                shot.status === 'Completed'
                  ? 'bg-emerald-950 text-emerald-400'
                  : shot.status === 'Filming'
                  ? 'bg-sky-950 text-sky-400'
                  : 'bg-zinc-800 text-zinc-400'
              }`}
            >
              {shot.status || 'Pending'}
            </span>
          )}
        </td>

        {/* Notes */}
        <td className="p-2 border-r border-border/40 text-gray-300">
          {editingCell?.id === shot.id && editingCell?.field === 'notes' ? (
            <input
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={() => saveEdit(shot.id, 'notes')}
              onKeyDown={(e) => handleKeyDown(e, shot.id, 'notes')}
              className="w-full bg-input text-xs text-white border border-primary outline-none px-2 py-0.5 rounded"
              autoFocus
            />
          ) : (
            <span onClick={() => startEditing(shot, 'notes')} className="cursor-pointer block min-h-[1rem] select-none truncate">
              {shot.notes || <span className="text-gray-600 italic">Double-click to write notes...</span>}
            </span>
          )}
        </td>

        {/* Actions */}
        <td className="p-2 text-center relative">
          <div className="flex items-center justify-center space-x-1.5 opacity-40 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => handleMuseClick(shot)}
              disabled={isMusing !== null}
              title="Muse AI"
              className="p-1 rounded text-yellow-500 hover:bg-yellow-500/10 cursor-pointer"
            >
              <Sparkles size={11} className={isMusing === shot.id ? "animate-spin" : ""} />
            </button>
            {onEditShot && (
              <button
                onClick={() => { setNlEditShotId(shot.id); setNlInstruction(''); }}
                title="Stage 10: edit this shot in plain English (e.g. 'make this a low-angle shot')"
                className="p-1 rounded text-blue-400 hover:bg-blue-500/10 cursor-pointer"
              >
                <MessageSquareText size={11} />
              </button>
            )}
            <button
              onClick={() => onDeleteShot(shot.id)}
              title="Delete"
              className="p-1 rounded text-red-500 hover:bg-red-500/10 cursor-pointer"
            >
              <Trash size={11} />
            </button>
          </div>

          {nlEditShotId === shot.id && (
            <div className="absolute right-0 top-full mt-1 z-50 w-64 bg-[#0c0c16] border border-blue-500/30 rounded-lg shadow-2xl p-2.5 text-left space-y-2">
              <textarea
                value={nlInstruction}
                onChange={(e) => setNlInstruction(e.target.value)}
                placeholder="e.g. make this a low-angle shot, use a 50mm lens..."
                autoFocus
                className="w-full h-16 bg-input border border-border rounded p-1.5 text-[10px] text-gray-200 focus:outline-none focus:border-blue-500 placeholder-gray-600 resize-none"
              />
              <div className="flex justify-end space-x-1.5">
                <button
                  onClick={() => setNlEditShotId(null)}
                  className="px-2 py-1 rounded bg-secondary text-gray-400 hover:text-white text-[9px] font-bold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={handleApplyNlEdit}
                  disabled={isApplyingEdit || !nlInstruction.trim()}
                  className="px-2 py-1 rounded bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed text-white text-[9px] font-bold cursor-pointer"
                >
                  {isApplyingEdit ? "Applying + regenerating..." : "Apply"}
                </button>
              </div>
            </div>
          )}
        </td>
      </tr>
    );
  }

  function renderMuseModal() {
    return (
      <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4 backdrop-blur-md animate-fade-in">
        <div className="glass max-w-4xl w-full rounded-2xl overflow-hidden shadow-2xl border border-amber-500/20 bg-[#07070a] flex flex-col max-h-[90vh]">
          
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent"></div>

          <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-[#0a0a0f]">
            <div className="flex items-center space-x-2">
              <Wand2 className="text-amber-500 animate-pulse" size={18} />
              <h3 className="font-bold text-gray-200 text-sm uppercase tracking-wider screenplay-font">
                Director's Muse - Comparison Monitors
              </h3>
            </div>
            <button 
              onClick={() => setShowMuseModal(false)}
              className="text-gray-400 hover:text-amber-500 transition-colors p-1 rounded-full cursor-pointer"
              title="Close modal"
            >
              <X size={20} />
            </button>
          </div>

          <div className="p-6 overflow-y-auto space-y-6 text-left">
            <div>
              <span className="text-[9px] font-bold text-amber-500 uppercase tracking-widest block">ACTIVE STYLE PRESET</span>
              <p className="text-xs text-gray-300 font-semibold uppercase">{selectedStyle} Style</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {museData.map((option: any, idx: number) => (
                <div 
                  key={idx}
                  onClick={() => applyMuseOption(option)}
                  className="relative bg-[#0c0c14] border border-border/80 hover:border-amber-500/40 hover:bg-secondary/10 p-5 rounded-xl cursor-pointer transition-all duration-200 flex flex-col group shadow-lg"
                >
                  <div className="absolute inset-0 border border-transparent group-hover:border-amber-500/10 rounded-xl pointer-events-none"></div>

                  <div className="flex items-center justify-between mb-3 border-b border-border/30 pb-2">
                    <span className="text-[10px] font-extrabold text-amber-500 uppercase tracking-widest">Setup Monitor {idx + 1}</span>
                    <span className="text-[9px] bg-amber-500/10 text-amber-500 font-bold px-2 py-0.5 rounded border border-amber-500/25">
                      {option.shot_size}
                    </span>
                  </div>
                  
                  <div className="space-y-2 text-[11px] text-gray-400 flex-1 leading-relaxed">
                    <p><b className="text-gray-300">Angle:</b> {option.angle}</p>
                    <p><b className="text-gray-300">Lens:</b> {option.lens}</p>
                    <p><b className="text-gray-300">Movement:</b> {option.movement}</p>
                    <p><b className="text-gray-300">Lighting:</b> {option.lighting}</p>
                    <p><b className="text-gray-300">Color Palette:</b> {option.color_palette}</p>
                    <p className="text-[10px] text-gray-500 italic mt-3 border-t border-border/20 pt-2 leading-relaxed">
                      <b className="text-gray-400 not-italic block uppercase tracking-wider text-[8px] mb-0.5">Composition tip:</b> 
                      {option.visual_tip}
                    </p>
                  </div>
                  
                  <button className="w-full mt-5 py-2 bg-amber-500/10 text-amber-500 border border-amber-500/30 text-[10px] uppercase tracking-wider font-extrabold rounded-lg group-hover:bg-amber-500 group-hover:text-black group-hover:border-amber-500 transition-all duration-150 shadow-sm cursor-pointer">
                    Apply Setup
                  </button>
                </div>
              ))}
            </div>

            <div className="border-t border-border/60 pt-5 space-y-3">
              <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">
                Style History Tracker
              </h4>
              {historyData.length > 0 ? (
                <div className="space-y-3 max-h-[200px] overflow-y-auto pr-1">
                  {historyData.map((histItem, hIdx) => {
                    const histOpts = (() => {
                      try {
                        return JSON.parse(histItem.response).alternatives;
                      } catch {
                        return [];
                      }
                    })();
                    const dateText = new Date(histItem.timestamp).toLocaleTimeString();
                    return (
                      <div key={hIdx} className="bg-[#09090f] border border-border/60 p-3.5 rounded-xl space-y-3 text-left">
                        <div className="flex justify-between text-[10px] text-gray-500">
                          <span><b>Style:</b> <span className="text-amber-500/80 font-bold uppercase">{histItem.director_style}</span></span>
                          <span>{dateText}</span>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                          {histOpts.map((opt: any, optIdx: number) => (
                            <div 
                              key={optIdx}
                              onClick={() => applyMuseOption(opt)}
                              className="bg-[#0d0d15] hover:bg-secondary/20 border border-border/40 p-2.5 rounded-lg cursor-pointer text-[10px] text-gray-400 space-y-1 hover:border-amber-500/30 transition-colors"
                            >
                              <p className="font-bold text-gray-300">{opt.shot_size} - {opt.angle}</p>
                              <p className="line-clamp-1">{opt.movement} • {opt.lens}</p>
                              <p className="line-clamp-1 italic text-gray-500">{opt.lighting}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-[10px] text-gray-600 italic">No previous generation history logged for this shot.</p>
              )}
            </div>

          </div>

          <div className="px-6 py-3 border-t border-border bg-[#0a0a0f] flex justify-end">
            <button 
              onClick={() => setShowMuseModal(false)}
              className="px-4 py-1.5 rounded-lg bg-secondary text-gray-300 hover:text-white font-semibold text-xs border border-border transition-colors cursor-pointer"
            >
              Close Monitor
            </button>
          </div>
        </div>
      </div>
    );
  }
}
