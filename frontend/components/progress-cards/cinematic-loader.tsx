'use client';

import React, { useEffect, useState } from 'react';
import { Film, CheckCircle2, Circle } from 'lucide-react';

interface LoaderStep {
  label: string;
  duration: number; // simulated duration in ms
}

interface CinematicLoaderProps {
  steps?: LoaderStep[];
  title?: string;
  onComplete?: () => void;
}

const DEFAULT_STEPS: LoaderStep[] = [
  { label: 'Analyzing seed logline & creative prompt...', duration: 1500 },
  { label: 'Extrapolating primary themes and subtextual conflicts...', duration: 1800 },
  { label: 'Fleshing out three-act boundaries & midpoint twists...', duration: 2000 },
  { label: 'Drafting character profiles, weaknesses, and arcs...', duration: 2200 },
  { label: 'Finalizing cinematic outline and saving beat sheets...', duration: 1200 },
];

export function CinematicLoader({ 
  steps = DEFAULT_STEPS, 
  title = "Initiating Story Development",
  onComplete 
}: CinematicLoaderProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  useEffect(() => {
    if (currentStep >= steps.length) {
      if (onComplete) onComplete();
      return;
    }

    const timer = setTimeout(() => {
      setCompletedSteps(prev => [...prev, currentStep]);
      setCurrentStep(prev => prev + 1);
    }, steps[currentStep].duration);

    return () => clearTimeout(timer);
  }, [currentStep, steps, onComplete]);

  return (
    <div className="flex flex-col items-center justify-center p-8 bg-[#07070a]/95 border border-amber-500/20 rounded-2xl max-w-md w-full shadow-2xl relative overflow-hidden backdrop-blur-md">
      {/* Ambient background glow */}
      <div className="absolute -top-24 -left-24 w-48 h-48 bg-amber-500/10 rounded-full blur-[60px] pointer-events-none"></div>
      
      {/* Spinner header */}
      <div className="relative mb-6">
        <div className="w-16 h-16 rounded-full border-2 border-amber-500/10 border-t-amber-500 animate-spin"></div>
        <div className="absolute inset-0 flex items-center justify-center text-amber-500">
          <Film size={20} className="animate-pulse" />
        </div>
      </div>

      <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-2 screenplay-font">{title}</h3>
      <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-6">Pipeline processing active</p>

      {/* Steps List */}
      <div className="w-full space-y-3.5 text-left border-t border-border/40 pt-4">
        {steps.map((step, idx) => {
          const isCompleted = completedSteps.includes(idx);
          const isActive = currentStep === idx;
          
          return (
            <div 
              key={idx} 
              className={`flex items-start space-x-3 transition-all duration-300 ${
                isActive ? 'opacity-100 scale-[1.01]' : isCompleted ? 'opacity-70' : 'opacity-35'
              }`}
            >
              <div className="mt-0.5 shrink-0">
                {isCompleted ? (
                  <CheckCircle2 size={13} className="text-amber-500" />
                ) : isActive ? (
                  <div className="w-3.5 h-3.5 rounded-full border border-amber-500 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></div>
                  </div>
                ) : (
                  <Circle size={13} className="text-gray-600" />
                )}
              </div>
              <div className="flex-1">
                <p className={`text-xs font-medium leading-tight ${isActive ? 'text-amber-500' : 'text-gray-300'}`}>
                  {step.label}
                </p>
                {isActive && (
                  <span className="text-[9px] text-amber-500/50 uppercase tracking-widest mt-0.5 block animate-pulse">
                    Synthesizing...
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
