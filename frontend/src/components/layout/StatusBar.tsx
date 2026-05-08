import React from 'react';
import { type Evidence, type Summary } from '../../services/api';

interface Props {
  evidence: Evidence[];
  summary: Summary | null;
  loading: boolean;
}

export const StatusBar = ({ evidence, summary, loading }: Props) => (
  <footer className="h-8 border-t border-[#3D3D4E] bg-[#141424] flex items-center gap-6 px-4 text-[9px] font-mono uppercase tracking-widest text-slate-500 shrink-0">
    <div className="flex items-center gap-1.5">
      <span className={loading ? 'text-blue-400' : 'text-emerald-400'}>{loading ? 'BUSY' : 'READY'}</span>
      <span className="opacity-80">{evidence.length} findings</span>
    </div>
    {summary && (
      <div className="flex items-center gap-1.5">
        <span className="text-[#F59E0B]">VERDICT</span>
        <span className="opacity-80">{summary.verdict}</span>
      </div>
    )}
    {summary && (
      <div className="flex items-center gap-1.5">
        <span className="text-red-400">RED</span>
        <span className="opacity-80">{summary.red_count}</span>
      </div>
    )}
    <div className="ml-auto hidden xs:flex items-center gap-4">
      <div className="flex items-center gap-1.5">
        <span className="opacity-40">API:</span>
        <span className="text-slate-400">/stream · /audit · /evidence</span>
      </div>
    </div>
  </footer>
);
