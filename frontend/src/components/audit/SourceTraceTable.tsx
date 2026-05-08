import React from 'react';
import { Filter, Download } from 'lucide-react';
import { TRACE_DETAILS } from '../../data/mockData';
import { ESRS_COLORS } from '../../constants/esrs';

export const SourceTraceTable = () => {
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
              <th className="py-3 px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold">File Name</th>
              <th className="py-3 px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold">Sheet</th>
              <th className="py-3 px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold">Ref</th>
              <th className="py-3 px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold text-right">Value</th>
              <th className="py-3 px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold text-right">Deviation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            {TRACE_DETAILS.map((row, idx) => (
              <tr key={idx} className="hover:bg-white/[0.01] transition-colors group min-h-[48px]">
                <td className="py-4 px-6 text-[11px] font-mono text-[#F59E0B]/80 group-hover:text-[#F59E0B]">{row.fileName}</td>
                <td className="py-4 px-6 text-[11px] text-slate-400 group-hover:text-slate-300">{row.sheet}</td>
                <td className="py-4 px-6 text-[11px] font-mono text-slate-400 group-hover:text-slate-300">{row.ref}</td>
                <td className="py-4 px-6 text-[11px] font-mono text-slate-400 group-hover:text-slate-300 text-right">{row.value}</td>
                <td className="py-4 px-6 text-[11px] font-mono text-right">
                  <span className={`
                    ${row.deviation === '0.00%' ? 'text-[#888888]' : 
                      row.deviation === 'REVIEWED' ? 'text-[#F59E0B]' :
                      'text-[#EF4444] font-bold'
                    }
                  `}>
                    {row.deviation}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
