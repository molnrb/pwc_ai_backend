import { ChevronDown } from 'lucide-react';

export const StepConfigure = () => {
  return (
    <div className="space-y-8">
      <h2 className="text-xl font-bold text-white uppercase tracking-tight">Step 2 of 3: Configure Audit</h2>

      <div className="space-y-6">
        <div className="space-y-2">
          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">Project Name</label>
          <input type="text" defaultValue="E1 Climate Resilience Audit" className="w-full bg-[#1A1A2E] border border-[#3D3D4E] p-4 rounded-sm text-white focus:outline-none focus:border-[#E8521A] transition-colors" />
        </div>

        <div className="space-y-2">
          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">Reporting Year</label>
          <div className="relative">
            <select defaultValue="2026" className="w-full appearance-none bg-[#1A1A2E] border border-[#3D3D4E] p-4 rounded-sm text-sm text-white focus:outline-none focus:border-[#E8521A] transition-colors cursor-pointer pr-10">
              <option>2026</option>
              <option>2025</option>
              <option>2024</option>
              <option>2023</option>
            </select>
            <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          </div>
        </div>

        <div className="space-y-4">
          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">ESRS Scope</label>
          <div className="space-y-3">
            <label className="flex items-center gap-3 p-4 bg-[#2C2C3E] border border-[#3D3D4E] rounded-sm">
              <input type="checkbox" className="w-4 h-4 accent-[#E8521A]" defaultChecked disabled />
              <span className="text-sm text-white font-bold">E1 — Climate Change</span>
            </label>
            <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest px-1 italic">
              Additional ESRS modules coming in future releases
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};