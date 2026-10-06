'use client';

import React, { useState } from 'react';
import { Character, api } from '../../lib/api';
import { Users, Plus, Edit, Trash2, Shield, Eye, Settings, Image as ImageIcon, Lock, LockOpen, Wand2 } from 'lucide-react';
import { RelationshipGraph } from '../relationship-graph/relationship-graph';


interface CharacterBibleProps {
  projectId: string;
  characters?: Character[];
  allCharacters?: Character[]; // for relationship binding
  onRefresh: () => void;
  onLockReference?: (characterId: string, files?: File[]) => Promise<Character | void>;
}

export function CharacterBible({ projectId, characters = [], allCharacters = [], onRefresh, onLockReference }: CharacterBibleProps) {
  const [editingChar, setEditingChar] = useState<Character | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newName, setNewName] = useState('');

  // Dialog State fields
  const [charName, setCharName] = useState('');
  const [charAge, setCharAge] = useState<number | ''>('');
  const [charDesc, setCharDesc] = useState('');
  const [charBackstory, setCharBackstory] = useState('');
  const [charPersonality, setCharPersonality] = useState('');
  const [charWeakness, setCharWeakness] = useState('');
  const [charMotivation, setCharMotivation] = useState('');
  const [charFear, setCharFear] = useState('');
  const [charImage, setCharImage] = useState('');
  const [charTraits, setCharTraits] = useState<string[]>([]);
  const [newTrait, setNewTrait] = useState('');

  // Relationship bindings: key = character_id, value = type
  const [charRels, setCharRels] = useState<Record<string, string>>({});

  // Stage 6: reference-lock state
  const [lockFiles, setLockFiles] = useState<File[]>([]);
  const [isLocking, setIsLocking] = useState(false);
  const [lockError, setLockError] = useState<string | null>(null);

  const parseJSON = (str?: string, fallback: any = []) => {
    if (!str) return fallback;
    try {
      return JSON.parse(str);
    } catch {
      return fallback;
    }
  };

  const handleOpenEdit = (char: Character) => {
    setEditingChar(char);
    setCharName(char.name);
    setCharAge(char.age !== undefined && char.age !== null ? char.age : '');
    setCharDesc(char.description || '');
    setCharBackstory(char.backstory || '');
    setCharPersonality(char.personality || '');
    setCharWeakness(char.weakness || '');
    setCharMotivation(char.motivation || '');
    setCharFear(char.fear || '');
    setCharImage(char.reference_image_url || '');
    setCharTraits(parseJSON(char.traits, []));
    setCharRels(parseJSON(char.relationships, {}));
    setLockFiles([]);
    setLockError(null);
    setIsModalOpen(true);
  };

  const handleLockFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setLockFiles(Array.from(e.target.files).slice(0, 4));
    }
  };

  const handleLockClick = async () => {
    if (!onLockReference || !editingChar) return;
    setIsLocking(true);
    setLockError(null);
    try {
      const updated = await onLockReference(editingChar.id, lockFiles.length > 0 ? lockFiles : undefined);
      if (updated) setEditingChar(updated);
      setLockFiles([]);
    } catch (e: any) {
      setLockError(e.message || 'Failed to lock character reference.');
    } finally {
      setIsLocking(false);
    }
  };

  const handleAddCharacter = async () => {
    const name = prompt("Enter new character name:");
    if (!name || !name.trim()) return;
    try {
      await api.createCharacter(projectId, name.trim());
      onRefresh();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteCharacter = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to remove this character from the bible?")) {
      try {
        await api.deleteCharacter(id);
        onRefresh();
      } catch (e) {
        console.error(e);
      }
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingChar) return;

    try {
      await api.updateCharacter(editingChar.id, {
        name: charName,
        age: charAge === '' ? undefined : Number(charAge),
        description: charDesc,
        backstory: charBackstory,
        personality: charPersonality,
        weakness: charWeakness,
        motivation: charMotivation,
        fear: charFear,
        reference_image_url: charImage,
        traits: JSON.stringify(charTraits),
        relationships: JSON.stringify(charRels)
      });
      setIsModalOpen(false);
      setEditingChar(null);
      onRefresh();
    } catch (e) {
      console.error("Failed to update character", e);
    }
  };

  const addTrait = () => {
    if (newTrait.trim() && !charTraits.includes(newTrait.trim())) {
      setCharTraits([...charTraits, newTrait.trim()]);
      setNewTrait('');
    }
  };

  const removeTrait = (idx: number) => {
    setCharTraits(charTraits.filter((_, i) => i !== idx));
  };

  const handleRelationshipChange = (targetId: string, value: string) => {
    setCharRels(prev => {
      const updated = { ...prev };
      if (!value) {
        delete updated[targetId];
      } else {
        updated[targetId] = value;
      }
      return updated;
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-[10px] uppercase tracking-wider text-gray-500 font-bold flex items-center space-x-1.5">
          <Users size={12} className="text-purple-400" />
          <span>Character Profiles</span>
        </h4>
        <button
          onClick={handleAddCharacter}
          className="flex items-center space-x-0.5 px-2 py-1 rounded bg-purple-900/40 hover:bg-purple-900 border border-purple-500/25 text-[10px] font-bold text-purple-300 hover:text-white cursor-pointer transition-colors"
        >
          <Plus size={10} />
          <span>Add Cast</span>
        </button>
      </div>

      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
        {characters.length > 0 ? (
          characters.map((char) => {
            const traits = parseJSON(char.traits, []);
            return (
              <div 
                key={char.id} 
                onClick={() => handleOpenEdit(char)}
                className="bg-[#0f0f1b] hover:bg-[#131325] border border-border/80 hover:border-purple-500/40 p-2.5 rounded-lg transition-all duration-150 cursor-pointer group text-left relative"
              >
                {char.reference_image_url && (
                  <div className="absolute right-3 top-3 w-8 h-8 rounded-full border border-border/80 overflow-hidden opacity-80 group-hover:opacity-100 transition-opacity">
                    <img src={char.reference_image_url} alt={char.name} className="w-full h-full object-cover" />
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-200 group-hover:text-purple-400 transition-colors flex items-center space-x-1">
                    <span>{char.name}</span>
                    {char.age && <span className="text-[9px] text-gray-500">({char.age})</span>}
                    {char.is_locked ? (
                      <span title="Reference locked"><Lock size={9} className="text-emerald-400" /></span>
                    ) : (
                      <span title="Not locked -- shots with this character will fail to generate"><LockOpen size={9} className="text-gray-600" /></span>
                    )}
                  </span>
                  <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity mr-8">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenEdit(char);
                      }}
                      className="p-1 hover:text-purple-400 rounded transition-colors"
                    >
                      <Edit size={10} />
                    </button>
                    <button
                      onClick={(e) => handleDeleteCharacter(char.id, e)}
                      className="p-1 hover:text-red-500 rounded transition-colors"
                    >
                      <Trash2 size={10} />
                    </button>
                  </div>
                </div>

                {char.description && (
                  <p className="text-[10px] text-gray-400 mt-1 leading-relaxed line-clamp-2 pr-10">{char.description}</p>
                )}

                {traits.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2.5">
                    {traits.slice(0, 3).map((t: string, idx: number) => (
                      <span key={idx} className="text-[8px] bg-secondary border border-border px-1.5 py-0.5 rounded text-gray-400">
                        {t}
                      </span>
                    ))}
                    {traits.length > 3 && (
                      <span className="text-[8px] text-gray-500 px-1 py-0.5">+{traits.length - 3}</span>
                    )}
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <p className="text-xs text-gray-500 text-center py-4">No characters detected. Outline the story to generate a cast.</p>
        )}
      </div>

      {/* Visual Relationship Graph */}
      {characters.length > 0 && (
        <div className="pt-2 border-t border-border/40">
          <RelationshipGraph 
            characters={characters} 
            onSelectCharacter={handleOpenEdit} 
          />
        </div>
      )}


      {/* Premium React Character Details Dialog Modal */}
      {isModalOpen && editingChar && (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-[100] p-4 backdrop-blur-md animate-fade-in">
          <form 
            onSubmit={handleSave}
            className="glass max-w-2xl w-full rounded-2xl overflow-hidden shadow-2xl border border-purple-500/30 bg-[#07070a]/95 flex flex-col max-h-[85vh] relative"
          >
            {/* Top Amber glow line */}
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-purple-500 to-transparent"></div>

            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-[#0a0a10]">
              <div className="flex items-center space-x-2">
                <Users className="text-purple-400" size={18} />
                <h3 className="font-bold text-gray-200 text-sm uppercase tracking-wider screenplay-font">
                  Cast Sheet: {editingChar.name}
                </h3>
              </div>
              <button 
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-gray-400 hover:text-white cursor-pointer"
              >
                <Plus className="rotate-45" size={20} />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-5 text-left text-xs text-gray-300">
              
              {/* Row 1: Name, Age, Image URL */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-1">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Character Name</label>
                  <input
                    type="text"
                    value={charName}
                    onChange={(e) => setCharName(e.target.value)}
                    required
                    className="w-full bg-[#0d0d15] border border-gray-800 rounded-lg p-2 text-gray-200 focus:outline-none focus:border-purple-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Age</label>
                  <input
                    type="number"
                    value={charAge}
                    onChange={(e) => setCharAge(e.target.value === '' ? '' : Number(e.target.value))}
                    className="w-full bg-[#0d0d15] border border-gray-800 rounded-lg p-2 text-gray-200 focus:outline-none focus:border-purple-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500 flex items-center space-x-1">
                    <ImageIcon size={10} />
                    <span>Reference Image URL</span>
                  </label>
                  <input
                    type="url"
                    value={charImage}
                    onChange={(e) => setCharImage(e.target.value)}
                    placeholder="https://..."
                    className="w-full bg-[#0d0d15] border border-gray-800 rounded-lg p-2 text-gray-200 focus:outline-none focus:border-purple-500/50"
                  />
                </div>
              </div>

              {/* Stage 6: Character Consistency Lock */}
              {onLockReference && (
                <div className="space-y-3 border border-purple-500/20 bg-purple-950/10 rounded-lg p-3.5">
                  <div className="flex items-center justify-between">
                    <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500 flex items-center space-x-1.5">
                      {editingChar.is_locked ? <Lock size={11} className="text-emerald-400" /> : <LockOpen size={11} className="text-gray-500" />}
                      <span>Character Consistency Lock (Stage 6)</span>
                    </label>
                    {editingChar.is_locked ? (
                      <span className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30">
                        LOCKED{editingChar.locked_seed ? ` · seed ${editingChar.locked_seed}` : ''}
                      </span>
                    ) : (
                      <span className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                        NOT LOCKED
                      </span>
                    )}
                  </div>

                  <p className="text-[10px] text-gray-500 leading-relaxed">
                    Locking freezes this character's identity for every shot they appear in. Upload 1-4 reference
                    photos to use those, or lock with none to auto-generate one and freeze its seed. Re-locking replaces
                    the current reference set.
                  </p>

                  {(() => {
                    const lockedPaths: string[] = parseJSON(editingChar.reference_image_paths, []);
                    if (lockedPaths.length === 0) return null;
                    const backendBaseUrl = 'http://localhost:8000';
                    return (
                      <div className="flex items-center space-x-2">
                        {lockedPaths.map((p, idx) => (
                          <img
                            key={idx}
                            src={p.startsWith('http') ? p : `${backendBaseUrl}${p}`}
                            alt={`Locked reference ${idx + 1}`}
                            className="w-12 h-12 rounded object-cover border border-emerald-500/30"
                          />
                        ))}
                      </div>
                    );
                  })()}

                  <div className="flex items-center space-x-2">
                    <label className="flex-1 flex items-center justify-center px-2 py-1.5 bg-[#0d0d15] border border-dashed border-gray-700 hover:border-purple-500/50 rounded cursor-pointer text-[10px] text-gray-400 hover:text-gray-200 transition-colors">
                      <span>{lockFiles.length > 0 ? `${lockFiles.length} photo(s) selected` : 'Choose up to 4 reference photos (optional)'}</span>
                      <input type="file" accept="image/*" multiple onChange={handleLockFilesChange} className="hidden" />
                    </label>
                    <button
                      type="button"
                      onClick={handleLockClick}
                      disabled={isLocking}
                      className="flex items-center space-x-1 px-3 py-1.5 rounded bg-purple-600 hover:bg-purple-500 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed text-white font-bold text-[10px] cursor-pointer transition-colors shrink-0"
                    >
                      <Wand2 size={11} className={isLocking ? "animate-pulse" : ""} />
                      <span>{isLocking ? "Locking..." : editingChar.is_locked ? "Re-lock" : "Lock Reference"}</span>
                    </button>
                  </div>
                  {lockError && <p className="text-[10px] text-red-400">{lockError}</p>}
                </div>
              )}

              {/* Row 2: Description, Backstory */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Logline Description</label>
                  <textarea
                    value={charDesc}
                    onChange={(e) => setCharDesc(e.target.value)}
                    className="w-full h-20 bg-[#0d0d15] border border-gray-800 rounded-lg p-2 text-gray-200 focus:outline-none focus:border-purple-500/50 resize-none leading-relaxed"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Backstory</label>
                  <textarea
                    value={charBackstory}
                    onChange={(e) => setCharBackstory(e.target.value)}
                    className="w-full h-20 bg-[#0d0d15] border border-gray-800 rounded-lg p-2 text-gray-200 focus:outline-none focus:border-purple-500/50 resize-none leading-relaxed"
                  />
                </div>
              </div>

              {/* Row 3: Personality, Weakness */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Personality & Demeanor</label>
                  <input
                    type="text"
                    value={charPersonality}
                    onChange={(e) => setCharPersonality(e.target.value)}
                    className="w-full bg-[#0d0d15] border border-gray-800 rounded-lg p-2.5 text-gray-200 focus:outline-none focus:border-purple-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Core Weakness</label>
                  <input
                    type="text"
                    value={charWeakness}
                    onChange={(e) => setCharWeakness(e.target.value)}
                    className="w-full bg-[#0d0d15] border border-gray-800 rounded-lg p-2.5 text-gray-200 focus:outline-none focus:border-purple-500/50"
                  />
                </div>
              </div>

              {/* Row 4: Motivation, Fear */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Primary Motivation</label>
                  <input
                    type="text"
                    value={charMotivation}
                    onChange={(e) => setCharMotivation(e.target.value)}
                    className="w-full bg-[#0d0d15] border border-gray-800 rounded-lg p-2.5 text-gray-200 focus:outline-none focus:border-purple-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Greatest Fear</label>
                  <input
                    type="text"
                    value={charFear}
                    onChange={(e) => setCharFear(e.target.value)}
                    className="w-full bg-[#0d0d15] border border-gray-800 rounded-lg p-2.5 text-gray-200 focus:outline-none focus:border-purple-500/50"
                  />
                </div>
              </div>

              {/* Row 5: Traits Tags */}
              <div className="space-y-2">
                <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Traits tags</label>
                <div className="flex flex-wrap gap-1.5 p-2 bg-[#0a0a0f] border border-gray-900 rounded-lg">
                  {charTraits.map((t, idx) => (
                    <span 
                      key={idx} 
                      className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-secondary text-gray-300 font-semibold border border-border"
                    >
                      <span>{t}</span>
                      <button 
                        type="button" 
                        onClick={() => removeTrait(idx)}
                        className="hover:text-red-500 text-[10px] ml-1.5"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <div className="inline-flex items-center space-x-1 pl-1">
                    <input
                      type="text"
                      placeholder="Add trait..."
                      value={newTrait}
                      onChange={(e) => setNewTrait(e.target.value)}
                      className="bg-transparent text-gray-300 w-24 border-b border-border/40 focus:border-purple-500 focus:outline-none placeholder-gray-600 text-xs"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addTrait();
                        }
                      }}
                    />
                    <button 
                      type="button" 
                      onClick={addTrait}
                      className="text-[10px] text-purple-400 font-bold hover:text-white"
                    >
                      +
                    </button>
                  </div>
                </div>
              </div>

              {/* Row 6: Relationship Bindings */}
              <div className="space-y-2 border-t border-border/40 pt-4">
                <label className="text-[9px] font-bold uppercase tracking-wider text-gray-500">Character Connections / Bonds</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[140px] overflow-y-auto pr-1">
                  {allCharacters.filter(c => c.id !== editingChar.id).map((other) => {
                    const currentVal = charRels[other.id] || '';
                    return (
                      <div key={other.id} className="flex items-center justify-between p-2 bg-[#09090f] border border-border/50 rounded-lg">
                        <span className="font-semibold text-gray-300">{other.name}</span>
                        <select
                          value={currentVal}
                          onChange={(e) => handleRelationshipChange(other.id, e.target.value)}
                          className="bg-[#0f0f1b] border border-border rounded px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-purple-500"
                        >
                          <option value="">No Bond</option>
                          <option value="ally">Ally</option>
                          <option value="enemy">Enemy</option>
                          <option value="mentor">Mentor</option>
                          <option value="love_interest">Love Interest</option>
                        </select>
                      </div>
                    );
                  })}
                </div>
              </div>

            </div>

            <div className="px-6 py-4 border-t border-border bg-[#0a0a10] flex justify-end space-x-2">
              <button 
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-1.5 rounded-lg bg-secondary hover:bg-muted border border-border text-gray-300 hover:text-white font-semibold text-xs transition-colors cursor-pointer"
              >
                Close
              </button>
              <button 
                type="submit"
                className="px-4 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 text-white font-bold text-xs shadow-md transition-colors cursor-pointer"
              >
                Save Changes
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
