'use client';

import React from 'react';
import { Film, FileText, Download, ChevronRight, LayoutDashboard } from 'lucide-react';
import Link from 'next/link';

interface NavbarProps {
  projectTitle?: string;
  projectId?: string;
  onExportPDF?: () => void;
  onExportCSV?: () => void;
}

export function Navbar({ projectTitle, projectId, onExportPDF, onExportCSV }: NavbarProps) {
  return (
    <nav className="glass border-b border-border h-14 flex items-center justify-between px-6 z-50 sticky top-0">
      <div className="flex items-center space-x-4">
        <Link href="/" className="flex items-center space-x-2 group">
          <div className="bg-primary text-black p-1.5 rounded-md group-hover:scale-105 transition-transform duration-250">
            <Film size={18} className="stroke-[2.5]" />
          </div>
          <span className="font-bold tracking-wider text-lg bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            70MM AI
          </span>
        </Link>
        
        {projectTitle && (
          <>
            <ChevronRight size={14} className="text-gray-600" />
            <div className="flex items-center space-x-2">
              <span className="text-sm font-semibold text-gray-300">{projectTitle}</span>
              <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                MVP WORKSPACE
              </span>
            </div>
          </>
        )}
      </div>

      <div className="flex items-center space-x-3">
        {projectId && (
          <div className="flex items-center space-x-2">
            {onExportPDF && (
              <button 
                onClick={onExportPDF}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-secondary hover:bg-muted text-gray-200 border border-border cursor-pointer transition-colors duration-150"
              >
                <FileText size={13} className="text-primary" />
                <span>Export PDF</span>
              </button>
            )}
            
            {onExportCSV && (
              <button 
                onClick={onExportCSV}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-secondary hover:bg-muted text-gray-200 border border-border cursor-pointer transition-colors duration-150"
              >
                <Download size={13} />
                <span>Export CSV</span>
              </button>
            )}
          </div>
        )}
        
        <Link 
          href="/projects"
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-primary text-black hover:bg-primary/95 transition-colors duration-150"
        >
          <LayoutDashboard size={13} />
          <span>Dashboard</span>
        </Link>
      </div>
    </nav>
  );
}
