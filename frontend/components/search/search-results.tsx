'use client';

import React, { useState, useEffect } from 'react';
import { Film, Film as SceneIcon, ArrowRight, Loader2, Info } from 'lucide-react';
import { FilterPanel } from './filter-panel';

interface SearchResultScene {
  id: string;
  project_id: string;
  project_title: string;
  scene_number: number;
  heading: string;
  raw_content: string;
}

interface SearchResultsProps {
  query: string;
  onClose: () => void;
}

export function SearchResults({ query, onClose }: SearchResultsProps) {
  const [results, setResults] = useState<SearchResultScene[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTag, setActiveTag] = useState('All');

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    
    const delayDebounce = setTimeout(async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`http://localhost:8000/api/search/scenes?query=${encodeURIComponent(query)}`);
        if (response.ok) {
          const data = await response.json();
          setResults(data || []);
        } else {
          setResults(getMockResults(query));
        }
      } catch {
        setResults(getMockResults(query));
      } finally {
        setIsLoading(false);
      }
    }, 400);

    return () => clearTimeout(delayDebounce);
  }, [query]);

  // Mock scenes for testing / standalone fallback
  const getMockResults = (q: string): SearchResultScene[] => {
    const list = [
      {
        id: "s-201",
        project_id: "p-10",
        project_title: "The Lost Cosmos",
        scene_number: 14,
        heading: "INT. HOSPITAL ROOM - NIGHT",
        raw_content: "VASU lies in the hospital bed, monitors beeping. SARAH argues with the doctor at the doorway about the recovery odds."
      },
      {
        id: "s-202",
        project_id: "p-11",
        project_title: "Neon Shadows",
        scene_number: 22,
        heading: "EXT. ALLEYWAY - NIGHT",
        raw_content: "An intense fight breaks out under the glowing neon sign. Vasu ducks under a wild punch, retaliating with a sweep."
      }
    ];
    return list.filter(item => 
      item.heading.toLowerCase().includes(q.toLowerCase() || '') ||
      item.raw_content.toLowerCase().includes(q.toLowerCase() || '')
    );
  };

  const filteredResults = activeTag === 'All'
    ? results
    : results.filter(r => r.heading.toLowerCase().includes(activeTag.toLowerCase()));

  return (
    <div className="space-y-4">
      <FilterPanel activeTag={activeTag} onTagChange={setActiveTag} />

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="animate-spin text-primary" size={24} />
        </div>
      ) : filteredResults.length === 0 ? (
        <div className="text-center py-12 text-gray-600">
          {query.trim() ? (
            <span>No matching scenes found. Try 'hospital' or 'alleyway'.</span>
          ) : (
            <span>Type above to search scenes across film repositories.</span>
          )}
        </div>
      ) : (
        <div className="space-y-2.5">
          {filteredResults.map((scene) => (
            <div key={scene.id} className="p-3 border border-white/5 bg-[#0c0c16] rounded-md flex flex-col space-y-1.5 hover:border-amber-500/25 transition-all">
              <div className="flex justify-between items-center text-[10px]">
                <div className="flex items-center space-x-1.5">
                  <Film size={11} className="text-amber-500" />
                  <span className="font-bold text-gray-200">{scene.project_title}</span>
                </div>
                <span className="font-mono text-gray-500">Scene #{scene.scene_number}</span>
              </div>
              
              <h5 className="font-bold text-gray-100 font-mono text-[11px]">{scene.heading}</h5>
              <p className="text-gray-400 leading-relaxed text-[11px] font-sans italic">
                "{scene.raw_content}"
              </p>

              <div className="flex justify-end pt-1">
                <button
                  onClick={() => {
                    // Navigate to project workspace and close
                    window.location.href = `/workspace/${scene.project_id}`;
                    onClose();
                  }}
                  className="flex items-center space-x-0.5 text-primary hover:text-primary/80 transition-colors font-bold cursor-pointer text-[10px]"
                >
                  <span>Jump to Scene</span>
                  <ArrowRight size={10} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
