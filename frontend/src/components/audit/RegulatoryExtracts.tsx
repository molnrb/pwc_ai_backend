import React from 'react';
import { AuditCard } from './AuditCard';
import { EXTRACTS } from '../../data/mockData';

export const RegulatoryExtracts = () => {
  return (
    <div className="w-full lg:w-[400px] lg:min-width-[320px] border-r border-[#3D3D4E] flex flex-col h-full bg-[#16162a] shrink-0">
      <div className="p-4 border-b border-[#3D3D4E] flex items-center justify-between bg-[#1A1A2E]/30 h-10 shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Regulatory Extracts</span>
        <span className="text-[10px] font-mono text-slate-500">{EXTRACTS.length} TOTAL</span>
      </div>
      
      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-2 p-2">
        {EXTRACTS.map((extract) => (
          <AuditCard key={extract.id} extract={extract} />
        ))}
      </div>
    </div>
  );
};
