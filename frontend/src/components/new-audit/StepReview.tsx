import type { PendingUploadFile } from './NewAudit';

interface Props {
  files: PendingUploadFile[];
  onComplete: () => void;
  submitting: boolean;
  error: string | null;
}

export const StepReview = ({ files, onComplete, submitting, error }: Props) => {
  return (
    <div className="space-y-8">
      <h2 className="text-xl font-bold text-white uppercase tracking-tight">Step 3 of 3: Review & Launch</h2>

      <div className="bg-[#2C2C3E] border border-[#3D3D4E] rounded-sm p-6 space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-2">Uploaded Files</p>
            <div className="space-y-1">
              {files.map((f) => (
                <p key={f.id} className="text-xs text-white font-mono flex justify-between">
                  <span className="truncate mr-2">{f.name}</span>
                  <span className="opacity-50 shrink-0">{f.sizeLabel}</span>
                </p>
              ))}
              {files.length === 0 && <p className="text-xs text-slate-500 italic">No files uploaded</p>}
            </div>
          </div>
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-widest mb-2">Audit Configuration</p>
            <div className="space-y-2">
              <p className="text-sm text-white font-medium">E1 Climate Resilience Audit</p>
              <p className="text-xs text-slate-400">Reporting Year: <span className="text-white font-bold">2024</span></p>
              <p className="text-xs">
                <span className="text-[#E8521A] font-bold">E1</span>
                <span className="text-slate-500"> — Climate Change</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <button
          onClick={onComplete}
          disabled={submitting}
          className="w-full bg-[#E8521A] hover:bg-[#E8521A]/90 disabled:bg-[#3D3D4E] disabled:text-slate-500 text-white p-6 rounded-sm font-bold uppercase tracking-[0.2em] text-lg shadow-2xl shadow-[#E8521A]/30 active:scale-95 transition-all"
        >
          {submitting ? 'Launching audit...' : 'Launch Audit'}
        </button>
        {error && (
          <div className="p-3 bg-red-400/5 border border-red-400/30 rounded-sm text-center text-xs text-red-400 font-medium">
            {error}
          </div>
        )}
        <p className="text-center text-[10px] text-slate-500 font-bold uppercase tracking-widest">
          Atlas will process your documents and display findings in real time
        </p>
      </div>
    </div>
  );
};