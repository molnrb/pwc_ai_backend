import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchEvidence, fetchHealth, fetchReport, triggerAudit, connectSSE, type Evidence, type Summary, type HealthStatus, type SSEEvent } from '../services/api';

interface FeedEntry {
  agent: string;
  timestamp: string;
  message: string;
}

function formatAgentProgress(data: Record<string, unknown>): string {
  if (typeof data.message === 'string' && data.message) return data.message;

  const counters = ['green', 'yellow', 'red', 'grey']
    .filter((key) => typeof data[key] === 'number')
    .map((key) => `${data[key] as number} ${key}`);
  if (counters.length > 0) return counters.join(' • ');

  if (typeof data.data_point === 'string') {
    const parts = [data.data_point];
    if (typeof data.claimed_value === 'number' || typeof data.claimed_value === 'string') {
      parts.push(String(data.claimed_value));
    }
    if (typeof data.unit === 'string' && data.unit) parts.push(data.unit);
    if (typeof data.progress === 'string' && data.progress) parts.push(`(${data.progress})`);
    return parts.join(' ');
  }

  if (typeof data.progress === 'string') return data.progress;
  return 'In progress';
}

function formatAgentDone(data: Record<string, unknown>): string {
  if (typeof data.message === 'string' && data.message) return data.message;
  if (typeof data.claims_found === 'number') return `${data.claims_found} claims extracted`;
  if (typeof data.findings === 'number') return `${data.findings} findings completed`;
  return 'Done';
}

export function useAtlasData() {
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [feed, setFeed] = useState<FeedEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const addFeedEntry = useCallback((agent: string, message: string) => {
    const now = new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    setFeed(prev => [{ agent, timestamp: now, message }, ...prev]);
  }, []);

  const clearRunState = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setEvidence([]);
    setSummary(null);
    setFeed([]);
    setLoading(false);
  }, []);

  const syncEvidence = useCallback(async () => {
    const ev = await fetchEvidence();
    setEvidence(ev.evidence);
    setSummary(ev.summary);
    return ev;
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [ev, h] = await Promise.all([syncEvidence(), fetchHealth()]);
      setHealth(h);
      addFeedEntry('SYSTEM', `Loaded ${ev.evidence.length} evidence items. ${ev.summary.red_count} red flags.`);
    } catch (err: any) {
      addFeedEntry('ERROR', `Data load failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [addFeedEntry, syncEvidence]);

  const runAudit = useCallback(async () => {
    setLoading(true);
    addFeedEntry('SYSTEM', 'Triggering backend audit...');

    try {
      const result = await triggerAudit();
      setEvidence(result.evidence);
      setSummary(result.summary);

      try {
        const currentHealth = await fetchHealth();
        setHealth(currentHealth);
      } catch {
        // Health refresh is best-effort after a successful audit.
      }

      addFeedEntry('SYSTEM', `${result.mode.toUpperCase()} audit complete. ${result.summary.red_count} red flags.`);
      return result;
    } catch (err: any) {
      addFeedEntry('ERROR', `Audit run failed: ${err.message}`);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [addFeedEntry]);

  const startStream = useCallback(() => {
    if (esRef.current) return;
    setLoading(true);
    addFeedEntry('SYSTEM', 'Connecting to live SSE stream...');

    const onSSE = (event: SSEEvent) => {
      switch (event.type) {
        case 'status':
          addFeedEntry('SYSTEM', String((event.data as any).message || ''));
          break;
        case 'phase':
          addFeedEntry('ORCHESTRATOR', String((event.data as any).message || ''));
          break;
        case 'file_found':
          addFeedEntry('ORCHESTRATOR', `Input detected: ${String((event.data as any).filename || 'unknown file')}`);
          break;
        case 'todo':
          addFeedEntry('ORCHESTRATOR', `TODO: ${((event.data as any).items || []).length} tasks planned`);
          break;
        case 'agent_start':
          addFeedEntry('ORCHESTRATOR', `${(event.data as any).agent}: ${(event.data as any).task}`);
          break;
        case 'agent_progress':
          addFeedEntry((event.data as any).agent || 'AGENT', formatAgentProgress(event.data));
          break;
        case 'agent_done':
          addFeedEntry((event.data as any).agent || 'AGENT', formatAgentDone(event.data));
          break;
        case 'finding':
          addFeedEntry((event.data as any).agent || 'AGENT', String((event.data as any).message || 'Finding recorded'));
          break;
        case 'parse_start':
          addFeedEntry('ORCHESTRATOR', `Parsing ${(event.data as any).file || 'input PDF'}...`);
          break;
        case 'parse_done':
          addFeedEntry('ORCHESTRATOR', `Parsed ${(event.data as any).claims_found || 0} claims.`);
          break;
        case 'trace_start':
          addFeedEntry('ORCHESTRATOR', `Tracing ${(event.data as any).claims_to_trace || 0} claims against source files...`);
          break;
        case 'trace_item':
          addFeedEntry('TRACER', `${(event.data as any).progress || ''} ${(event.data as any).data_point || 'claim'}`.trim());
          break;
        case 'trace_done':
          addFeedEntry('ORCHESTRATOR', `Validation complete for ${(event.data as any).findings || 0} findings.`);
          break;
        case 'report_generating':
          addFeedEntry('ORCHESTRATOR', 'Generating final report...');
          break;
        case 'heartbeat':
          break;
        case 'complete':
          {
            const ev = (event.data as any).evidence as Evidence[] | undefined;
            const sum = (event.data as any).summary as Summary | undefined;
            if (ev) setEvidence(ev);
            if (sum) setSummary(sum);
            if (!ev) {
              void syncEvidence().catch((err: any) => {
                addFeedEntry('ERROR', `Result refresh failed: ${err.message}`);
              });
            }
            addFeedEntry('SYSTEM', `Audit complete. ${sum?.total || ev?.length || 0} findings. ${sum?.red_count || 0} red flags.`);
            void fetchReport()
              .then((report) => {
                addFeedEntry('SYSTEM', `Pipeline: ${report.audit_metadata.pipeline} (${report.audit_metadata.parser_mode})`);
              })
              .catch(() => {
                // Report metadata is best-effort enrichment for the live feed.
              });
            esRef.current?.close();
            esRef.current = null;
            setLoading(false);
          }
          break;
        case 'error':
          addFeedEntry('ERROR', String((event.data as any).message || 'Stream error'));
          setLoading(false);
          break;
        default:
          addFeedEntry('SSE', JSON.stringify(event.data));
      }
    };

    const onErr = () => {
      addFeedEntry('ERROR', 'SSE connection error — retrying...');
      esRef.current?.close();
      esRef.current = null;
      setLoading(false);
    };

    esRef.current = connectSSE(onSSE, onErr);
  }, [addFeedEntry, syncEvidence]);

  const stopStream = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setLoading(false);
    addFeedEntry('SYSTEM', 'Stream disconnected.');
  }, [addFeedEntry]);

  useEffect(() => {
    loadData();
    return () => { esRef.current?.close(); };
  }, [loadData]);

  return { evidence, summary, health, feed, loading, loadData, runAudit, startStream, stopStream, addFeedEntry, clearRunState };
}