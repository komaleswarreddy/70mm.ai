"use client";

import { useState } from "react";

// ─────────────────────────────────────────────────────────────────
// SCRIPT DOCTOR PANEL — Module 42
// Structural analysis: acts, pacing, stakes, themes, scoring.
// ─────────────────────────────────────────────────────────────────

interface ActDiagnosis {
  scene_range: string;
  scene_count: number;
  missing_elements: string[];
  issues: string[];
  health: string;
}

interface ScriptDoctorResult {
  total_scenes: number;
  estimated_runtime_minutes: number;
  act_diagnosis: Record<string, ActDiagnosis>;
  pacing: {
    average_scene_length_words: number;
    pacing_verdict: string;
    potentially_slow_scenes: number[];
    potentially_rushed_scenes: number[];
  };
  dialogue: {
    dialogue_word_ratio: number;
    verdict: string;
  };
  stakes: {
    detected_stake_types: string[];
    stake_count: number;
    verdict: string;
  };
  themes: {
    verdict: string;
    themes_found_in_script?: string[];
    themes_missing_from_script?: string[];
    project_themes?: string[];
  };
  overall_score: {
    score: number;
    grade: string;
    label: string;
  };
  citations: Array<{ source: string; quote: string }>;
  ai_diagnosis: string;
}

interface ScriptDoctorPanelProps {
  projectId?: string;
  apiBase?: string;
}

const ACT_LABELS: Record<string, string> = {
  act_1: "Act I — Setup",
  act_2a: "Act IIa — Rising Action",
  act_2b: "Act IIb — Darkest Hour",
  act_3: "Act III — Resolution",
};

const GRADE_COLORS: Record<string, string> = {
  A: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10",
  B: "text-blue-400 border-blue-400/30 bg-blue-400/10",
  C: "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
  D: "text-orange-400 border-orange-400/30 bg-orange-400/10",
  F: "text-red-400 border-red-400/30 bg-red-400/10",
};

function ScoreBar({ score }: { score: number }) {
  const color = score >= 90 ? "#34d399" : score >= 75 ? "#60a5fa" : score >= 60 ? "#facc15" : score >= 45 ? "#fb923c" : "#f87171";
  return (
    <div className="relative h-2 bg-white/8 rounded-full overflow-hidden">
      <div
        className="absolute inset-y-0 left-0 rounded-full transition-all duration-700"
        style={{ width: `${score}%`, background: color }}
      />
    </div>
  );
}

export function ScriptDoctorPanel({ projectId, apiBase = "http://localhost:8000/api" }: ScriptDoctorPanelProps) {
  const [screenplay, setScreenplay] = useState("");
  const [result, setResult] = useState<ScriptDoctorResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "acts" | "pacing" | "citations">("overview");

  async function analyse() {
    if (!screenplay.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/script-doctor/analyse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          screenplay_text: screenplay,
          project_id: projectId || null,
        }),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      setResult(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const gradeClass = result ? (GRADE_COLORS[result.overall_score.grade] || GRADE_COLORS.C) : "";

  return (
    <div className="flex flex-col h-full bg-[#0d0d14] rounded-2xl border border-white/8 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/8 bg-white/2">
        <span className="text-blue-400 text-lg">⚕</span>
        <div>
          <h3 className="text-sm font-semibold text-white/90 tracking-wide">Script Doctor</h3>
          <p className="text-xs text-white/40">Structural analysis with RAG citations</p>
        </div>
      </div>

      {/* Input */}
      <div className="p-4 space-y-3 border-b border-white/8">
        <textarea
          id="script-doctor-input"
          value={screenplay}
          onChange={(e) => setScreenplay(e.target.value)}
          placeholder="Paste your screenplay text here for structural analysis..."
          rows={5}
          className="w-full bg-white/4 border border-white/10 rounded-xl px-4 py-3 text-sm text-white/80 placeholder-white/25 resize-none focus:outline-none focus:border-blue-400/40 focus:bg-white/6 transition-all font-mono leading-relaxed"
        />
        <button
          id="script-doctor-analyse-btn"
          onClick={analyse}
          disabled={loading || !screenplay.trim()}
          className="w-full py-2.5 rounded-xl bg-blue-500/20 border border-blue-500/30 text-blue-300 text-sm font-medium hover:bg-blue-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
              Diagnosing…
            </>
          ) : (
            <>⚕ Diagnose Script</>
          )}
        </button>
        {error && <p className="text-xs text-red-400/80">{error}</p>}
      </div>

      {/* Results */}
      {result && (
        <div className="flex-1 overflow-y-auto">
          {/* Overall score */}
          <div className="p-4 border-b border-white/8">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-white/50">Overall Score</span>
              <span className={`text-lg font-bold px-3 py-1 rounded-lg border ${gradeClass}`}>
                {result.overall_score.grade}
              </span>
            </div>
            <ScoreBar score={result.overall_score.score} />
            <div className="flex justify-between mt-2 text-xs text-white/40">
              <span>{result.total_scenes} scenes</span>
              <span>~{result.estimated_runtime_minutes} min runtime</span>
              <span>{result.overall_score.score}/100</span>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 px-4 py-3 border-b border-white/8">
            {(["overview", "acts", "pacing", "citations"] as const).map((tab) => (
              <button
                key={tab}
                id={`doctor-tab-${tab}`}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs capitalize transition-all ${
                  activeTab === tab
                    ? "bg-blue-500/20 border border-blue-500/30 text-blue-300"
                    : "text-white/40 hover:text-white/70"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="p-4 space-y-4">
            {/* Overview tab */}
            {activeTab === "overview" && (
              <div className="space-y-3">
                {/* AI Diagnosis */}
                {result.ai_diagnosis && (
                  <div className="p-3 rounded-xl bg-blue-500/5 border border-blue-500/15">
                    <div className="flex items-center gap-1.5 mb-2">
                      <span className="text-blue-400 text-xs">⚕</span>
                      <span className="text-xs font-medium text-blue-400/80">AI Diagnosis</span>
                    </div>
                    <div className="text-xs text-white/65 leading-relaxed whitespace-pre-line">
                      {result.ai_diagnosis}
                    </div>
                  </div>
                )}

                {/* Stakes */}
                <div className="p-3 rounded-xl bg-white/4 border border-white/8">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-white/60">Stakes</span>
                    <div className="flex gap-1">
                      {result.stakes.detected_stake_types.map((t) => (
                        <span key={t} className="text-xs px-1.5 py-0.5 rounded bg-amber-400/10 border border-amber-400/20 text-amber-400 capitalize">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-white/50">{result.stakes.verdict}</p>
                </div>

                {/* Dialogue */}
                <div className="p-3 rounded-xl bg-white/4 border border-white/8">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-white/60">Dialogue Ratio</span>
                    <span className="text-xs text-white/50">{Math.round(result.dialogue.dialogue_word_ratio * 100)}%</span>
                  </div>
                  <ScoreBar score={result.dialogue.dialogue_word_ratio * 100} />
                  <p className="text-xs text-white/45 mt-1.5">{result.dialogue.verdict}</p>
                </div>

                {/* Themes */}
                {result.themes.project_themes && (
                  <div className="p-3 rounded-xl bg-white/4 border border-white/8">
                    <span className="text-xs font-medium text-white/60 block mb-2">Theme Alignment</span>
                    <p className="text-xs text-white/50">{result.themes.verdict}</p>
                    {result.themes.themes_missing_from_script && result.themes.themes_missing_from_script.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {result.themes.themes_missing_from_script.map((t) => (
                          <span key={t} className="text-xs px-1.5 py-0.5 rounded bg-red-400/10 border border-red-400/20 text-red-400">
                            missing: {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Acts tab */}
            {activeTab === "acts" && (
              <div className="space-y-3">
                {Object.entries(result.act_diagnosis).map(([key, act]) => (
                  <div key={key} className={`p-3 rounded-xl border ${act.health.includes("✅") ? "border-emerald-400/20 bg-emerald-400/5" : "border-orange-400/20 bg-orange-400/5"}`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-white/80">{ACT_LABELS[key] || key}</span>
                      <span className="text-xs">{act.health}</span>
                    </div>
                    <div className="text-xs text-white/45 mb-1">Scenes {act.scene_range} ({act.scene_count} total)</div>
                    {act.issues.map((issue, i) => (
                      <div key={i} className="flex gap-1.5 mt-1.5">
                        <span className="text-orange-400/60 text-xs flex-shrink-0">⚠</span>
                        <p className="text-xs text-white/55">{issue}</p>
                      </div>
                    ))}
                    {act.issues.length === 0 && (
                      <p className="text-xs text-emerald-400/70">No structural issues detected.</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Pacing tab */}
            {activeTab === "pacing" && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-3 rounded-xl bg-white/4 border border-white/8 text-center">
                    <div className="text-lg font-bold text-white/80">{result.pacing.average_scene_length_words}</div>
                    <div className="text-xs text-white/40 mt-0.5">avg words/scene</div>
                  </div>
                  <div className="p-3 rounded-xl bg-white/4 border border-white/8 text-center">
                    <div className="text-sm font-semibold text-white/70 mt-0.5">{result.pacing.pacing_verdict}</div>
                    <div className="text-xs text-white/40 mt-0.5">pacing verdict</div>
                  </div>
                </div>

                {result.pacing.potentially_slow_scenes.length > 0 && (
                  <div className="p-3 rounded-xl bg-orange-400/5 border border-orange-400/15">
                    <span className="text-xs font-medium text-orange-400/80 block mb-1">Potentially Slow Scenes</span>
                    <p className="text-xs text-white/55">Scenes: {result.pacing.potentially_slow_scenes.join(", ")}</p>
                    <p className="text-xs text-white/40 mt-1">Consider trimming or splitting these scenes.</p>
                  </div>
                )}

                {result.pacing.potentially_rushed_scenes.length > 0 && (
                  <div className="p-3 rounded-xl bg-blue-400/5 border border-blue-400/15">
                    <span className="text-xs font-medium text-blue-400/80 block mb-1">Potentially Rushed Scenes</span>
                    <p className="text-xs text-white/55">Scenes: {result.pacing.potentially_rushed_scenes.join(", ")}</p>
                    <p className="text-xs text-white/40 mt-1">Consider expanding these scenes for more breathing room.</p>
                  </div>
                )}
              </div>
            )}

            {/* Citations tab */}
            {activeTab === "citations" && (
              <div className="space-y-3">
                <p className="text-xs text-white/40 mb-2">RAG-sourced citations from your cinematic knowledge base:</p>
                {result.citations.map((c, i) => (
                  <div key={i} className="p-3 rounded-xl bg-white/4 border border-white/8">
                    <p className="text-xs text-white/65 leading-relaxed italic mb-2">"{c.quote}"</p>
                    <p className="text-xs text-amber-400/70">— {c.source}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
          <div className="text-4xl mb-3 opacity-20">⚕</div>
          <p className="text-xs text-white/30 leading-relaxed max-w-xs">
            Paste your screenplay and get a full structural diagnosis — act analysis, pacing, stakes, themes, and RAG citations.
          </p>
        </div>
      )}
    </div>
  );
}
