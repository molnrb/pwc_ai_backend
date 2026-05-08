import React, { useState } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { StatusBar } from './components/layout/StatusBar';
import { RegulatoryExtracts } from './components/audit/RegulatoryExtracts';
import { SourceTraceTable } from './components/audit/SourceTraceTable';
import { AgentFeed } from './components/audit/AgentFeed';
import { Dashboard } from './components/dashboard/Dashboard';
import { NewAudit } from './components/new-audit/NewAudit';

export default function App() {
  const [view, setView] = useState<'Dashboard' | 'Audit Logs' | 'Settings' | 'New Audit'>('Audit Logs');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#1A1A2E] text-slate-300 font-sans selection:bg-[#E8521A] selection:text-white overflow-hidden">
      <Sidebar 
        view={view} 
        setView={setView} 
        isSidebarOpen={isSidebarOpen} 
        setIsSidebarOpen={setIsSidebarOpen} 
      />

      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <Header 
          view={view} 
          setIsSidebarOpen={setIsSidebarOpen} 
        />

        <div className="flex-1 flex overflow-hidden">
          {view === 'Dashboard' && <Dashboard />}
          
          {view === 'Settings' && (
            <div className="flex-1 flex flex-col items-center justify-center p-8 bg-[#1A1A2E]">
              <div className="text-center space-y-2">
                <p className="text-lg font-bold text-white uppercase tracking-tight">No configuration required</p>
                <p className="text-sm text-slate-400">Atlas runs automatically with optimal defaults</p>
              </div>
            </div>
          )}

          {view === 'New Audit' && (
            <NewAudit onComplete={() => setView('Audit Logs')} />
          )}

          {view === 'Audit Logs' && (
            <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
              <RegulatoryExtracts />
              <div className="flex-1 flex flex-col h-full overflow-hidden min-w-0">
                <SourceTraceTable />
                <AgentFeed />
              </div>
            </div>
          )}
        </div>

        <StatusBar />
      </main>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
          height: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #3D3D4E;
          border-radius: 2px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #4A4A5E;
        }
      `}</style>
    </div>
  );
}
