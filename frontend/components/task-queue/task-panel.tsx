'use client';

import React, { useState } from 'react';
import { Layers, CheckCircle2, AlertCircle, RefreshCw, Clock, Play } from 'lucide-react';
import { ProgressCard } from './progress-card';

interface BackgroundJob {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed';
  progress: number; // percentage
  timestamp: string;
}

export function TaskPanel() {
  const [jobs, setJobs] = useState<BackgroundJob[]>([
    { id: "job-101", name: "Rendering Storyboard Shot 2.3", status: "running", progress: 65, timestamp: "Just now" },
    { id: "job-102", name: "Index Save The Cat beat sheet RAG", status: "completed", progress: 100, timestamp: "2 mins ago" },
    { id: "job-103", name: "Compile Animatic Reel MP4", status: "completed", progress: 100, timestamp: "5 mins ago" },
    { id: "job-104", name: "Export Screenplay report PDF", status: "failed", progress: 40, timestamp: "10 mins ago" }
  ]);
  const [isProcessing, setIsProcessing] = useState(false);

  const simulateNewJob = () => {
    setIsProcessing(true);
    const newJobId = `job-${Math.floor(Math.random() * 900) + 100}`;
    const newJob: BackgroundJob = {
      id: newJobId,
      name: "Background RAG Script Indexing",
      status: "running",
      progress: 0,
      timestamp: "Just now"
    };
    setJobs(prev => [newJob, ...prev]);

    // Simulate progress bar increments
    let currentPct = 0;
    const interval = setInterval(() => {
      currentPct += 20;
      setJobs(prev => prev.map(j => 
        j.id === newJobId 
          ? { ...j, progress: currentPct, status: currentPct >= 100 ? 'completed' : 'running' } 
          : j
      ));
      if (currentPct >= 100) {
        clearInterval(interval);
        setIsProcessing(false);
      }
    }, 800);
  };

  return (
    <div className="p-4 rounded-xl border border-white/5 bg-[#0a0a14] space-y-4 text-xs text-gray-300">
      <div className="flex items-center justify-between border-b border-white/5 pb-2">
        <div className="flex items-center space-x-1.5">
          <Layers className="text-amber-500 animate-pulse" size={14} />
          <span className="font-bold text-gray-200 uppercase tracking-wider">Celery Tasks Queue</span>
        </div>
        <button
          onClick={simulateNewJob}
          disabled={isProcessing}
          className="flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-500 hover:bg-amber-600 text-black font-semibold disabled:opacity-40 transition-colors cursor-pointer text-[10px]"
        >
          <Play size={10} fill="black" />
          <span>Simulate Job</span>
        </button>
      </div>

      {/* Progress Cards lists */}
      <div className="space-y-3.5 max-h-[220px] overflow-y-auto pr-1">
        {jobs.map((job) => (
          <div key={job.id} className="space-y-1.5 p-2.5 rounded bg-black/40 border border-white/5">
            <div className="flex justify-between items-center text-[10px]">
              <span className="font-semibold text-gray-200">{job.name}</span>
              <span className="text-gray-500 font-mono">{job.timestamp}</span>
            </div>
            
            <ProgressCard progress={job.progress} status={job.status} />

            <div className="flex items-center justify-between text-[9px] text-gray-600">
              <span className="font-mono">ID: {job.id}</span>
              <span className="capitalize font-bold text-amber-500/80">{job.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
export default TaskPanel;
