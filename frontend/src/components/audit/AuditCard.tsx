import React from 'react';
import { ESRS_COLORS } from '../../constants/esrs';

export const AuditCard = ({ extract }: any) => {
  const getBadgeStyles = (status: string) => {
    switch (status) {
      case 'OK': return { bg: ESRS_COLORS.OK, text: 'white' };
      case 'REVIEW': return { bg: ESRS_COLORS.REVIEW, text: 'black' };
      case 'ERROR': return { bg: ESRS_COLORS.ERROR, text: 'white' };
      default: return { bg: '#888', text: 'white' };
    }
  };

  const badgeStyle = getBadgeStyles(extract.badge);
  const borderColor = extract.badge === 'OK' ? ESRS_COLORS.OK : extract.badge === 'REVIEW' ? ESRS_COLORS.REVIEW : ESRS_COLORS.ERROR;

  return (
    <div 
      className="bg-[#2C2C3E]/40 border border-[#3D3D4E] border-l-[3px] p-5 py-[20px] rounded-sm transition-all hover:bg-white/[0.04] cursor-pointer group"
      style={{ borderLeftColor: borderColor }}
    >
      <div className="flex justify-between items-start mb-3">
        <span 
          className="px-2 py-0.5 text-[11px] font-[700] tracking-[0.05em] uppercase rounded-sm"
          style={{ backgroundColor: badgeStyle.bg, color: badgeStyle.text }}
        >
          {extract.badge}
        </span>
        <span className="text-[10px] font-mono text-slate-500 tracking-wider">ID: {extract.id}</span>
      </div>
      <h3 className="text-sm font-bold text-slate-200 leading-[1.5] mb-3 group-hover:text-white transition-colors">
        {extract.title}
      </h3>
      <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
        <span className="text-[9px] uppercase tracking-widest opacity-50">File:</span>
        <span>{extract.filename}</span>
      </div>
    </div>
  );
};
