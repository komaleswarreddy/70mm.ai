'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { Download, FileText, Image as ImageIcon, RefreshCw, Save, Settings2, Type, X } from 'lucide-react';
import { api, Board, BoardSettings, Project, Shot } from '../lib/api';

const BACKEND_BASE = 'http://localhost:8000';

const LEGEND_FIELDS: [string, string][] = [
  ['camera_style', 'Camera style'],
  ['colour_tone', 'Colour tone'],
  ['lighting', 'Lighting'],
  ['mood', 'Mood'],
  ['lens_guide', 'Lens guide'],
  ['notes', 'Notes'],
];

const TEXT_FIELDS: [keyof BoardSettings, string, string][] = [
  ['title', 'Title', 'e.g. YOURS, SITA'],
  ['title_native', 'Title in native script (shown instead of the title)', 'e.g. ఇట్లు, సీతామహాలక్ష్మి'],
  ['title_sub', 'Line under the title (handwritten)', 'e.g. Itlu, Sita Mahalakshmi · Letters from 1965'],
  ['title_roman', 'Romanised title (used in the credit line)', 'e.g. Itlu, Sita Mahalakshmi'],
  ['subtitle', 'Scenes box subtitle', 'e.g. The Letter — The Dance Hall'],
  ['period', 'Period', 'e.g. India, 1965'],
  ['tagline', 'Hero tagline (any script)', ''],
  ['tagline_translation', 'Tagline translation', ''],
  ['postmark_ring', 'Postmark ring text', 'e.g. KASHMIR · HYDERABAD · AIR MAIL · '],
  ['postmark_center', 'Postmark centre', 'e.g. 1965'],
  ['end_translation', 'End-card translation', ''],
  ['signature', 'End-card signature', ''],
  ['signature_roman', 'Signature, romanised', ''],
  ['end_stamp', 'End-card stamp', 'END OF BOARD 1 · TO BE CONTINUED'],
  ['credit', 'Credit line (bottom of sheet)', 'leave empty to auto-generate'],
];

async function downloadFile(url: string, filename: string) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  const blob = await res.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(href), 10_000);
}

// The backend writes a ~0.7 MB JPEG preview next to each 7200 px PNG; the
// modal shows that, the downloads stay full quality.
const previewPath = (png: string) => png.replace(/\.png$/, '_preview.jpg');

const errorMessage = (e: unknown) => (e instanceof Error ? e.message : String(e));

const lines = (v?: string[]) => (v || []).join('\n');
const toLines = (v: string) => v.split('\n').map((l) => l.trim()).filter(Boolean);

interface BoardStudioProps {
  projectId: string;
  boards: Board[];
  isComposing?: boolean;
  onRecompose: () => Promise<Board[] | void>;
  onClose: () => void;
}

export function BoardStudio({ projectId, boards: initialBoards, isComposing, onRecompose, onClose }: BoardStudioProps) {
  const [tab, setTab] = useState<'preview' | 'settings' | 'captions'>('preview');
  const [boards, setBoards] = useState<Board[]>(initialBoards);
  const [project, setProject] = useState<Project | null>(null);
  const [settings, setSettings] = useState<BoardSettings>({});
  const [captions, setCaptions] = useState<Record<string, { board_caption: string; board_dialogue: string }>>({});
  const [dirtyShots, setDirtyShots] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getProject(projectId).then((p) => {
      setProject(p);
      try {
        const parsed = p.board_legend_settings ? JSON.parse(p.board_legend_settings) : {};
        setSettings(parsed && typeof parsed === 'object' ? parsed : {});
      } catch {
        setSettings({});
      }
      const map: Record<string, { board_caption: string; board_dialogue: string }> = {};
      (p.scenes || []).forEach((s) => (s.shots || []).forEach((sh: Shot) => {
        map[sh.id] = { board_caption: sh.board_caption || '', board_dialogue: sh.board_dialogue || '' };
      }));
      setCaptions(map);
    }).catch((e) => setError(errorMessage(e)));
  }, [projectId]);

  const scenes = useMemo(
    () => [...(project?.scenes || [])].sort((a, b) => a.scene_number - b.scene_number),
    [project],
  );

  const baseName = (project?.title || 'storyboard').replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '');

  const saveAll = async () => {
    setError(null);
    setBusy('Saving…');
    await api.updateProject(projectId, { board_legend_settings: JSON.stringify(settings) } as Partial<Project>);
    for (const id of dirtyShots) {
      await api.updateShot(id, captions[id]);
    }
    setDirtyShots(new Set());
  };

  const saveAndRecompose = async () => {
    try {
      await saveAll();
      setBusy('Composing boards… (this can take a minute)');
      const result = await onRecompose();
      if (result) setBoards(result);
      setTab('preview');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  const download = async (b: Board, kind: 'pdf' | 'png') => {
    const path = kind === 'pdf' ? b.output_pdf_path : b.output_image_path;
    if (!path) return;
    setBusy(`Preparing ${kind.toUpperCase()}…`);
    try {
      await downloadFile(`${BACKEND_BASE}${path}?v=${encodeURIComponent(b.updated_at)}`, `${baseName}_board_${b.board_number}.${kind}`);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  const setField = (key: keyof BoardSettings, value: string) => setSettings((s) => ({ ...s, [key]: value }));

  // Portalled to <body>: the navbar uses backdrop-filter, which turns it into
  // the containing block for position:fixed children -- rendered in place,
  // this modal was squeezed into the 56px navbar strip and was invisible.
  if (typeof document === 'undefined') return null;
  return createPortal(
    <div className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-6" role="dialog" aria-modal="true" aria-label="Board studio">
      <div className="bg-[#0c0c16] border border-border rounded-xl shadow-2xl w-full max-w-7xl max-h-[92vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <div className="flex items-center space-x-1">
            {([['preview', 'Preview & download', ImageIcon], ['settings', 'Board settings', Settings2], ['captions', 'Captions', Type]] as const).map(([key, label, Icon]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border cursor-pointer ${tab === key ? 'bg-primary/15 text-primary border-primary/30' : 'text-gray-300 border-transparent hover:bg-white/5'}`}
              >
                <Icon size={13} /><span>{label}</span>
              </button>
            ))}
          </div>
          <div className="flex items-center space-x-3">
            {busy && <span className="text-[11px] text-primary animate-pulse">{busy}</span>}
            <button onClick={onClose} aria-label="Close" className="p-1.5 rounded hover:bg-white/10 text-gray-400 cursor-pointer"><X size={16} /></button>
          </div>
        </div>

        {error && <div className="mx-5 mt-3 px-3 py-2 rounded bg-red-500/10 border border-red-500/30 text-[11px] text-red-300">{error}</div>}

        <div className="flex-1 overflow-y-auto p-5">
          {tab === 'preview' && (
            boards.length === 0 ? (
              <p className="text-sm text-gray-400">No boards composed yet — no scenes found.</p>
            ) : (
              <div className="space-y-6">
                {boards.map((b) => (
                  <div key={b.id} className="border border-border rounded-lg overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-2 bg-white/[0.03] border-b border-border">
                      <div className="text-xs text-gray-200 font-semibold">
                        Board {b.board_number} <span className="text-gray-500 font-normal">· {b.title} · {b.length_label} · page {b.page_range_label}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <button onClick={() => download(b, 'pdf')} className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-primary text-black hover:opacity-90 cursor-pointer">
                          <FileText size={13} /><span>Download PDF (full quality)</span>
                        </button>
                        <button onClick={() => download(b, 'png')} className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-secondary text-gray-200 border border-border hover:bg-muted cursor-pointer">
                          <Download size={13} /><span>Download PNG (7200 px)</span>
                        </button>
                      </div>
                    </div>
                    {b.output_image_path && (
                      <a href={`${BACKEND_BASE}${b.output_image_path}?v=${encodeURIComponent(b.updated_at)}`} target="_blank" rel="noreferrer" title="Open full size">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={`${BACKEND_BASE}${previewPath(b.output_image_path)}?v=${encodeURIComponent(b.updated_at)}`} alt={`Board ${b.board_number}`} className="w-full h-auto block bg-[#f7f2e6]" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )
          )}

          {tab === 'settings' && (
            <div className="grid grid-cols-2 gap-4">
              {TEXT_FIELDS.map(([key, label, placeholder]) => (
                <label key={key} className="block">
                  <span className="text-[11px] text-gray-400">{label}</span>
                  <input
                    value={(settings[key] as string) || ''}
                    placeholder={placeholder}
                    onChange={(e) => setField(key, e.target.value)}
                    className="mt-1 w-full bg-black/40 border border-border rounded px-2.5 py-1.5 text-sm text-gray-100 focus:border-primary outline-none"
                  />
                </label>
              ))}
              <label className="block">
                <span className="text-[11px] text-gray-400">End-card lines (one per line, any script)</span>
                <textarea rows={3} value={lines(settings.end_lines)} onChange={(e) => setSettings((s) => ({ ...s, end_lines: toLines(e.target.value) }))}
                  className="mt-1 w-full bg-black/40 border border-border rounded px-2.5 py-1.5 text-sm text-gray-100 focus:border-primary outline-none" />
              </label>
              <label className="block">
                <span className="text-[11px] text-gray-400">Cast-lock notes (one per line)</span>
                <textarea rows={3} value={lines(settings.cast_notes)} onChange={(e) => setSettings((s) => ({ ...s, cast_notes: toLines(e.target.value) }))}
                  className="mt-1 w-full bg-black/40 border border-border rounded px-2.5 py-1.5 text-sm text-gray-100 focus:border-primary outline-none" />
              </label>
              <div className="col-span-2 grid grid-cols-3 gap-4 pt-2 border-t border-border">
                {LEGEND_FIELDS.map(([key, label]) => (
                  <label key={key} className="block">
                    <span className="text-[11px] text-gray-400">Footer: {label} (up to 3 lines; empty = auto)</span>
                    <textarea rows={3} value={lines(settings.legend?.[key])}
                      onChange={(e) => setSettings((s) => ({ ...s, legend: { ...(s.legend || {}), [key]: toLines(e.target.value) } }))}
                      className="mt-1 w-full bg-black/40 border border-border rounded px-2.5 py-1.5 text-sm text-gray-100 focus:border-primary outline-none" />
                  </label>
                ))}
              </div>
            </div>
          )}

          {tab === 'captions' && (
            <div className="space-y-5">
              {scenes.map((s) => (
                <div key={s.id}>
                  <div className="text-xs font-bold text-primary mb-2">SCENE {s.scene_number} · {s.heading}</div>
                  <div className="space-y-2">
                    {[...(s.shots || [])].sort((a, b) => a.shot_number - b.shot_number).map((sh) => (
                      <div key={sh.id} className="grid grid-cols-[60px_1fr_1fr] gap-2 items-center">
                        <span className="text-[11px] text-gray-400">{s.scene_number}.{sh.shot_number}</span>
                        <input
                          aria-label={`Caption ${s.scene_number}.${sh.shot_number}`}
                          value={captions[sh.id]?.board_caption || ''}
                          placeholder="Action caption (empty = drafted by AI at compose)"
                          onChange={(e) => { setCaptions((c) => ({ ...c, [sh.id]: { ...c[sh.id], board_caption: e.target.value } })); setDirtyShots((d) => new Set(d).add(sh.id)); }}
                          className="bg-black/40 border border-border rounded px-2.5 py-1.5 text-sm text-gray-100 focus:border-primary outline-none"
                        />
                        <input
                          aria-label={`Dialogue ${s.scene_number}.${sh.shot_number}`}
                          value={captions[sh.id]?.board_dialogue || ''}
                          placeholder='Dialogue, e.g. SITA: “Do I know you?”'
                          onChange={(e) => { setCaptions((c) => ({ ...c, [sh.id]: { ...c[sh.id], board_dialogue: e.target.value } })); setDirtyShots((d) => new Set(d).add(sh.id)); }}
                          className="bg-black/40 border border-border rounded px-2.5 py-1.5 text-sm text-gray-100 focus:border-primary outline-none"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {tab !== 'preview' && (
          <div className="flex items-center justify-end space-x-2 px-5 py-3 border-t border-border">
            <button onClick={async () => { try { await saveAll(); } catch (e) { setError(errorMessage(e)); } finally { setBusy(null); } }}
              disabled={!!busy} className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-secondary text-gray-200 border border-border hover:bg-muted disabled:opacity-50 cursor-pointer">
              <Save size={13} /><span>Save</span>
            </button>
            <button onClick={saveAndRecompose} disabled={!!busy || isComposing}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-primary text-black hover:opacity-90 disabled:opacity-50 cursor-pointer">
              <RefreshCw size={13} className={busy?.startsWith('Composing') ? 'animate-spin' : ''} /><span>Save &amp; re-compose</span>
            </button>
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
