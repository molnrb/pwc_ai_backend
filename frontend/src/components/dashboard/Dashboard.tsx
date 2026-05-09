import { useState } from 'react';
import { FileSearch, X, ShieldAlert, ArrowRight, FileJson } from 'lucide-react';
import { SummaryCard } from './SummaryCard';
import { ESRS_COLORS } from '../../constants/esrs';
import { downloadReportPackage, type Evidence, type HealthStatus, type Summary } from '../../services/api';
import { getEvidenceKey } from '../../utils/evidenceKey';

interface FeedEntry { agent: string; timestamp: string; message: string; }

interface Props {
  evidence: Evidence[];
  summary: Summary | null;
  health: HealthStatus | null;
  feed: FeedEntry[];
}

export const Dashboard = ({ evidence, summary, health, feed }: Props) => {
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const redFlags = evidence.filter(e => e.flag === 'red');
  const tracedFindings = evidence.filter(e => e.source_file != null);
  const total = summary?.total ?? evidence.length;
  const filesChecked = health?.input_file_count ?? 0;
  const reviewRequired = summary?.review_required ?? false;

  const handleDownloadReport = async () => {
    setDownloadError(null);
    setIsDownloading(true);

    try {
      await downloadReportPackage();
    } catch (err: any) {
      setDownloadError(err.message || 'Evidence package download failed.');
    } finally {
      setIsDownloading(false);
    }
  };

  const stats = [
    { label: 'Total Findings', val: total, icon: FileSearch, color: '#888888' },
    { label: 'Red Flags', val: summary?.red_count ?? evidence.filter(e => e.flag === 'red').length, icon: X, color: ESRS_COLORS.ERROR },
    { label: 'Files Checked', val: filesChecked, icon: FileJson, color: '#888888' },
    { label: 'Review Required', val: reviewRequired ? 'YES' : 'NO', icon: ShieldAlert, color: reviewRequired ? ESRS_COLORS.ERROR : ESRS_COLORS.OK },
  ];

  return (
    <div className="p-8 space-y-10 overflow-y-auto custom-scrollbar flex-1 bg-[#1A1A2E]">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <SummaryCard key={stat.label} label={stat.label} val={String(stat.val)} icon={stat.icon} color={stat.color} />
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
            onClick={() => void handleDownloadReport()}
            disabled={isDownloading}
            className="w-full bg-[#2C2C3E] border border-[#3D3D4E] hover:border-[#E8521A] p-4 rounded-sm flex items-center gap-3 transition-colors group"
          >
            <FileJson className="w-5 h-5 text-slate-500 group-hover:text-[#E8521A] transition-colors" />
            <div className="text-left">
              <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400 group-hover:text-[#E8521A] transition-colors">Evidence Package</p>
              <p className="text-[10px] text-slate-600">{isDownloading ? 'Preparing full audit package...' : 'Download backend audit package JSON'}</p>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-[#E8521A] ml-auto transition-colors" />
          </button>
          {downloadError && (
            <div className="mt-3 p-3 bg-red-400/5 border border-red-400/30 rounded-sm text-center text-xs text-red-400 font-medium">
              {downloadError}
            </div>
          )}

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
                {redFlags.map((flag, index) => (
                  <div key={getEvidenceKey(flag, index)} className="p-4 bg-[#1A1A2E] border border-[#3D3D4E] border-l-[3px] border-l-[#EF4444] rounded-sm">
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

        </div>
      </div>
    </div>
  );
};