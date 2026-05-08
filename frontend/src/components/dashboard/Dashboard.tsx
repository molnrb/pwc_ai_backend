import React from 'react';
import { FileSearch, CheckCircle2, AlertCircle, X } from 'lucide-react';
import { SummaryCard } from './SummaryCard';
import { ESRS_COLORS } from '../../constants/esrs';
import { type Evidence, type Summary } from '../../services/api';

interface FeedEntry { agent: string; timestamp: string; message: string; }

interface Props {
  evidence: Evidence[];
  summary: Summary | null;
  feed: FeedEntry[];
}

export const Dashboard = ({ evidence, summary, feed }: Props) => {
  const stats = [
    { label: 'Total Findings', val: summary?.total ?? evidence.length, icon: FileSearch, color: '#888888' },
    { label: 'Green', val: summary?.green_count ?? evidence.filter(e => e.flag === 'green').length, icon: CheckCircle2, color: ESRS_COLORS.OK },
    { label: 'Review / Yellow', val: summary?.yellow_count ?? evidence.filter(e => e.flag === 'yellow').length, icon: AlertCircle, color: ESRS_COLORS.REVIEW },
    { label: 'Red Flags', val: summary?.red_count ?? evidence.filter(e => e.flag === 'red').length, icon: X, color: ESRS_COLORS.ERROR },
  ];

  return (
    <div className="p-8 space-y-10 overflow-y-auto custom-scrollbar flex-1 bg-[#1A1A2E]">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((s, i) => (
          <SummaryCard key={i} label={s.label} val={String(s.val)} icon={s.icon} color={s.color} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-[#2C2C3E] border border-[#3D3D4E] p-6 rounded-sm flex flex-col">
          <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-500 mb-4">VERDICT</h3>
          <div className="flex-1 flex items-center justify-center">
            <p className={`text-xl font-bold ${(summary?.red_count ?? 0) === 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {summary?.verdict ?? 'Loading...'}
            </p>
          </div>
          <p className="text-xs text-slate-400 mt-4 leading-relaxed">{summary?.materiality_note ?? ''}</p>
        </div>

        <div className="bg-[#2C2C3E] border border-[#3D3D4E] p-6 rounded-sm">
          <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-500 mb-6">RECENT ACTIVITY</h3>
          <div className="space-y-4">
            {feed.slice(0, 5).map((f, i) => (
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
            {feed.length === 0 && (
              <p className="text-xs text-slate-600 uppercase tracking-widest text-center py-8">No activity yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
