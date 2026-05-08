import React from 'react';
import { LayoutDashboard, FileText, Settings, Activity, Plus, X } from 'lucide-react';

export const Sidebar = ({ view, setView, isSidebarOpen, setIsSidebarOpen }: any) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {isSidebarOpen && (
        <div 
          onClick={() => setIsSidebarOpen(false)}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:relative inset-y-0 left-0 z-50 w-64 bg-[#141424] border-r border-[#3D3D4E] flex flex-col transition-transform duration-300 transform
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="p-6">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-[#E8521A] rounded-sm flex items-center justify-center">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight leading-none">Atlas</h1>
                <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Audit Engine</span>
              </div>
            </div>
            <button className="lg:hidden p-2 text-slate-500" onClick={() => setIsSidebarOpen(false)}>
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="space-y-1">
            {[
              { name: 'Dashboard', icon: LayoutDashboard },
              { name: 'Audit Logs', icon: FileText },
              { name: 'Settings', icon: Settings },
            ].map((item) => (
              <button
                key={item.name}
                onClick={() => { setView(item.name); setIsSidebarOpen(false); }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-sm text-sm font-medium transition-all ${
                  view === item.name 
                    ? 'bg-white/5 text-white border-l-[3px] border-[#E8521A]' 
                    : 'text-slate-500 hover:text-slate-300 hover:bg-white/2'
                }`}
              >
                <item.icon className="w-4 h-4" />
                {item.name}
              </button>
            ))}
          </nav>
        </div>

        <div className="mt-auto p-4">
          <button 
            onClick={() => { setView('New Audit'); setIsSidebarOpen(false); }}
            className={`w-full flex items-center justify-center gap-2 py-3 rounded-sm font-bold text-sm tracking-wide transition-all active:scale-95 uppercase ${
              view === 'New Audit' ? 'bg-white/10 text-white' : 'bg-[#E8521A] hover:bg-[#E8521A]/90 text-white'
            }`}
          >
            <Plus className="w-4 h-4" />
            New Audit
          </button>
        </div>
      </aside>
    </>
  );
};
