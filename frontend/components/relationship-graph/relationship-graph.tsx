'use client';

import React from 'react';
import { Character } from '../../lib/api';
import { Network, ShieldAlert, Heart, UserCheck, Flame } from 'lucide-react';

interface RelationshipGraphProps {
  characters?: Character[];
  onSelectCharacter: (char: Character) => void;
}

export function RelationshipGraph({ characters = [], onSelectCharacter }: RelationshipGraphProps) {
  if (characters.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 bg-[#0c0c14]/40 border border-border/60 rounded-xl h-60 text-center">
        <Network size={28} className="text-gray-600 mb-2" />
        <p className="text-xs text-gray-500">Generate story outlines or add cast to inspect relationships.</p>
      </div>
    );
  }

  // Pre-calculate positions in a circle layout
  const width = 360;
  const height = 280;
  const cx = width / 2;
  const cy = height / 2;
  const r = Math.min(width, height) * 0.35;

  const nodes = characters.map((char, index) => {
    const angle = (index * 2 * Math.PI) / characters.length;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    return {
      character: char,
      x,
      y,
      id: char.id,
      name: char.name,
    };
  });

  // Extract links from character's relationships field
  // JSON structure: {"character_id": "type"} where type can be: mentor, enemy, love_interest, ally
  const links: Array<{
    source: typeof nodes[0];
    target: typeof nodes[0];
    type: string;
    key: string;
  }> = [];

  const parseJSON = (str?: string) => {
    if (!str) return {};
    try {
      return JSON.parse(str);
    } catch {
      return {};
    }
  };

  nodes.forEach((sourceNode) => {
    const rels = parseJSON(sourceNode.character.relationships);
    Object.entries(rels).forEach(([targetId, type]) => {
      const targetNode = nodes.find((n) => n.id === targetId);
      if (targetNode) {
        // Prevent duplicate bidirectional links for cleaner visualization
        const key = sourceNode.id < targetNode.id 
          ? `${sourceNode.id}-${targetNode.id}` 
          : `${targetNode.id}-${sourceNode.id}`;
        
        if (!links.some((l) => l.key === key)) {
          links.push({
            source: sourceNode,
            target: targetNode,
            type: String(type),
            key,
          });
        }
      }
    });
  });

  // Helper for rendering link colors/glows
  const getLinkStyles = (type: string) => {
    switch (type.toLowerCase()) {
      case 'mentor':
        return { stroke: '#d97706', strokeDasharray: '4 2', label: 'Mentor', color: 'text-amber-500' };
      case 'enemy':
        return { stroke: '#ef4444', strokeDasharray: 'none', label: 'Enemy', color: 'text-red-500' };
      case 'love_interest':
        return { stroke: '#ec4899', strokeDasharray: '3 3', label: 'Love Interest', color: 'text-pink-500' };
      case 'ally':
      default:
        return { stroke: '#3b82f6', strokeDasharray: 'none', label: 'Ally', color: 'text-blue-500' };
    }
  };

  return (
    <div className="flex flex-col bg-[#08080f]/90 border border-border/80 rounded-xl p-4 shadow-xl text-left">
      <h4 className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-4 flex items-center space-x-1.5">
        <Network size={12} className="text-amber-500" />
        <span>Cast Connection Graph</span>
      </h4>

      {/* SVG Canvas */}
      <div className="bg-[#040408]/60 border border-border/40 rounded-lg p-2 flex items-center justify-center relative overflow-hidden">
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
          {/* Defs for link filters and gradients */}
          <defs>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Links / Connection lines */}
          {links.map((link) => {
            const styles = getLinkStyles(link.type);
            return (
              <g key={link.key}>
                <line
                  x1={link.source.x}
                  y1={link.source.y}
                  x2={link.target.x}
                  y2={link.target.y}
                  stroke={styles.stroke}
                  strokeWidth="1.5"
                  strokeDasharray={styles.strokeDasharray}
                  opacity="0.6"
                  className="transition-all hover:stroke-white hover:opacity-100 duration-200"
                  style={{ filter: 'url(#glow)' }}
                />
                {/* Connection midpoint label */}
                <circle
                  cx={(link.source.x + link.target.x) / 2}
                  cy={(link.source.y + link.target.y) / 2}
                  r="4"
                  fill={styles.stroke}
                />
              </g>
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            return (
              <g 
                key={node.id} 
                className="cursor-pointer group"
                onClick={() => onSelectCharacter(node.character)}
              >
                {/* Node Ring Glow */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="12"
                  fill="transparent"
                  stroke="#f59e0b"
                  strokeWidth="2"
                  strokeOpacity="0"
                  className="group-hover:stroke-opacity-40 transition-all duration-300"
                  style={{ filter: 'url(#glow)' }}
                />
                {/* Main Node Dot */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="7"
                  fill="#0f172a"
                  stroke="#f59e0b"
                  strokeWidth="2"
                  className="transition-all group-hover:fill-amber-500 duration-200"
                />
                {/* Character Name Label */}
                <text
                  x={node.x}
                  y={node.y + 20}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize="10"
                  className="font-semibold select-none group-hover:fill-white group-hover:scale-105 transition-all duration-150"
                >
                  {node.name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend details */}
      <div className="grid grid-cols-2 gap-2 mt-4 text-[10px] text-gray-400 border-t border-border/40 pt-3">
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-[2px] bg-[#d97706] inline-block"></span>
          <span>Amber (Mentor)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-[2px] bg-[#ef4444] inline-block"></span>
          <span>Red (Enemy)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-[2px] bg-[#ec4899] inline-block"></span>
          <span>Pink (Love Interest)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-[2px] bg-[#3b82f6] inline-block"></span>
          <span>Blue (Ally)</span>
        </div>
      </div>
    </div>
  );
}
