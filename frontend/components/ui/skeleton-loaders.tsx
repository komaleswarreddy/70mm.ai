"use client";

import React from "react";

// ─────────────────────────────────────────────────────────────────
// SKELETON LOADER COMPONENTS — Module 46: UI Polish
// Cinematic dark-theme skeletons for all major data views.
// ─────────────────────────────────────────────────────────────────

const shimmer = `
  relative overflow-hidden bg-white/5 rounded
  before:absolute before:inset-0
  before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent
  before:animate-[shimmer_1.5s_infinite]
`;

// ─── Base Shimmer Block ──────────────────────────────────────────

interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ className = "", style }: SkeletonProps) {
  return (
    <div
      className={`relative overflow-hidden rounded bg-white/5 ${className}`}
      style={style}
    >
      <div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/8 to-transparent"
        style={{
          animation: "shimmer 1.8s ease-in-out infinite",
          backgroundSize: "200% 100%",
        }}
      />
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  );
}

// ─── Project Card Skeleton ───────────────────────────────────────

export function ProjectCardSkeleton() {
  return (
    <div className="rounded-xl border border-white/8 bg-white/3 p-5 space-y-3 backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-4/5" />
      <div className="flex gap-2 pt-1">
        <Skeleton className="h-3 w-20 rounded-full" />
        <Skeleton className="h-3 w-16 rounded-full" />
      </div>
      <div className="flex justify-between pt-2">
        <Skeleton className="h-8 w-24 rounded-lg" />
        <Skeleton className="h-8 w-8 rounded-lg" />
      </div>
    </div>
  );
}

// ─── Scene List Skeleton ─────────────────────────────────────────

export function SceneListSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 rounded-lg border border-white/6 bg-white/3 p-3"
        >
          <Skeleton className="h-4 w-8 rounded flex-shrink-0" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3.5 w-3/4" />
            <Skeleton className="h-2.5 w-1/2" />
          </div>
          <Skeleton className="h-6 w-16 rounded-full flex-shrink-0" />
        </div>
      ))}
    </div>
  );
}

// ─── Shot Grid Skeleton ──────────────────────────────────────────

export function ShotGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-xl border border-white/8 bg-white/3 overflow-hidden"
        >
          <Skeleton className="h-32 w-full rounded-none" />
          <div className="p-2.5 space-y-1.5">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-2.5 w-full" />
            <Skeleton className="h-2.5 w-3/4" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Storyboard Frame Skeleton ───────────────────────────────────

export function StoryboardSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="flex gap-4 overflow-x-auto pb-2">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex-shrink-0 w-48 rounded-xl border border-white/8 bg-white/3 overflow-hidden"
        >
          <Skeleton className="h-28 w-full rounded-none" />
          <div className="p-2 space-y-1">
            <Skeleton className="h-2.5 w-3/4" />
            <Skeleton className="h-2 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Character Card Skeleton ─────────────────────────────────────

export function CharacterCardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-xl border border-white/8 bg-white/3 p-4 space-y-3"
        >
          <div className="flex items-center gap-3">
            <Skeleton className="h-12 w-12 rounded-full flex-shrink-0" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
          <div className="flex gap-1.5 flex-wrap">
            {Array.from({ length: 3 }).map((_, j) => (
              <Skeleton key={j} className="h-5 w-16 rounded-full" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Timeline Skeleton ───────────────────────────────────────────

export function TimelineSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-start gap-3">
          <Skeleton className="h-4 w-4 rounded-full flex-shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1">
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-2.5 w-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Full Page Skeleton ──────────────────────────────────────────

export function PageSkeleton() {
  return (
    <div className="min-h-screen bg-[#0a0a0f] p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <Skeleton className="h-10 w-32 rounded-lg" />
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-white/8 bg-white/3 p-4 space-y-2">
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-8 w-1/2" />
          </div>
        ))}
      </div>

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <Skeleton className="h-5 w-32" />
          <SceneListSkeleton count={5} />
        </div>
        <div className="space-y-4">
          <Skeleton className="h-5 w-28" />
          <CharacterCardSkeleton count={2} />
        </div>
      </div>
    </div>
  );
}

// ─── Inline Text Skeleton ────────────────────────────────────────

export function TextSkeleton({ lines = 3 }: { lines?: number }) {
  const widths = ["100%", "92%", "85%", "78%", "95%"];
  return (
    <div className="space-y-1.5">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className="h-3"
          style={{ width: widths[i % widths.length] }}
        />
      ))}
    </div>
  );
}

// ─── Table Skeleton ──────────────────────────────────────────────

export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="rounded-xl border border-white/8 overflow-hidden">
      {/* Header */}
      <div className="grid bg-white/5 p-3 border-b border-white/8" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-3/4" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, r) => (
        <div
          key={r}
          className="grid p-3 border-b border-white/5 last:border-0"
          style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
        >
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-3" style={{ width: c === 0 ? "80%" : "60%" }} />
          ))}
        </div>
      ))}
    </div>
  );
}
