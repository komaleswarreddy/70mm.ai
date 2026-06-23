'use client';

import React, { useState, useEffect } from 'react';
import { Calendar, Kanban, Wallet, FileText, Plus, Trash, Printer, AlertCircle, Loader2 } from 'lucide-react';
import { api, CallSheet, BudgetItem } from '../lib/api';

interface ProductionPlannerProps {
  projectId: string;
}

export function ProductionPlanner({ projectId }: ProductionPlannerProps) {
  const [activeTab, setActiveTab] = useState<'schedule' | 'kanban' | 'budget'>('schedule');
  const [callSheets, setCallSheets] = useState<CallSheet[]>([]);
  const [budgetItems, setBudgetItems] = useState<BudgetItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Form states
  const [csDate, setCsDate] = useState('');
  const [csTime, setCsTime] = useState('08:00 AM');
  const [csLocation, setCsLocation] = useState('');
  const [csNotes, setCsNotes] = useState('');

  const [budgetName, setBudgetName] = useState('');
  const [budgetCost, setBudgetCost] = useState(0);
  const [budgetCategory, setBudgetCategory] = useState('Cast');

  useEffect(() => {
    if (projectId) {
      loadPlannerData();
    }
  }, [projectId]);

  const loadPlannerData = async () => {
    setIsLoading(true);
    try {
      const sheets = await api.getCallSheets(projectId);
      const items = await api.getBudget(projectId);
      setCallSheets(sheets || []);
      setBudgetItems(items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCallSheet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csDate) return;
    try {
      await api.createCallSheet(projectId, {
        date: csDate,
        call_time: csTime,
        location: csLocation,
        notes: csNotes
      });
      setCsDate('');
      setCsLocation('');
      setCsNotes('');
      await loadPlannerData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteCallSheet = async (id: string) => {
    try {
      await api.deleteCallSheet(id);
      await loadPlannerData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateBudgetItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!budgetName || budgetCost <= 0) return;
    try {
      await api.createBudgetItem(projectId, budgetCategory, budgetName, budgetCost);
      setBudgetName('');
      setBudgetCost(0);
      await loadPlannerData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteBudgetItem = async (id: string) => {
    try {
      await api.deleteBudgetItem(id);
      await loadPlannerData();
    } catch (err) {
      console.error(err);
    }
  };

  const totalBudget = budgetItems.reduce((acc, item) => acc + item.cost, 0);

  // Grouped cost calculation
  const categoryTotals = budgetItems.reduce((acc: Dict<string, number>, item) => {
    acc[item.category] = (acc[item.category] || 0) + item.cost;
    return acc;
  }, {});

  return (
    <div className="flex-1 flex flex-col h-full bg-[#07070c] border-l border-border overflow-hidden text-xs text-gray-300">
      {/* Header and Tabs Selector */}
      <div className="p-3 border-b border-border bg-[#0d0d15]/80 flex items-center justify-between">
        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Production Planner</span>
        <div className="flex space-x-1 bg-black/40 p-0.5 rounded border border-white/5">
          <button
            onClick={() => setActiveTab('schedule')}
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded transition-all cursor-pointer ${
              activeTab === 'schedule' ? 'bg-primary text-black font-semibold' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Calendar size={11} />
            <span>Call Sheets</span>
          </button>
          <button
            onClick={() => setActiveTab('kanban')}
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded transition-all cursor-pointer ${
              activeTab === 'kanban' ? 'bg-primary text-black font-semibold' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Kanban size={11} />
            <span>Kanban Board</span>
          </button>
          <button
            onClick={() => setActiveTab('budget')}
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded transition-all cursor-pointer ${
              activeTab === 'budget' ? 'bg-primary text-black font-semibold' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Wallet size={11} />
            <span>Budget</span>
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="animate-spin text-primary" size={24} />
        </div>
      ) : (
        <div className="flex-1 p-3 overflow-y-auto">
          {/* TAB 1: SCHEDULE & CALL SHEETS */}
          {activeTab === 'schedule' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              {/* Form panel */}
              <div className="lg:col-span-1 p-3 rounded border border-white/5 bg-[#0d0d18] space-y-3">
                <h4 className="font-bold text-gray-200 text-xs flex items-center space-x-1">
                  <Plus size={13} className="text-amber-500" />
                  <span>Create Call Sheet</span>
                </h4>
                <form onSubmit={handleCreateCallSheet} className="space-y-2.5">
                  <div className="space-y-1">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wide">Date</label>
                    <input
                      type="date"
                      value={csDate}
                      onChange={(e) => setCsDate(e.target.value)}
                      className="w-full bg-[#07070c] border border-border rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                      required
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wide">Call Time</label>
                    <input
                      type="text"
                      placeholder="e.g. 08:00 AM"
                      value={csTime}
                      onChange={(e) => setCsTime(e.target.value)}
                      className="w-full bg-[#07070c] border border-border rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wide">Location / Soundstage</label>
                    <input
                      type="text"
                      placeholder="e.g. Stage A, Metro Studios"
                      value={csLocation}
                      onChange={(e) => setCsLocation(e.target.value)}
                      className="w-full bg-[#07070c] border border-border rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-gray-500 uppercase tracking-wide">Notes & Crew Details</label>
                    <textarea
                      placeholder="Cast details, scene headings, meals time..."
                      rows={3}
                      value={csNotes}
                      onChange={(e) => setCsNotes(e.target.value)}
                      className="w-full bg-[#07070c] border border-border rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-amber-500 placeholder-gray-700"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full py-1.5 rounded bg-amber-500 hover:bg-amber-600 text-black font-bold transition-all shadow-md cursor-pointer text-center"
                  >
                    Generate Sheet
                  </button>
                </form>
              </div>

              {/* Call Sheet lists */}
              <div className="lg:col-span-2 space-y-2">
                <h4 className="font-bold text-gray-400 text-xs">Active Daily Call Sheets</h4>
                {callSheets.length === 0 ? (
                  <div className="p-8 border border-white/5 bg-[#0d0d18] rounded flex flex-col items-center justify-center text-center text-gray-600">
                    <FileText size={24} className="opacity-20 mb-1" />
                    <span>No Call Sheets created yet. Use the scheduler form to start.</span>
                  </div>
                ) : (
                  callSheets.map((cs) => (
                    <div key={cs.id} className="p-3 border border-white/5 bg-[#0c0c16] rounded-md flex items-center justify-between hover:border-amber-500/30 transition-all">
                      <div className="space-y-1 flex-1 pr-4">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-amber-500">{cs.date}</span>
                          <span className="px-1.5 py-0.5 rounded bg-black/40 border border-white/5 text-[9px] font-mono text-gray-400">
                            Call: {cs.call_time}
                          </span>
                        </div>
                        <p className="font-semibold text-gray-200">{cs.location || "Stage TBD"}</p>
                        {cs.notes && <p className="text-[10px] text-gray-500 italic line-clamp-1">{cs.notes}</p>}
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <button
                          onClick={() => window.open(`http://localhost:8000/api/projects/${projectId}/export/pdf`, '_blank')}
                          className="p-1.5 rounded hover:bg-white/5 text-gray-400 hover:text-white transition-colors cursor-pointer"
                          title="Print Call Sheet"
                        >
                          <Printer size={13} />
                        </button>
                        <button
                          onClick={() => handleDeleteCallSheet(cs.id)}
                          className="p-1.5 rounded hover:bg-white/5 text-gray-500 hover:text-red-400 transition-colors cursor-pointer"
                        >
                          <Trash size={13} />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 2: KANBAN BOARD */}
          {activeTab === 'kanban' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* Column 1 */}
              <div className="p-2 border border-white/5 bg-[#0d0d16] rounded-lg flex flex-col space-y-2">
                <div className="flex items-center justify-between border-b border-border pb-1 px-1">
                  <span className="font-bold text-amber-400">To Shoot</span>
                  <span className="px-1.5 py-0.5 rounded bg-black/40 text-[9px] font-mono">2 Shots</span>
                </div>
                <div className="space-y-2">
                  <div className="p-2 border border-white/5 bg-[#07070d] rounded hover:border-amber-500/20 transition-all cursor-pointer">
                    <p className="font-bold text-primary">Shot 1.1 &mdash; CU</p>
                    <p className="text-[10px] text-gray-500 line-clamp-1">John enters room look nervously.</p>
                  </div>
                  <div className="p-2 border border-white/5 bg-[#07070d] rounded hover:border-amber-500/20 transition-all cursor-pointer">
                    <p className="font-bold text-primary">Shot 1.2 &mdash; WS</p>
                    <p className="text-[10px] text-gray-500 line-clamp-1">Wide view of kitchen showing neon clock.</p>
                  </div>
                </div>
              </div>

              {/* Column 2 */}
              <div className="p-2 border border-white/5 bg-[#0d0d16] rounded-lg flex flex-col space-y-2">
                <div className="flex items-center justify-between border-b border-border pb-1 px-1">
                  <span className="font-bold text-sky-400">Filming</span>
                  <span className="px-1.5 py-0.5 rounded bg-black/40 text-[9px] font-mono">1 Shot</span>
                </div>
                <div className="space-y-2">
                  <div className="p-2 border border-white/5 bg-[#07070d] rounded border-sky-500/20 hover:border-sky-500/40 transition-all cursor-pointer">
                    <div className="flex items-center justify-between">
                      <p className="font-bold text-primary">Shot 1.3 &mdash; MCU</p>
                      <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-ping"></span>
                    </div>
                    <p className="text-[10px] text-gray-500 line-clamp-1">OTS John looking at clock.</p>
                  </div>
                </div>
              </div>

              {/* Column 3 */}
              <div className="p-2 border border-white/5 bg-[#0d0d16] rounded-lg flex flex-col space-y-2">
                <div className="flex items-center justify-between border-b border-border pb-1 px-1">
                  <span className="font-bold text-emerald-400">Completed</span>
                  <span className="px-1.5 py-0.5 rounded bg-black/40 text-[9px] font-mono">0 Shots</span>
                </div>
                <div className="p-6 border border-dashed border-white/5 bg-[#07070d]/30 rounded text-center text-gray-700">
                  <span>Empty. Update shot statuses in the grid to see them here.</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: BUDGET TRACKER */}
          {activeTab === 'budget' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              {/* Form & Metrics Panel */}
              <div className="lg:col-span-1 space-y-3">
                <div className="p-3 border border-white/5 bg-[#0c0c16] rounded-md space-y-2.5">
                  <span className="text-[10px] text-gray-500 uppercase tracking-wide block">Total Estimated Cost</span>
                  <span className="text-2xl font-bold text-amber-500 font-mono">${totalBudget.toLocaleString()}</span>
                  
                  {/* Budget Allocation Progress Grid */}
                  <div className="space-y-2 pt-2 border-t border-border">
                    {['Cast', 'Crew', 'Props', 'Food', 'Equipment'].map((cat) => {
                      const cost = categoryTotals[cat] || 0;
                      const pct = totalBudget > 0 ? (cost / totalBudget) * 100 : 0;
                      return (
                        <div key={cat} className="space-y-1">
                          <div className="flex justify-between text-[10px]">
                            <span className="text-gray-400 font-semibold">{cat}</span>
                            <span className="text-gray-500 font-mono">${cost.toLocaleString()}</span>
                          </div>
                          <div className="w-full bg-black/40 h-1.5 rounded overflow-hidden">
                            <div style={{ width: `${pct}%` }} className="bg-amber-500 h-full rounded transition-all duration-500"></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="p-3 rounded border border-white/5 bg-[#0d0d18] space-y-3">
                  <h4 className="font-bold text-gray-200 text-xs">Add Expense</h4>
                  <form onSubmit={handleCreateBudgetItem} className="space-y-2">
                    <div className="space-y-1">
                      <label className="text-[10px] text-gray-500">Item Name</label>
                      <input
                        type="text"
                        placeholder="e.g. Dolly track lease, Catering..."
                        value={budgetName}
                        onChange={(e) => setBudgetName(e.target.value)}
                        className="w-full bg-[#07070c] border border-border rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-amber-500"
                        required
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="space-y-1">
                        <label className="text-[10px] text-gray-500">Category</label>
                        <select
                          value={budgetCategory}
                          onChange={(e) => setBudgetCategory(e.target.value)}
                          className="w-full bg-[#07070c] border border-border rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-amber-500"
                        >
                          <option>Cast</option>
                          <option>Crew</option>
                          <option>Props</option>
                          <option>Food</option>
                          <option>Equipment</option>
                        </select>
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] text-gray-500">Cost ($)</label>
                        <input
                          type="number"
                          value={budgetCost}
                          onChange={(e) => setBudgetCost(parseInt(e.target.value) || 0)}
                          className="w-full bg-[#07070c] border border-border rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-amber-500 font-mono"
                          required
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      className="w-full py-1 rounded bg-amber-500 hover:bg-amber-600 text-black font-bold transition-all shadow-md cursor-pointer text-center"
                    >
                      Save Item
                    </button>
                  </form>
                </div>
              </div>

              {/* Items List */}
              <div className="lg:col-span-2 space-y-2">
                <h4 className="font-bold text-gray-400 text-xs">Cost Estimation Sheet</h4>
                {budgetItems.length === 0 ? (
                  <div className="p-8 border border-white/5 bg-[#0d0d18] rounded flex flex-col items-center justify-center text-center text-gray-600">
                    <Wallet size={24} className="opacity-20 mb-1" />
                    <span>No budget estimations recorded yet. Use form to create items.</span>
                  </div>
                ) : (
                  <div className="border border-white/5 rounded-md overflow-hidden bg-[#0c0c16]">
                    <table className="w-full text-left text-[11px]">
                      <thead>
                        <tr className="bg-white/5 border-b border-border text-gray-400 uppercase font-semibold text-[9px]">
                          <th className="p-2">Name</th>
                          <th className="p-2">Category</th>
                          <th className="p-2 text-right">Cost</th>
                          <th className="p-2 text-center w-12">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {budgetItems.map((item) => (
                          <tr key={item.id} className="border-b border-border hover:bg-white/5 transition-colors">
                            <td className="p-2 font-semibold text-gray-200">{item.name}</td>
                            <td className="p-2">
                              <span className="px-1.5 py-0.5 rounded bg-black/40 text-[9px] border border-white/5">
                                {item.category}
                              </span>
                            </td>
                            <td className="p-2 text-right font-mono text-amber-500 font-semibold">${item.cost.toLocaleString()}</td>
                            <td className="p-2 text-center">
                              <button
                                onClick={() => handleDeleteBudgetItem(item.id)}
                                className="p-1 rounded text-gray-600 hover:text-red-400 transition-colors cursor-pointer"
                              >
                                <Trash size={12} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
type Dict<K extends string, V> = { [key in K]?: V };
