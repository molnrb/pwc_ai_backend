import { useState, useRef } from 'react';
import { Upload, Plus, FileText, Trash2, CheckCircle2 } from 'lucide-react';
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
  const statementInputRef = useRef<HTMLInputElement | null>(null);
  const supportInputRef = useRef<HTMLInputElement | null>(null);
  const [dragOverStatement, setDragOverStatement] = useState(false);
  const [dragOverSupport, setDragOverSupport] = useState(false);

  const openStatementPicker = () => statementInputRef.current?.click();
  const openSupportPicker = () => supportInputRef.current?.click();

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

  const handleDrop = (e: React.DragEvent, isStatement: boolean) => {
    e.preventDefault();
    setDragOverStatement(false);
    setDragOverSupport(false);
    mergeFiles(e.dataTransfer.files, isStatement);
  };

  const handleDropZoneKeyDown = (event: React.KeyboardEvent, onActivate: () => void) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onActivate();
    }
  };

  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((entry) => entry.id !== fileId));
  };

  const statementFile = files.find(f => f.name.toLowerCase().endsWith('.pdf'));

  return (
    <div className="space-y-8">
      <h2 className="text-xl font-bold text-white uppercase tracking-tight">Step 1 of 3: Upload Documents</h2>

      <div className="space-y-4 max-w-[800px] mx-auto">
        {/* Statement PDF Upload */}
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
        <button
          type="button"
          className={`w-full border-2 border-dashed transition-colors py-12 flex flex-col items-center justify-center gap-4 cursor-pointer rounded-sm ${dragOverStatement ? 'border-[#E8521A] bg-[#E8521A]/5' : 'border-[#3D3D4E] hover:border-[#E8521A] bg-[#2C2C3E]/30'
            }`}
          onClick={openStatementPicker}
          onKeyDown={(event) => handleDropZoneKeyDown(event, openStatementPicker)}
          onDragOver={(e) => { e.preventDefault(); setDragOverStatement(true); }}
          onDragLeave={() => setDragOverStatement(false)}
          onDrop={(e) => handleDrop(e, true)}
        >
          {statementFile ? (
            <>
              <CheckCircle2 className="w-10 h-10 text-emerald-400" />
              <span className="text-white font-bold">{statementFile.name}</span>
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-widest">{statementFile.sizeLabel} · Statement PDF</span>
              <span className="text-[10px] text-slate-600 tracking-wider">Drop a new PDF to replace, or click to change</span>
            </>
          ) : (
            <>
              <Upload className="w-10 h-10 text-slate-500" />
              <span className="text-slate-300 font-medium tracking-wide text-center">Drop your ESRS E1 sustainability statement PDF here</span>
              <span className="text-[10px] uppercase font-bold text-slate-600 tracking-widest">PDF · Required</span>
            </>
          )}
        </button>

        {/* Supporting Files Upload */}
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
        <button
          type="button"
          className={`w-full border-2 border-dashed transition-colors py-12 flex flex-col items-center justify-center gap-2 cursor-pointer rounded-sm ${dragOverSupport ? 'border-[#E8521A] bg-[#E8521A]/5' : 'border-[#3D3D4E] hover:border-[#E8521A] bg-[#1A1A2E]/50'
            }`}
          onClick={openSupportPicker}
          onKeyDown={(event) => handleDropZoneKeyDown(event, openSupportPicker)}
          onDragOver={(e) => { e.preventDefault(); setDragOverSupport(true); }}
          onDragLeave={() => setDragOverSupport(false)}
          onDrop={(e) => handleDrop(e, false)}
        >
          <div className="flex items-center gap-2 text-slate-500">
            <Plus className="w-5 h-5" />
            <span className="text-xs uppercase font-bold tracking-widest">Supporting source files — Excel, CSV, PDF</span>
          </div>
          <span className="text-[10px] text-slate-600 tracking-wider">Optional — drag & drop or click to browse</span>
        </button>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest">Selected Files ({files.length})</p>
          </div>
          {files.map((f) => (
            <div key={f.id} className="flex items-center justify-between bg-[#2C2C3E] p-3 border border-[#3D3D4E] rounded-sm group hover:border-white/10 transition-colors">
              <div className="flex items-center gap-3 min-w-0">
                <FileText className={`w-4 h-4 shrink-0 ${f.name.toLowerCase().endsWith('.pdf') ? 'text-emerald-400' : 'text-[#E8521A]'}`} />
                <span className="text-sm text-slate-300 font-mono truncate">{f.name}</span>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-[10px] text-slate-600 font-mono">{f.sizeLabel}</span>
                <button
                  type="button"
                  onClick={() => removeFile(f.id)}
                  className="text-slate-600 hover:text-red-500 transition-colors p-1"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">
        One statement PDF required · Supporting source files improve trace accuracy
      </p>
    </div>
  );
};