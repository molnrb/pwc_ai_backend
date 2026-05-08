import { Filter, Download, FileJson } from 'lucide-react';
import { type Evidence, type Summary } from '../../services/api';

interface Props {
  evidence: Evidence[];
  summary: Summary | null;
}

const downloadEvidencePackage = (evidence: Evidence[], summary: Summary | null) => {
  const pkg = {
    generated_at: new Date().toISOString(),
    summary: summary ?? { total: evidence.length, green_count: 0, yellow_count: 0, red_count: 0, grey_count: 0, red_flags: [], verdict: 'N/A', materiality_note: '' },
    evidence,
  };
  const blob = new Blob([JSON.stringify(pkg, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `atlas-evidence-package-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
};

const FLAG_LABEL_MAP: Record<string, { label: string; color: string }> = {
  green: { label: 'OK', color: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30' },
  yellow: { label: 'REVIEW', color: 'text-amber-400 bg-amber-400/10 border-amber-400/30' },
  red: { label: 'FAIL', color: 'text-red-400 bg-red-400/10 border-red-400/30' },
  grey: { label: 'NO DATA', color: 'text-slate-500 bg-slate-400/10 border-slate-400/30' },
};

export const SourceTraceTable = ({ evidence, summary }: Props) => {
  return (
    <div className="flex-1 flex flex-col overflow-hidden min-h-0">
      <div className="p-4 border-b border-[#3D3D4E] flex items-center justify-between bg-[#16162a] h-10 shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Source Trace Details</span>
        <div className="flex items-center gap-3">
          <button
            onClick={() => downloadEvidencePackage(evidence, summary)}
            className="flex items-center gap-1.5 px-2 py-1 rounded-sm bg-[#1A1A2E] border border-[#3D3D4E] hover:border-[#E8521A] transition-colors text-[10px] uppercase tracking-widest text-slate-400 hover:text-[#E8521A] font-bold"
            title="Download evidence package JSON"
          >
            <FileJson className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Evidence Pkg</span>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto custom-scrollbar bg-[#1A1A2E]">
        <table className="w-full text-left border-collapse min-w-[800px]">
          <thead>
            <tr className="bg-[#16162a] sticky top-0 backdrop-blur-sm z-10 border-b border-[#3D3D4E]">
              <th className="py-3 px-4 text-[10px] uppercase tracking-widest text-slate-500 font-bold">Flag</th>
              <th className="py-3 px-4 text-[10px] uppercase tracking-widest text-slate-500 font-bold">Data Point</th>
              <th className="py-3 px-4 text-[10px] uppercase tracking-widest text-slate-500 font-bold">Source File</th>
              <th className="py-3 px-4 text-[10px] uppercase tracking-widest text-slate-500 font-bold">Sheet / Ref</th>
              <th className="py-3 px-4 text-[10px] uppercase tracking-widest text-slate-500 font-bold">Cell</th>
              <th className="py-3 px-4 text-[10px] uppercase tracking-widest text-slate-500 font-bold text-right">Source Value</th>
              <th className="py-3 px-4 text-[10px] uppercase tracking-widest text-slate-500 font-bold text-right">Deviation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            {evidence.map((row, idx) => {
              const flagStyle = FLAG_LABEL_MAP[row.flag || 'grey'] || FLAG_LABEL_MAP.grey;
              return (
                <tr key={idx} className="hover:bg-white/[0.01] transition-colors group min-h-[48px]">
                  <td className="py-4 px-4">
                    <span className={`inline-block px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded-sm border ${flagStyle.color}`}>
                      {flagStyle.label}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-[11px] font-mono text-[#F59E0B]/80 group-hover:text-[#F59E0B] max-w-[200px] truncate">{row.data_point}</td>
                  <td className="py-4 px-4 text-[11px] text-slate-400 group-hover:text-slate-300 max-w-[150px] truncate">{row.source_file || 'N/A'}</td>
                  <td className="py-4 px-4 text-[11px] font-mono text-slate-400 group-hover:text-slate-300">{row.source_sheet || '—'}</td>
                  <td className="py-4 px-4 text-[11px] font-mono text-slate-400 group-hover:text-slate-300">{row.source_cell || '—'}</td>
                  <td className="py-4 px-4 text-[11px] font-mono text-slate-400 group-hover:text-slate-300 text-right">
                    {row.source_value != null ? `${row.source_value.toLocaleString()} ${row.unit}` : 'N/A'}
                  </td>
                  <td className="py-4 px-4 text-[11px] font-mono text-right">
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
              );
            })}
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