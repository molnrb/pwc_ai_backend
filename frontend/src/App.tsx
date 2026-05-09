import { useState } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { RegulatoryExtracts } from './components/audit/RegulatoryExtracts';
import { AgentFeed } from './components/audit/AgentFeed';
import { Dashboard } from './components/dashboard/Dashboard';
import { NewAudit } from './components/new-audit/NewAudit';
import { useAtlasData } from './hooks/useAtlasData';
import { resetWorkspace, uploadInputFiles } from './services/api';

export default function App() {
  const [view, setView] = useState<'Audit Logs' | 'Dashboard' | 'New Audit'>('Audit Logs');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { evidence, summary, health, feed, loading, startStream, addFeedEntry, clearRunState } = useAtlasData();

  const prepareFreshAudit = async () => {
    setView('Audit Logs');
    clearRunState();
    addFeedEntry('SYSTEM', 'Preparing fresh audit run...');

    try {
      await resetWorkspace();
      addFeedEntry('SYSTEM', 'Previous audit outputs cleared.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown reset error';
      addFeedEntry('ERROR', `Workspace reset failed: ${message}`);
    }
  };

  const launchAuditStream = async () => {
    await prepareFreshAudit();
    addFeedEntry('SYSTEM', 'Starting live audit stream...');
    startStream();
  };

  const handleAuditComplete = async (files: File[] = []) => {
    await prepareFreshAudit();

    if (files.length > 0) {
      addFeedEntry('SYSTEM', `Uploading ${files.length} file(s) to backend workspace...`);
      const upload = await uploadInputFiles(files);
      addFeedEntry('SYSTEM', `Upload complete. ${upload.input_file_count} file(s) ready.`);
    }

    addFeedEntry('SYSTEM', 'Starting live audit stream...');
    startStream();
  };

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
          evidenceCount={evidence.length}
          redCount={summary?.red_count ?? 0}
          loading={loading}
          onLaunchAudit={() => { void launchAuditStream(); }}
          setIsSidebarOpen={setIsSidebarOpen}
        />

        <div className="flex-1 flex overflow-hidden">
          {view === 'Dashboard' && <Dashboard evidence={evidence} summary={summary} health={health} feed={feed} />}

          {view === 'New Audit' && (
            <NewAudit onComplete={(files) => { void handleAuditComplete(files); }} />
          )}

          {view === 'Audit Logs' && (
            <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
              <RegulatoryExtracts evidence={evidence} />
              <div className="flex-1 flex flex-col h-full overflow-hidden min-w-0">
                <AgentFeed feed={feed} fullHeight />
              </div>
            </div>
          )}
        </div>
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