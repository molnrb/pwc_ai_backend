import { motion, AnimatePresence } from 'motion/react';
import { AGENT_COLORS } from '../../constants/esrs';

interface FeedEntry {
  agent: string;
  timestamp: string;
  message: string;
}

interface Props {
  feed: FeedEntry[];
  fullHeight?: boolean;
}

const getAgentColor = (agent: string) => (AGENT_COLORS as any)[agent] || '#888888';

export const AgentFeed = ({ feed, fullHeight }: Props) => {
  const seenEntries = new Map<string, number>();

  return (
    <div className={`${fullHeight ? 'flex-1 min-h-0' : 'h-[280px] min-h-[200px]'} border-t-2 border-[#3D3D4E] flex flex-col bg-[#0f0f1b]`}>
      <div className="p-3 border-b border-[#3D3D4E] flex items-center gap-2 px-4 shadow-lg shadow-black/20 h-10 shrink-0">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Live Agent Feed</span>
        <span className="ml-auto text-[9px] font-mono text-slate-600">{feed.length} entries</span>
      </div>

      <div className="flex-1 min-h-0 p-4 font-mono text-[11px] overflow-y-auto overscroll-contain custom-scrollbar bg-black/20 leading-[28px]">
        <AnimatePresence mode="popLayout">
          {feed.map((entry) => {
            const isRedFlag = entry.message.toLowerCase().includes('red flag') || entry.message.toLowerCase().includes('mismatch') || entry.message.toLowerCase().includes('discrepancy');
            const baseKey = `${entry.timestamp}-${entry.agent}-${entry.message}`;
            const occurrence = seenEntries.get(baseKey) ?? 0;
            seenEntries.set(baseKey, occurrence + 1);

            return (
              <motion.div
                key={`${baseKey}-${occurrence}`}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                className={`flex gap-3 group ${isRedFlag ? 'bg-red-400/5 -mx-4 px-4 border-l-2 border-red-400/40' : ''}`}
              >
                <span style={{ color: getAgentColor(entry.agent) }}>[{entry.agent}]</span>
                <span className="text-slate-600 whitespace-nowrap">· {entry.timestamp} ·</span>
                <span className={`${isRedFlag ? 'text-red-300 font-bold' : 'text-slate-300'} group-hover:text-white transition-colors`}>{entry.message}</span>
              </motion.div>
            );
          })}
        </AnimatePresence>
        {feed.length === 0 && (
          <div className="flex items-center justify-center h-full text-slate-600 text-[10px] uppercase tracking-widest">
            Waiting for agent activity...
          </div>
        )}
      </div>
    </div>
  );
};