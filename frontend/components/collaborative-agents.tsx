'use client';

import React, { useState } from 'react';
import { User, Users, Play, Loader2, Sparkles, MessageSquare } from 'lucide-react';

interface AgentMessage {
  agentName: string;
  avatarColor: string;
  role: string;
  message: string;
}

export function CollaborativeAgents() {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [isCollaborating, setIsCollaborating] = useState(false);

  const startCollaboration = async () => {
    setIsCollaborating(true);
    setMessages([]);

    const agentSequence: AgentMessage[] = [
      {
        agentName: "Story Agent",
        avatarColor: "bg-indigo-600",
        role: "Narrative Architect",
        message: "I've reviewed Act II. The emotional beat after the catalyst is lacking depth. Vasu should discover the secret map inside the antique clock rather than just finding it in the drawer."
      },
      {
        agentName: "Director Agent",
        avatarColor: "bg-amber-600",
        role: "Visual Strategist",
        message: "Agreed. Let's frame the antique clock centered in a symmetrical Wide Shot. A ticking clock builds suspense and fits the Fincher mood board."
      },
      {
        agentName: "Cinematographer Agent",
        avatarColor: "bg-teal-600",
        role: "Lighting & Composition",
        message: "Excellent suggestion. I'll use a 35mm Prime lens, positioning a cold neon blue spotlight casting long shadows from the clock's pendulum. The face should catch a warm tungsten highlight."
      },
      {
        agentName: "Continuity Agent",
        avatarColor: "bg-emerald-600",
        role: "Supervisor",
        message: "Check. I've noted that if he pulls the map out, his gloves should be on. In the previous scene he was wearing black leather gloves outside."
      },
      {
        agentName: "Research Agent",
        avatarColor: "bg-rose-600",
        role: "Historical & Realism",
        message: "Historical check: Widescreen pocket watches from 1920 typically used mechanical spring winders. The map folding pattern should align with period-accurate logistics."
      }
    ];

    // Simulating agent turn-taking dialog sequence
    for (let i = 0; i < agentSequence.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 1200));
      setMessages(prev => [...prev, agentSequence[i]]);
    }

    setIsCollaborating(false);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07070c] border-l border-border overflow-hidden text-xs text-gray-300">
      {/* Header */}
      <div className="p-3 border-b border-border bg-[#0d0d15]/80 flex items-center justify-between">
        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center space-x-1.5">
          <Users size={12} className="text-indigo-400" />
          <span>Collaborative Agents Room</span>
        </span>
        <button
          onClick={startCollaboration}
          disabled={isCollaborating}
          className="flex items-center space-x-1 px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-700 text-white font-bold transition-all disabled:opacity-40 cursor-pointer"
        >
          {isCollaborating ? (
            <>
              <Loader2 className="animate-spin" size={11} />
              <span>Brainstorming...</span>
            </>
          ) : (
            <>
              <Play size={11} fill="white" />
              <span>Engage Collaboration</span>
            </>
          )}
        </button>
      </div>

      {/* Collaboration Chat Log */}
      <div className="flex-1 p-3 overflow-y-auto space-y-3">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 space-y-2 text-gray-500 text-center">
            <Users size={28} className="text-indigo-500/20" />
            <p className="font-semibold text-gray-400">Collaborative Agent Brainstorming</p>
            <p className="text-[10px] text-gray-600 max-w-[200px]">
              Engages Story, Director, Cinematographer, Continuity, and Research agents to refine scene beats.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((msg, idx) => (
              <div key={idx} className="p-2.5 rounded border border-white/5 bg-[#0c0c16]/90 flex items-start space-x-2.5 animate-fadeIn">
                <div className={`w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-white ${msg.avatarColor} font-bold text-[9px]`}>
                  {msg.agentName[0]}
                </div>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-gray-200">{msg.agentName}</span>
                    <span className="text-[8px] text-gray-500 font-mono">({msg.role})</span>
                  </div>
                  <p className="text-gray-300 leading-relaxed text-[11px] font-sans">{msg.message}</p>
                </div>
              </div>
            ))}
            {isCollaborating && (
              <div className="flex items-center space-x-2 p-2.5 pl-3">
                <div className="flex space-x-1">
                  <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-[10px] text-gray-600 font-mono">Agent analyzing scene context...</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
export default CollaborativeAgents;
