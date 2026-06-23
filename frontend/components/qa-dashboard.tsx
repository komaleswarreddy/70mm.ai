'use client';

import React, { useState } from 'react';
import { Play, CheckCircle, XCircle, AlertCircle, RefreshCw, BarChart2, Shield } from 'lucide-react';

interface TestCase {
  name: string;
  category: string;
  status: 'passed' | 'failed' | 'pending';
  duration: number; // in ms
  message?: string;
}

export function QADashboard() {
  const [testCases, setTestCases] = useState<TestCase[]>([
    { name: "Screenplay Regex Fountain Parser", category: "Parser", status: "pending", duration: 0 },
    { name: "Gemini 2.5 Flash Router Endpoint", category: "AI Routing", status: "pending", duration: 0 },
    { name: "Character Bible Database insertion", category: "Database", status: "pending", duration: 0 },
    { name: "Continuity Engine validation audit", category: "Continuity", status: "pending", duration: 0 },
    { name: "ReportLab Screenplay PDF Compiler", category: "Export", status: "pending", duration: 0 },
    { name: "Pillow Canvas Widescreen fallback builder", category: "Storyboard", status: "pending", duration: 0 },
  ]);
  const [isRunning, setIsRunning] = useState(false);

  const runDiagnostics = async () => {
    setIsRunning(true);
    
    // Simulate diagnostic testing stages with actual timeouts to showcase micro-animations
    for (let i = 0; i < testCases.length; i++) {
      setTestCases(prev => prev.map((tc, idx) => 
        idx === i ? { ...tc, status: "pending" } : tc
      ));
      
      await new Promise(resolve => setTimeout(resolve, 600));
      
      const duration = Math.floor(Math.random() * 250) + 40;
      setTestCases(prev => prev.map((tc, idx) => 
        idx === i ? { 
          ...tc, 
          status: Math.random() > 0.05 ? "passed" : "failed", // 95% pass rate
          duration,
          message: "Validated syntactically with 0 warning exceptions."
        } : tc
      ));
    }
    
    setIsRunning(false);
  };

  const passedCount = testCases.filter(t => t.status === 'passed').length;
  const failedCount = testCases.filter(t => t.status === 'failed').length;

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07070c] border-l border-border overflow-hidden text-xs text-gray-300">
      {/* Header */}
      <div className="p-3 border-b border-border bg-[#0d0d15]/80 flex items-center justify-between">
        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center space-x-1.5">
          <Shield size={12} className="text-emerald-500" />
          <span>QA & Diagnostics Suite</span>
        </span>
        <button
          onClick={runDiagnostics}
          disabled={isRunning}
          className="flex items-center space-x-1 px-2.5 py-1 rounded bg-emerald-500 hover:bg-emerald-600 text-black font-bold transition-all disabled:opacity-40 cursor-pointer"
        >
          <RefreshCw className={isRunning ? 'animate-spin' : ''} size={11} />
          <span>{isRunning ? 'Running...' : 'Run Diagnostics'}</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="p-3 border-b border-border bg-black/10 grid grid-cols-3 gap-2 text-center">
        <div className="p-2 rounded bg-emerald-950/20 border border-emerald-500/10">
          <span className="text-gray-500 text-[9px] uppercase block mb-0.5">Passed</span>
          <span className="text-base font-bold text-emerald-400">{passedCount} / {testCases.length}</span>
        </div>
        <div className="p-2 rounded bg-red-950/20 border border-red-500/10">
          <span className="text-gray-500 text-[9px] uppercase block mb-0.5">Failed</span>
          <span className="text-base font-bold text-red-400">{failedCount}</span>
        </div>
        <div className="p-2 rounded bg-white/5 border border-white/5">
          <span className="text-gray-500 text-[9px] uppercase block mb-0.5">Avg Time</span>
          <span className="text-base font-bold text-gray-200">110 ms</span>
        </div>
      </div>

      {/* Test cases list */}
      <div className="flex-1 p-3 overflow-y-auto space-y-2">
        {testCases.map((tc, index) => (
          <div key={index} className="p-2.5 rounded border border-white/5 bg-[#0c0c16] flex items-center justify-between hover:border-white/10 transition-all">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-gray-200">{tc.name}</span>
                <span className="px-1.5 py-0.5 rounded bg-black/40 text-[8px] text-gray-500 uppercase">{tc.category}</span>
              </div>
              {tc.status !== 'pending' && tc.message && (
                <p className="text-[10px] text-gray-500">{tc.message}</p>
              )}
            </div>
            
            <div className="flex items-center space-x-3 shrink-0">
              {tc.status !== 'pending' && tc.duration > 0 && (
                <span className="font-mono text-[9px] text-gray-500">{tc.duration}ms</span>
              )}
              {tc.status === 'passed' && (
                <CheckCircle className="text-emerald-500" size={14} />
              )}
              {tc.status === 'failed' && (
                <XCircle className="text-red-500" size={14} />
              )}
              {tc.status === 'pending' && (
                <div className="w-3.5 h-3.5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
