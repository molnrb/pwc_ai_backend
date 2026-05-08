import React from 'react';
import { Upload, Plus, FileText, Trash2 } from 'lucide-react';
import type { PendingUploadFile } from './NewAudit';

const formatSize = (size: number) => {
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${Math.max(1, Math.round(size / 1024))} KB`;
};

const toPendingFile = (file: File): PendingUploadFile => ({
  file,
  id: `${file.name}-${file.size}-${file.lastModified}`,
  name: file.name,
  sizeLabel: formatSize(file.size),
});

interface Props {
  files: PendingUploadFile[];
  setFiles: React.Dispatch<React.SetStateAction<PendingUploadFile[]>>;
}

export const StepUpload = ({ files, setFiles }: Props) => {
  const statementInputRef = React.useRef<HTMLInputElement | null>(null);
  const supportInputRef = React.useRef<HTMLInputElement | null>(null);

  const mergeFiles = (selected: FileList | null, replacePdf: boolean) => {
    if (!selected || selected.length === 0) return;

    const nextFiles = Array.from(selected).map(toPendingFile);
    setFiles((prev) => {
      const deduped = new Map<string, PendingUploadFile>();
      const retained = replacePdf ? prev.filter((entry) => !entry.name.toLowerCase().endsWith('.pdf')) : prev;

      [...retained, ...nextFiles].forEach((entry) => {
        deduped.set(entry.id, entry);
      });

      return Array.from(deduped.values());
    });
  };

  return (
    <div className="space-y-8">
      <h2 className="text-xl font-bold text-white uppercase tracking-tight">Step 1 of 3: Upload Documents</h2>
      
      <div className="space-y-4">
        <input
          ref={statementInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={(event) => {
            mergeFiles(event.target.files, true);
            event.target.value = '';
          }}
        />
        <div 
          className="border-2 border-dashed border-[#3D3D4E] hover:border-[#E8521A] transition-colors p-16 flex flex-col items-center justify-center gap-4 cursor-pointer rounded-sm bg-[#2C2C3E]/30"
          onClick={() => statementInputRef.current?.click()}
        >
          <Upload className="w-12 h-12 text-slate-500" />
          <p className="text-slate-400 font-medium tracking-wide text-center">Drop your ESRS E1 sustainability statement PDF here</p>
          <p className="text-[10px] uppercase font-bold text-slate-600 tracking-widest">or click to browse</p>
        </div>

        <input
          ref={supportInputRef}
          type="file"
          accept=".pdf,.csv,.xlsx,.xls,application/pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
          multiple
          className="hidden"
          onChange={(event) => {
            mergeFiles(event.target.files, false);
            event.target.value = '';
          }}
        />
        <div className="border-2 border-dashed border-[#3D3D4E] hover:border-[#E8521A] transition-colors p-8 flex flex-col items-center justify-center gap-2 cursor-pointer rounded-sm bg-[#1A1A2E]/50" onClick={() => supportInputRef.current?.click()}>
          <div className="flex items-center gap-2 text-slate-500">
            <Plus className="w-5 h-5" />
            <span className="text-xs uppercase font-bold tracking-widest">Supporting source files (Excel, CSV)</span>
          </div>
        </div>
      </div>

      {files.length > 0 && (
        <div className="space-y-3">
          <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest">Uploaded Files ({files.length})</p>
          {files.map((f) => (
            <div key={f.id} className="flex items-center justify-between bg-[#2C2C3E] p-3 border border-[#3D3D4E] rounded-sm">
              <div className="flex items-center gap-3">
                <FileText className="w-4 h-4 text-emerald-500" />
                <span className="text-sm text-slate-300 font-mono">{f.name}</span>
              </div>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  setFiles((prev) => prev.filter((entry) => entry.id !== f.id));
                }} 
                className="text-slate-600 hover:text-red-500 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">
        Launch replaces the current backend input workspace with the selected files.
      </p>
    </div>
  );
};
