import React from 'react';
import { FileSearch, CheckCircle2, AlertCircle, X } from 'lucide-react';
import { SummaryCard } from './SummaryCard';
import { ESRS_COLORS } from '../../constants/esrs';
import { FEED } from '../../data/mockData';

export const Dashboard = () => {
  const stats = [
    { label: 'Total Extracts', val: '248', icon: FileSearch, color: '#888888' },
    { label: 'OK', val: '180', icon: CheckCircle2, color: ESRS_COLORS.OK },
    { label: 'Review needed', val: '52', icon: AlertCircle, color: ESRS_COLORS.REVIEW },
    { label: 'Errors', val: '16', icon: X, color: ESRS_COLORS.ERROR },
  ];

  const chartData = [
    { label: 'Scope 1', ok: 85, review: 10, error: 5 },
    { label: 'Scope 2', ok: 60, review: 20, error: 20 },
    { label: 'Scope 3', ok: 70, review: 20, error: 10 },
    { label: 'Energy', ok: 90, review: 5, error: 5 },
    { label: 'Renewables', ok: 80, review: 15, error: 5 },
    { label: 'Transition', ok: 40, review: 50, error: 10 },
  ];

  return (
    <div className="p-8 space-y-10 overflow-y-auto custom-scrollbar flex-1 bg-[#1A1A2E]">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((s, i) => (
          <SummaryCard key={i} {...s} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-[#2C2C3E] border border-[#3D3D4E] p-6 rounded-sm flex flex-col">
          <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-500 mb-8">E1 CLIMATE AUDIT PROGRESS</h3>
          <div className="flex-1 flex items-end justify-between px-4 pb-4 h-64 gap-6 sm:gap-10">
            {chartData.map((d, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-3 h-full">
                <div className="w-full flex flex-col-reverse rounded-sm overflow-hidden h-full bg-white/5">
                  <div style={{ height: `${d.ok}%`, backgroundColor: ESRS_COLORS.OK }} />
                  <div style={{ height: `${d.review}%`, backgroundColor: ESRS_COLORS.REVIEW }} />
                  <div style={{ height: `${d.error}%`, backgroundColor: ESRS_COLORS.ERROR }} />
                </div>
                <span className="text-[9px] font-mono text-slate-400 font-bold uppercase text-center hidden sm:block">{d.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-[#2C2C3E] border border-[#3D3D4E] p-6 rounded-sm">
          <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-500 mb-6">RECENT ACTIVITY</h3>
          <div className="space-y-4">
            {FEED.slice(0, 5).map((f, i) => (
              <div key={i} className="flex gap-4 items-start p-3 bg-[#1A1A2E]/30 rounded-sm border border-[#3D3D4E]/50">
                <div className="mt-1.5 w-1 h-1 rounded-full bg-slate-600 shrink-0" />
                <div className="space-y-1">
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <span className="font-bold opacity-60">[{f.agent}]</span> {f.message}
                  </p>
                  <p className="text-[10px] font-mono text-slate-600 uppercase">{f.timestamp}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
