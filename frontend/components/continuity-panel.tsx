'use client';

import React, { useState } from 'react';
import { ShieldAlert, CheckCircle, AlertTriangle, Play, Loader2, Sparkles } from 'lucide-react';
import { api } from '../lib/api';

interface ContinuityWarning {
  type: string;
  severity: 'warning' | 'error';
  description: string;
  fix_suggestion: string;
  auto_fixable: boolean;
  fix_data?: {
    shot_id?: string;
    updates?: any;
  };
}

interface ContinuityPanelProps {
  sceneId?: string;
  onRefreshProject: () => void;
}

export function ContinuityPanel({ sceneId, onRefreshProject }: ContinuityPanelProps) {
  const [warnings, setWarnings] = useState<ContinuityWarning[]>([]);
  const [isValidating, setIsValidating] = useState(false);
  const [hasRun, setHasRun] = useState(false);

  const runValidation = async () => {
    if (!sceneId) return;
    setIsValidating(true);
    try {
      const response = await api.validateContinuity(sceneId);
      setWarnings(response.warnings || []);
      setHasRun(true);
    } catch (err) {
      console.error(err);
    } finally {
      setIsValidating(false);
    }
  };

  const applyAutoFix = async (warning: ContinuityWarning) => {
    if (!warning.fix_data?.shot_id || !warning.fix_data?.updates) return;
    try {
      await api.updateShot(warning.fix_data.shot_id, warning.fix_data.updates);
      // Remove from list
      setWarnings(prev => prev.filter(w => w !== warning));
      onRefreshProject();
    } catch (err) {
      console.error(err);
    }
  };

  if (!sceneId) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-gray-500 h-full text-center">
        <p className="text-xs font-semibold">Select a scene to validate screenplay continuity</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07070c] overflow-hidden text-xs">
      <div className="p-3 border-b border-border bg-[#0d0d15]/80 flex items-center justify-between">
        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Continuity Engine</span>
        <button
          onClick={runValidation}
          disabled={isValidating}
          className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-amber-500 hover:bg-amber-600 text-black font-semibold transition-colors disabled:opacity-40 cursor-pointer"
        >
          {isValidating ? (
            <>
              <Loader2 className="animate-spin" size={12} />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <ShieldAlert size={12} />
              <span>Scan Scene</span>
            </>
          )}
        </button>
      </div>

      <div className="flex-1 p-3 overflow-y-auto space-y-2">
        {!hasRun ? (
          <div className="flex flex-col items-center justify-center h-48 space-y-2 text-gray-500 text-center">
            <ShieldAlert size={28} className="text-amber-500/40" />
            <p className="font-semibold text-gray-400">Validate AI screenplay hallucinations</p>
            <p className="text-[10px] text-gray-600 max-w-[200px]">Cross-references cast list, props, and day/night settings against your shots list.</p>
          </div>
        ) : warnings.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 space-y-2 text-center">
            <CheckCircle size={28} className="text-emerald-500/80 animate-pulse" />
            <p className="font-semibold text-gray-300">Perfect Continuity</p>
            <p className="text-[10px] text-gray-600">Zero discrepancies detected between script and shot list.</p>
          </div>
        ) : (
          warnings.map((warning, index) => (
            <div
              key={index}
              className={`p-3 rounded border bg-[#0d0d18] transition-all duration-300 hover:translate-x-1 ${
                warning.severity === 'error' ? 'border-red-500/20 hover:border-red-500/40' : 'border-amber-500/20 hover:border-amber-500/40'
              }`}
            >
              <div className="flex items-start space-x-2">
                {warning.severity === 'error' ? (
                  <AlertTriangle className="text-red-500 shrink-0 mt-0.5" size={14} />
                ) : (
                  <AlertTriangle className="text-amber-500 shrink-0 mt-0.5" size={14} />
                )}
                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className={`font-semibold capitalize ${warning.severity === 'error' ? 'text-red-400' : 'text-amber-400'}`}>
                      {warning.type} Conflict
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${
                      warning.severity === 'error' ? 'bg-red-950 text-red-400' : 'bg-amber-950 text-amber-400'
                    }`}>
                      {warning.severity}
                    </span>
                  </div>
                  <p className="text-gray-300 leading-normal text-[11px]">{warning.description}</p>
                  <div className="pt-1.5 flex items-center justify-between bg-black/30 p-1.5 rounded border border-white/5 mt-2">
                    <span className="text-gray-500 font-mono text-[9px] truncate max-w-[150px]">
                      {warning.fix_suggestion}
                    </span>
                    {warning.auto_fixable && (
                      <button
                        onClick={() => applyAutoFix(warning)}
                        className="flex items-center space-x-0.5 bg-emerald-500 hover:bg-emerald-600 text-black px-1.5 py-0.5 rounded text-[9px] font-bold transition-all cursor-pointer shadow-lg hover:scale-105"
                      >
                        <Sparkles size={9} />
                        <span>Auto-Fix</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
