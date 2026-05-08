export const SummaryCard = ({ label, val, icon: Icon, color }: any) => {
  return (
    <div className="bg-[#2C2C3E] border border-[#3D3D4E] p-6 rounded-sm flex items-center gap-5">
      <div className="p-3 bg-[#1A1A2E] rounded-sm" style={{ color: color }}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <p className="text-[10px] uppercase font-bold tracking-widest text-slate-500 mb-1">{label}</p>
        <p className="text-3xl font-bold text-white tracking-tighter">{val}</p>
      </div>
    </div>
  );
};