import React from 'react';
import { Upload, Plus, FileText, Trash2 } from 'lucide-react';

export const StepUpload = ({ files, setFiles }: any) => {
  return (
    <div className="space-y-8">
      <h2 className="text-xl font-bold text-white uppercase tracking-tight">Step 1 of 3: Upload Documents</h2>
      
      <div className="space-y-4">
        <div 
          className="border-2 border-dashed border-[#3D3D4E] hover:border-[#E8521A] transition-colors p-16 flex flex-col items-center justify-center gap-4 cursor-pointer rounded-sm bg-[#2C2C3E]/30"
          onClick={() => setFiles((prev: any) => [...prev, { name: `e1_statement_${Date.now()}.pdf`, size: '2.4 MB' }])}
        >
          <Upload className="w-12 h-12 text-slate-500" />
          <p className="text-slate-400 font-medium tracking-wide text-center">Drop your ESRS E1 sustainability statement PDF here</p>
          <p className="text-[10px] uppercase font-bold text-slate-600 tracking-widest">or click to browse</p>
        </div>

        <div className="border-2 border-dashed border-[#3D3D4E] hover:border-[#E8521A] transition-colors p-8 flex flex-col items-center justify-center gap-2 cursor-pointer rounded-sm bg-[#1A1A2E]/50">
          <div className="flex items-center gap-2 text-slate-500">
            <Plus className="w-5 h-5" />
            <span className="text-xs uppercase font-bold tracking-widest">Supporting source files (Excel, CSV)</span>
          </div>
        </div>
      </div>

      {files.length > 0 && (
        <div className="space-y-3">
          <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest">Uploaded Files ({files.length})</p>
          {files.map((f: any, i: number) => (
            <div key={i} className="flex items-center justify-between bg-[#2C2C3E] p-3 border border-[#3D3D4E] rounded-sm">
              <div className="flex items-center gap-3">
                <FileText className="w-4 h-4 text-emerald-500" />
                <span className="text-sm text-slate-300 font-mono">{f.name}</span>
              </div>
              <button 
                onClick={(e) => { e.stopPropagation(); setFiles(files.filter((_: any, idx: number) => idx !== i)); }} 
                className="text-slate-600 hover:text-red-500 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
