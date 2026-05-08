import React from 'react';
import { Menu, Clock, Play } from 'lucide-react';

export const Header = ({ view, setIsSidebarOpen }: any) => {
  return (
    <header className="h-16 border-b border-[#3D3D4E] flex items-center justify-between px-6 bg-[#1A1A2E]/50 backdrop-blur-sm z-30 shrink-0">
      <div className="flex items-center gap-4">
        <button className="lg:hidden p-2 -ml-2 text-slate-500 hover:text-white" onClick={() => setIsSidebarOpen(true)}>
          <Menu className="w-6 h-6" />
        </button>
        <h2 className="text-lg font-bold text-white uppercase tracking-tight truncate">
          {view === 'Audit Logs' ? 'CSRD FY24 Phase 1' : view}
        </h2>
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 bg-white/5 rounded-full border border-[#3D3D4E]">
          <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">In Progress 82%</span>
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-6">
        <div className="hidden sm:flex items-center gap-2 text-slate-500">
          <Clock className="w-4 h-4" />
          <span className="text-xs font-mono">Last Run: 14:22:09</span>
        </div>
        <button className="flex items-center gap-2 bg-[#E8521A] hover:bg-[#E8521A]/90 text-white px-4 py-1.5 rounded-sm font-bold text-sm uppercase tracking-wide transition-colors">
          <Play className="w-3.5 h-3.5 fill-current" />
          <span className="hidden xs:inline">Run Audit</span>
          <span className="xs:hidden">Run</span>
        </button>
      </div>
    </header>
  );
};
