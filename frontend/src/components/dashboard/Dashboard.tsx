import { FileSearch, CheckCircle2, AlertCircle, X, ShieldAlert, ArrowRight, FileJson } from 'lucide-react';
import { SummaryCard } from './SummaryCard';
import { ESRS_COLORS } from '../../constants/esrs';
import { type Evidence, type Summary } from '../../services/api';

interface FeedEntry { agent: string; timestamp: string; message: string; }

interface Props {
  evidence: Evidence[];
  summary: Summary | null;
  feed: FeedEntry[];
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

export const Dashboard = ({ evidence, summary, feed }: Props) => {
  const redFlags = evidence.filter(e => e.flag === 'red');
  const tracedFindings = evidence.filter(e => e.source_file != null);
  const total = summary?.total ?? evidence.length;

  const stats = [
    { label: 'Total Findings', val: total, icon: FileSearch, color: '#888888' },
    { label: 'Green / OK', val: summary?.green_count ?? evidence.filter(e => e.flag === 'green').length, icon: CheckCircle2, color: ESRS_COLORS.OK },
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

      {/* Demo Narrative Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1 space-y-8">
          {/* Verdict */}
          <div className="bg-[#2C2C3E] border border-[#3D3D4E] p-6 rounded-sm">
            <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-500 mb-4">VERDICT</h3>
            <div className="flex items-center gap-3">
              <ShieldAlert className={`w-8 h-8 ${(summary?.red_count ?? 0) === 0 ? 'text-emerald-400' : 'text-red-400'}`} />
              <p className={`text-xl font-bold ${(summary?.red_count ?? 0) === 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {summary?.verdict ?? 'Loading...'}
              </p>
            </div>
            {summary?.materiality_note && (
              <p className="text-xs text-slate-400 mt-4 leading-relaxed">{summary.materiality_note}</p>
            )}
          </div>

          {/* Evidence Package Download */}
          <button
            onClick={() => downloadEvidencePackage(evidence, summary)}
            className="w-full bg-[#2C2C3E] border border-[#3D3D4E] hover:border-[#E8521A] p-4 rounded-sm flex items-center gap-3 transition-colors group"
          >
            <FileJson className="w-5 h-5 text-slate-500 group-hover:text-[#E8521A] transition-colors" />
            <div className="text-left">
              <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400 group-hover:text-[#E8521A] transition-colors">Evidence Package</p>
              <p className="text-[10px] text-slate-600">Download audit-ready JSON</p>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-[#E8521A] ml-auto transition-colors" />
          </button>

          {/* Quick Stats */}
          <div className="bg-[#2C2C3E] border border-[#3D3D4E] p-6 rounded-sm space-y-4">
            <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-500">COVERAGE</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-2xl font-bold text-white">{total}</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-500">Claims Analyzed</p>
              </div>
              <div className="space-y-1">
                <p className="text-2xl font-bold text-white">{tracedFindings.length}</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-500">Source Traces</p>
              </div>
              <div className="space-y-1">
                <p className="text-2xl font-bold text-white">{redFlags.length}</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-500">Red Flags</p>
              </div>
              <div className="space-y-1">
                <p className="text-2xl font-bold text-white">E1</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-500">Scope</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Red Flags Detail + Activity */}
        <div className="lg:col-span-2 space-y-8">
          {/* Red Flags Detail */}
          <div className="bg-[#2C2C3E] border border-[#3D3D4E] p-6 rounded-sm">
            <div className="flex items-center gap-2 mb-6">
              <div className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
              <h3 className="text-[11px] font-bold uppercase tracking-widest text-slate-500">CRITICAL FINDINGS — REQUIRES REVIEW</h3>
            </div>
            {redFlags.length > 0 ? (
              <div className="space-y-4">
                {redFlags.map((flag, i) => (
                  <div key={i} className="p-4 bg-[#1A1A2E] border border-[#3D3D4E] border-l-[3px] border-l-[#EF4444] rounded-sm">
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-2">
                        <p className="text-sm font-bold text-white">{flag.data_point}</p>
                        <p className="text-[11px] text-slate-400 leading-relaxed">{flag.explanation}</p>
                        <div className="flex items-center gap-4 text-[10px] font-mono text-slate-500">
                          <span>Claimed: <span className="text-slate-300">{flag.claimed_value} {flag.unit}</span></span>
                          <span>Actual: <span className="text-slate-300">{flag.source_value} {flag.unit}</span></span>
                          {flag.deviation_pct != null && (
                            <span className="text-red-400 font-bold">Δ {flag.deviation_pct}%</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-600 uppercase tracking-widest text-center py-6">No critical findings — all claims verified</p>
            )}
          </div>

          {/* Recent Activity */}
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
    </div>
  );
};