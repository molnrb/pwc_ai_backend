import React from 'react';
import { Filter, Download } from 'lucide-react';
import { type Evidence } from '../../services/api';

interface Props {
  evidence: Evidence[];
}

export const SourceTraceTable = ({ evidence }: Props) => {
  return (
    <div className="flex-1 flex flex-col overflow-hidden min-h-0">
      <div className="p-4 border-b border-[#3D3D4E] flex items-center justify-between bg-[#16162a] h-10 shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Source Trace Details</span>
        <div className="flex items-center gap-3">
          <Filter className="w-4 h-4 text-slate-500 cursor-pointer hover:text-slate-300" />
          <Download className="w-4 h-4 text-slate-500 cursor-pointer hover:text-slate-300" />
        </div>
      </div>
      
      <div className="flex-1 overflow-auto custom-scrollbar bg-[#1A1A2E]">
        <table className="w-full text-left border-collapse min-w-[700px]">
          <thead>
            <tr className="bg-[#16162a] sticky top-0 backdrop-blur-sm z-10 border-b border-[#3D3D4E]">
              <th className="py-3 px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold">Data Point</th>
              <th className="py-3 px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold">Source File</th>
              <th className="py-3 px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold">Sheet / Ref</th>
              <th className="py-3 px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold">Cell</th>
              <th className="py-3 px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold text-right">Source Value</th>
              <th className="py-3 px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold text-right">Deviation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            {evidence.map((row, idx) => (
              <tr key={idx} className="hover:bg-white/[0.01] transition-colors group min-h-[48px]">
                <td className="py-4 px-6 text-[11px] font-mono text-[#F59E0B]/80 group-hover:text-[#F59E0B]">{row.data_point}</td>
                <td className="py-4 px-6 text-[11px] text-slate-400 group-hover:text-slate-300">{row.source_file || 'N/A'}</td>
                <td className="py-4 px-6 text-[11px] font-mono text-slate-400 group-hover:text-slate-300">{row.source_sheet || '—'}</td>
                <td className="py-4 px-6 text-[11px] font-mono text-slate-400 group-hover:text-slate-300">{row.source_cell || '—'}</td>
                <td className="py-4 px-6 text-[11px] font-mono text-slate-400 group-hover:text-slate-300 text-right">{row.source_value != null ? `${row.source_value} ${row.unit}` : 'N/A'}</td>
                <td className="py-4 px-6 text-[11px] font-mono text-right">
                  <span className={
                    row.deviation_pct == null ? 'text-[#888]'
                    : row.deviation_pct === 0 ? 'text-[#888]'
                    : row.deviation_pct > 0.5 ? 'text-[#EF4444] font-bold'
                    : 'text-[#F59E0B]'
                  }>
                    {row.deviation_pct != null ? `${row.deviation_pct}%` : 'N/A'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {evidence.length === 0 && (
          <div className="flex items-center justify-center h-full py-20 text-slate-600 text-xs uppercase tracking-widest">
            No evidence loaded — run an audit or start the live stream
          </div>
        )}
      </div>
    </div>
  );
};
