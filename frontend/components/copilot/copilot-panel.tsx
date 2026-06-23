"use client";

import { useState } from "react";

// ─────────────────────────────────────────────────────────────────
// CINEMATIC COPILOT PANEL — Module 41
// Inline AI scene suggestions: camera, blocking, emotion, transitions.
// ─────────────────────────────────────────────────────────────────

interface CopilotSuggestion {
  scene_type: string;
  detected_emotion: string;
  camera_suggestions: string[];
  blocking_suggestions: string[];
  emotion_enhancement: string;
  transition_options: string[];
  ai_suggestion: string;
  director_note: string;
}

interface CopilotPanelProps {
  projectId?: string;
  directorStyle?: string;
  apiBase?: string;
}

const EMOTION_COLORS: Record<string, string> = {
  grief: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  joy: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  rage: "text-red-400 bg-red-400/10 border-red-400/20",
  fear: "text-purple-400 bg-purple-400/10 border-purple-400/20",
  love: "text-pink-400 bg-pink-400/10 border-pink-400/20",
  despair: "text-slate-400 bg-slate-400/10 border-slate-400/20",
  hope: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  betrayal: "text-orange-400 bg-orange-400/10 border-orange-400/20",
  neutral: "text-white/50 bg-white/5 border-white/10",
};

const SECTION_ICONS: Record<string, string> = {
  camera: "🎥",
  blocking: "🧍",
  emotion: "🎭",
  transition: "✂️",
  ai: "✦",
  director: "🎬",
};

export function CopilotPanel({ projectId, directorStyle = "Kubrick", apiBase = "http://localhost:8000/api" }: CopilotPanelProps) {
  const [fragment, setFragment] = useState("");
  const [suggestion, setSuggestion] = useState<CopilotSuggestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"camera" | "blocking" | "emotion" | "transition">("camera");

  async function getSuggestions() {
    if (!fragment.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/copilot/suggest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scene_fragment: fragment,
          project_id: projectId || null,
          director_style: directorStyle,
        }),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      setSuggestion(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const emotionClass = suggestion ? (EMOTION_COLORS[suggestion.detected_emotion] || EMOTION_COLORS.neutral) : "";

  return (
    <div className="flex flex-col h-full bg-[#0d0d14] rounded-2xl border border-white/8 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/8 bg-white/2">
        <span className="text-amber-400 text-lg">✦</span>
        <div>
          <h3 className="text-sm font-semibold text-white/90 tracking-wide">Cinematic Copilot</h3>
          <p className="text-xs text-white/40">AI inline scene suggestions</p>
        </div>
        {directorStyle && (
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-amber-400/10 border border-amber-400/20 text-amber-400">
            {directorStyle}
          </span>
        )}
      </div>

      {/* Input area */}
      <div className="p-4 space-y-3 border-b border-white/8">
        <textarea
          id="copilot-fragment-input"
          value={fragment}
          onChange={(e) => setFragment(e.target.value)}
          placeholder="Paste a scene fragment here... (action, dialogue, or description)"
          rows={4}
          className="w-full bg-white/4 border border-white/10 rounded-xl px-4 py-3 text-sm text-white/80 placeholder-white/25 resize-none focus:outline-none focus:border-amber-400/40 focus:bg-white/6 transition-all font-mono leading-relaxed"
        />
        <button
          id="copilot-suggest-btn"
          onClick={getSuggestions}
          disabled={loading || !fragment.trim()}
          className="w-full py-2.5 rounded-xl bg-amber-500/20 border border-amber-500/30 text-amber-300 text-sm font-medium hover:bg-amber-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-amber-400/30 border-t-amber-400 rounded-full animate-spin" />
              Analysing…
            </>
          ) : (
            <>✦ Get Suggestions</>
          )}
        </button>
        {error && <p className="text-xs text-red-400/80">{error}</p>}
      </div>

      {/* Results */}
      {suggestion && (
        <div className="flex-1 overflow-y-auto">
          {/* Scene type + Emotion badges */}
          <div className="flex gap-2 px-4 pt-4 pb-3">
            <span className="text-xs px-2 py-1 rounded-full bg-white/8 border border-white/10 text-white/60 capitalize">
              {suggestion.scene_type} scene
            </span>
            <span className={`text-xs px-2 py-1 rounded-full border capitalize ${emotionClass}`}>
              {suggestion.detected_emotion}
            </span>
          </div>

          {/* Tab nav */}
          <div className="flex gap-1 px-4 pb-3">
            {(["camera", "blocking", "emotion", "transition"] as const).map((tab) => (
              <button
                key={tab}
                id={`copilot-tab-${tab}`}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs transition-all ${
                  activeTab === tab
                    ? "bg-amber-500/20 border border-amber-500/30 text-amber-300"
                    : "text-white/40 hover:text-white/70"
                }`}
              >
                {SECTION_ICONS[tab]} {tab}
              </button>
            ))}
          </div>

          <div className="px-4 pb-4 space-y-3">
            {/* Camera suggestions */}
            {activeTab === "camera" && (
              <div className="space-y-2">
                {suggestion.camera_suggestions.map((s, i) => (
                  <div key={i} className="flex gap-2.5 p-3 rounded-xl bg-white/4 border border-white/8">
                    <span className="text-amber-400/60 text-xs mt-0.5 flex-shrink-0">🎥</span>
                    <p className="text-xs text-white/70 leading-relaxed">{s}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Blocking suggestions */}
            {activeTab === "blocking" && (
              <div className="space-y-2">
                {suggestion.blocking_suggestions.map((s, i) => (
                  <div key={i} className="flex gap-2.5 p-3 rounded-xl bg-white/4 border border-white/8">
                    <span className="text-white/40 text-xs mt-0.5 flex-shrink-0">🧍</span>
                    <p className="text-xs text-white/70 leading-relaxed">{s}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Emotion enhancement */}
            {activeTab === "emotion" && suggestion.emotion_enhancement && (
              <div className={`p-3 rounded-xl border ${emotionClass}`}>
                <p className="text-xs leading-relaxed">🎭 {suggestion.emotion_enhancement}</p>
              </div>
            )}

            {/* Transition options */}
            {activeTab === "transition" && (
              <div className="space-y-2">
                {suggestion.transition_options.map((s, i) => (
                  <div key={i} className="flex gap-2.5 p-3 rounded-xl bg-white/4 border border-white/8">
                    <span className="text-white/40 text-xs mt-0.5 flex-shrink-0">✂️</span>
                    <p className="text-xs text-white/70 leading-relaxed">{s}</p>
                  </div>
                ))}
              </div>
            )}

            {/* AI suggestion */}
            {suggestion.ai_suggestion && (
              <div className="mt-3 p-3 rounded-xl bg-amber-500/5 border border-amber-500/15">
                <div className="flex items-center gap-1.5 mb-2">
                  <span className="text-amber-400 text-xs">✦</span>
                  <span className="text-xs font-medium text-amber-400/80">AI Suggestion</span>
                </div>
                <p className="text-xs text-white/65 leading-relaxed italic">{suggestion.ai_suggestion}</p>
              </div>
            )}

            {/* Director note */}
            {suggestion.director_note && (
              <div className="p-3 rounded-xl bg-white/3 border border-white/8">
                <div className="flex items-center gap-1.5 mb-2">
                  <span className="text-xs">🎬</span>
                  <span className="text-xs font-medium text-white/50">Director Note</span>
                </div>
                <p className="text-xs text-white/55 leading-relaxed">{suggestion.director_note}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!suggestion && !loading && (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
          <div className="text-4xl mb-3 opacity-20">✦</div>
          <p className="text-xs text-white/30 leading-relaxed max-w-xs">
            Paste any scene fragment above and get instant cinematic suggestions for camera, blocking, and emotion.
          </p>
        </div>
      )}
    </div>
  );
}
