import React from 'react';

export const StatusBar = () => (
  <footer className="h-8 border-t border-[#3D3D4E] bg-[#141424] flex items-center gap-6 px-4 text-[9px] font-mono uppercase tracking-widest text-slate-500 shrink-0">
    <div className="flex items-center gap-1.5">
      <span className="text-blue-400">PROD</span>
      <span className="opacity-80">atlas-node-04</span>
    </div>
    <div className="flex items-center gap-1.5">
      <span className="text-[#F59E0B]">TOKEN</span>
      <span className="opacity-80">4,291/min</span>
    </div>
    <div className="ml-auto hidden xs:flex items-center gap-4">
      <div className="flex items-center gap-1.5">
        <span className="opacity-40">Keyboard Shortcuts:</span>
        <span className="text-slate-400">[CMD+K] Actions</span>
        <span className="text-slate-400">[CMD+G] Graph</span>
      </div>
    </div>
  </footer>
);
