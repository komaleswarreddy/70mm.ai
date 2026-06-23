"use client";

import React from "react";

// ─────────────────────────────────────────────────────────────────
// EMPTY STATE COMPONENTS — Module 46: UI Polish
// Premium, cinematic empty states for all major views.
// ─────────────────────────────────────────────────────────────────

interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  variant?: "film" | "scene" | "character" | "shot" | "storyboard" | "search" | "default";
}

// ─── Film Roll Icon SVG ──────────────────────────────────────────
const FilmIcon = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none" className="opacity-40">
    <rect x="8" y="16" width="48" height="32" rx="3" stroke="currentColor" strokeWidth="2" />
    <rect x="8" y="22" width="6" height="6" fill="currentColor" opacity="0.5" />
    <rect x="8" y="32" width="6" height="6" fill="currentColor" opacity="0.5" />
    <rect x="8" y="42" width="6" height="6" fill="currentColor" opacity="0.5" />
    <rect x="50" y="22" width="6" height="6" fill="currentColor" opacity="0.5" />
    <rect x="50" y="32" width="6" height="6" fill="currentColor" opacity="0.5" />
    <rect x="50" y="42" width="6" height="6" fill="currentColor" opacity="0.5" />
    <line x1="20" y1="16" x2="20" y2="48" stroke="currentColor" strokeWidth="1" opacity="0.3" />
    <line x1="44" y1="16" x2="44" y2="48" stroke="currentColor" strokeWidth="1" opacity="0.3" />
    <circle cx="32" cy="32" r="6" stroke="currentColor" strokeWidth="2" opacity="0.6" />
  </svg>
);

const SceneIcon = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none" className="opacity-40">
    <rect x="8" y="20" width="48" height="32" rx="3" stroke="currentColor" strokeWidth="2" />
    <path d="M8 20L24 12h16l16 8" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    <line x1="24" y1="12" x2="24" y2="20" stroke="currentColor" strokeWidth="2" />
    <line x1="40" y1="12" x2="40" y2="20" stroke="currentColor" strokeWidth="2" />
    <rect x="16" y="28" width="12" height="16" rx="2" fill="currentColor" opacity="0.2" />
    <rect x="36" y="28" width="12" height="16" rx="2" fill="currentColor" opacity="0.2" />
  </svg>
);

const PersonIcon = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none" className="opacity-40">
    <circle cx="32" cy="20" r="10" stroke="currentColor" strokeWidth="2" />
    <path d="M12 52c0-11.046 8.954-20 20-20s20 8.954 20 20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

const CameraIcon = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none" className="opacity-40">
    <rect x="8" y="20" width="40" height="28" rx="4" stroke="currentColor" strokeWidth="2" />
    <path d="M48 28l8-6v20l-8-6V28z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    <circle cx="28" cy="34" r="8" stroke="currentColor" strokeWidth="2" />
    <circle cx="28" cy="34" r="3" fill="currentColor" opacity="0.4" />
  </svg>
);

const FrameIcon = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none" className="opacity-40">
    <rect x="8" y="12" width="48" height="36" rx="3" stroke="currentColor" strokeWidth="2" />
    <path d="M8 36l12-10 10 8 8-6 14 14" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
    <circle cx="20" cy="22" r="4" stroke="currentColor" strokeWidth="2" />
    <line x1="16" y1="52" x2="48" y2="52" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

const SearchIcon = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none" className="opacity-40">
    <circle cx="27" cy="27" r="16" stroke="currentColor" strokeWidth="2" />
    <line x1="38" y1="38" x2="54" y2="54" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    <line x1="21" y1="27" x2="33" y2="27" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    <line x1="27" y1="21" x2="27" y2="33" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

const ICONS: Record<string, React.ReactNode> = {
  film: <FilmIcon />,
  scene: <SceneIcon />,
  character: <PersonIcon />,
  shot: <CameraIcon />,
  storyboard: <FrameIcon />,
  search: <SearchIcon />,
  default: <FilmIcon />,
};

const ACCENT_COLORS: Record<string, string> = {
  film: "from-amber-500/20 to-orange-600/10",
  scene: "from-blue-500/20 to-indigo-600/10",
  character: "from-purple-500/20 to-violet-600/10",
  shot: "from-cyan-500/20 to-blue-600/10",
  storyboard: "from-emerald-500/20 to-teal-600/10",
  search: "from-rose-500/20 to-pink-600/10",
  default: "from-white/10 to-white/5",
};

export function EmptyState({
  title,
  description,
  action,
  icon,
  variant = "default",
}: EmptyStateProps) {
  const gradientClass = ACCENT_COLORS[variant] || ACCENT_COLORS.default;
  const iconNode = icon || ICONS[variant] || ICONS.default;

  return (
    <div className="flex flex-col items-center justify-center py-16 px-8 text-center">
      {/* Glow backdrop */}
      <div className={`relative mb-6`}>
        <div
          className={`absolute inset-0 rounded-full bg-gradient-radial ${gradientClass} blur-2xl scale-150 opacity-60`}
        />
        <div className="relative z-10 text-white/50">{iconNode}</div>
      </div>

      <h3 className="text-lg font-semibold text-white/80 mb-2 tracking-wide">
        {title}
      </h3>
      <p className="text-sm text-white/40 max-w-xs leading-relaxed mb-6">
        {description}
      </p>

      {action && <div className="flex justify-center">{action}</div>}
    </div>
  );
}

// ─── Pre-built Empty State Variants ─────────────────────────────

export function NoProjectsEmpty({ onNew }: { onNew?: () => void }) {
  return (
    <EmptyState
      variant="film"
      title="No Projects Yet"
      description="Begin your cinematic journey. Create your first 70MM AI project and let the story unfold."
      action={
        onNew && (
          <button
            id="btn-new-project-empty"
            onClick={onNew}
            className="px-5 py-2.5 rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-300 text-sm font-medium hover:bg-amber-500/30 transition-colors"
          >
            + New Project
          </button>
        )
      }
    />
  );
}

export function NoScenesEmpty({ onParse }: { onParse?: () => void }) {
  return (
    <EmptyState
      variant="scene"
      title="No Scenes Yet"
      description="Upload your screenplay to automatically parse scenes, or write your first scene manually."
      action={
        onParse && (
          <button
            id="btn-upload-screenplay-empty"
            onClick={onParse}
            className="px-5 py-2.5 rounded-lg bg-blue-500/20 border border-blue-500/30 text-blue-300 text-sm font-medium hover:bg-blue-500/30 transition-colors"
          >
            Upload Screenplay
          </button>
        )
      }
    />
  );
}

export function NoShotsEmpty({ onAdd }: { onAdd?: () => void }) {
  return (
    <EmptyState
      variant="shot"
      title="No Shots Planned"
      description="Start building your shot list for this scene. Define camera angles, lenses, and movements."
      action={
        onAdd && (
          <button
            id="btn-add-shot-empty"
            onClick={onAdd}
            className="px-5 py-2.5 rounded-lg bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 text-sm font-medium hover:bg-cyan-500/30 transition-colors"
          >
            + Add Shot
          </button>
        )
      }
    />
  );
}

export function NoCharactersEmpty({ onAdd }: { onAdd?: () => void }) {
  return (
    <EmptyState
      variant="character"
      title="Character Bible Empty"
      description="Define your cast. Build rich, AI-powered character profiles with backstories, arcs, and relationships."
      action={
        onAdd && (
          <button
            id="btn-add-character-empty"
            onClick={onAdd}
            className="px-5 py-2.5 rounded-lg bg-purple-500/20 border border-purple-500/30 text-purple-300 text-sm font-medium hover:bg-purple-500/30 transition-colors"
          >
            + Add Character
          </button>
        )
      }
    />
  );
}

export function NoStoryboardEmpty({ onGenerate }: { onGenerate?: () => void }) {
  return (
    <EmptyState
      variant="storyboard"
      title="Storyboard Blank"
      description="Generate AI storyboard frames for your shots. Visualise your film before you shoot it."
      action={
        onGenerate && (
          <button
            id="btn-generate-storyboard-empty"
            onClick={onGenerate}
            className="px-5 py-2.5 rounded-lg bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-sm font-medium hover:bg-emerald-500/30 transition-colors"
          >
            ✦ Generate Frames
          </button>
        )
      }
    />
  );
}

export function NoSearchResultsEmpty({ query }: { query?: string }) {
  return (
    <EmptyState
      variant="search"
      title="No Results Found"
      description={
        query
          ? `No matches for "${query}". Try different keywords or broaden your search.`
          : "Try searching for a project title, scene heading, or character name."
      }
    />
  );
}
