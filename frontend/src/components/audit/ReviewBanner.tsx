import { AlertTriangle, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { useState } from 'react';
import type { Evidence } from '../../services/api';

interface Props {
    evidence: Evidence[];
}

export const ReviewBanner = ({ evidence }: Props) => {
    const redFlags = evidence.filter((e) => e.flag === 'red');
    const [expanded, setExpanded] = useState(false);

    if (redFlags.length === 0) return null;

    return (
        <div className="border-t-2 border-[#EF4444]/60 bg-[#2C1A1A]">
            <button
                onClick={() => setExpanded((v) => !v)}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-[#3a2020] transition-colors"
            >
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                <span className="text-[11px] font-bold uppercase tracking-widest text-red-400">
                    Review Required — {redFlags.length} Red Flag{redFlags.length > 1 ? 's' : ''}
                </span>
                <span className="ml-auto text-[10px] font-mono text-red-400/60">{redFlags.length} finding{redFlags.length > 1 ? 's' : ''}</span>
                {expanded ? (
                    <ChevronUp className="w-4 h-4 text-red-400/60" />
                ) : (
                    <ChevronDown className="w-4 h-4 text-red-400/60" />
                )}
            </button>

            {expanded && (
                <div className="px-4 pb-3 space-y-2">
                    {redFlags.map((flag, i) => (
                        <div
                            key={i}
                            className="flex items-start gap-3 p-3 bg-[#1A1A2E] border border-[#3D3D4E] border-l-[3px] border-l-[#EF4444] rounded-sm text-[11px]"
                        >
                            <div className="flex-1 min-w-0 space-y-1">
                                <p className="text-white font-bold truncate">{flag.data_point}</p>
                                <p className="text-slate-400 text-[10px] leading-relaxed">{flag.explanation}</p>
                                <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500 pt-0.5">
                                    <span>Claimed: {flag.claimed_value} {flag.unit}</span>
                                    <span>Source: {flag.source_value} {flag.unit}</span>
                                    {flag.deviation_pct != null && (
                                        <span className="text-red-400 font-bold">Δ {flag.deviation_pct}%</span>
                                    )}
                                </div>
                            </div>
                            {flag.source_file && (
                                <div className="flex items-center gap-1 text-[10px] text-slate-500 shrink-0 pt-1">
                                    <ExternalLink className="w-3 h-3" />
                                    <span className="max-w-[120px] truncate">{flag.source_file}</span>
                                    {flag.source_cell && <span className="opacity-50">{flag.source_cell}</span>}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};