import React from 'react';

export const StepReview = ({ files, onComplete }: any) => {
  return (
    <div className="space-y-8">
      <h2 className="text-xl font-bold text-white uppercase tracking-tight">Step 3 of 3: Review & Launch</h2>
      
      <div className="bg-[#2C2C3E] border border-[#3D3D4E] rounded-sm p-6 space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-2">Uploaded Files</p>
            <div className="space-y-1">
              {files.map((f: any, i: number) => (
                <p key={i} className="text-xs text-white font-mono flex justify-between">
                  <span>{f.name}</span>
                  <span className="opacity-50">{f.size}</span>
                </p>
              ))}
              {files.length === 0 && <p className="text-xs text-slate-500 italic">No files uploaded</p>}
            </div>
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-2">Project Name</p>
            <p className="text-sm text-white font-medium">E1 Climate Resilience Audit</p>
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-2">Scope</p>
            <p className="text-sm text-white font-bold text-[#E8521A]">E1 Climate</p>
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-2">Reporting Year</p>
            <p className="text-sm text-white font-medium">2024</p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <button 
          onClick={onComplete}
          className="w-full bg-[#E8521A] hover:bg-[#E8521A]/90 text-white p-6 rounded-sm font-bold uppercase tracking-[0.2em] text-lg shadow-2xl shadow-[#E8521A]/30 active:scale-95 transition-all"
        >
          Launch Audit
        </button>
        <p className="text-center text-[10px] text-slate-500 font-bold uppercase tracking-widest">
          Atlas will notify you when the audit is complete
        </p>
      </div>
    </div>
  );
};
