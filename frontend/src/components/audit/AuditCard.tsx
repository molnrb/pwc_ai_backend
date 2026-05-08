import React from 'react';
import { ESRS_COLORS } from '../../constants/esrs';
import { type Evidence } from '../../services/api';

const FLAG_MAP: Record<string, { bg: string; text: string; border: string }> = {
  green: { bg: ESRS_COLORS.OK, text: 'white', border: ESRS_COLORS.OK },
  yellow: { bg: ESRS_COLORS.REVIEW, text: 'black', border: ESRS_COLORS.REVIEW },
  red: { bg: ESRS_COLORS.ERROR, text: 'white', border: ESRS_COLORS.ERROR },
};

export const AuditCard = ({ extract }: { extract: Evidence }) => {
  const flagKey = extract.flag || 'grey';
  const styles = FLAG_MAP[flagKey] || { bg: '#888', text: 'white', border: '#888' };

  return (
    <div 
      className="bg-[#2C2C3E]/40 border border-[#3D3D4E] border-l-[3px] p-5 py-[20px] rounded-sm transition-all hover:bg-white/[0.04] cursor-pointer group"
      style={{ borderLeftColor: styles.border }}
    >
      <div className="flex justify-between items-start mb-3">
        <span 
          className="px-2 py-0.5 text-[11px] font-[700] tracking-[0.05em] uppercase rounded-sm"
          style={{ backgroundColor: styles.bg, color: styles.text }}
        >
          {extract.flag?.toUpperCase() || 'GREY'}
        </span>
        <span className="text-[10px] font-mono text-slate-500 tracking-wider">
          Page {extract.page}
        </span>
      </div>
      <h3 className="text-sm font-bold text-slate-200 leading-[1.5] mb-3 group-hover:text-white transition-colors">
        {extract.data_point}
      </h3>
      <div className="space-y-1">
        <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
          <span className="text-[9px] uppercase tracking-widest opacity-50">Claim:</span>
          <span>{extract.claimed_value} {extract.unit}</span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
          <span className="text-[9px] uppercase tracking-widest opacity-50">Source:</span>
          <span>{extract.source_file || 'N/A'}</span>
        </div>
        {extract.deviation_pct != null && (
          <div className="flex items-center gap-1.5 text-[10px] font-mono">
            <span className="text-[9px] uppercase tracking-widest opacity-50">Dev:</span>
            <span className={extract.deviation_pct > 0 ? 'text-[#EF4444] font-bold' : 'text-[#888]'}>
              {extract.deviation_pct}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
