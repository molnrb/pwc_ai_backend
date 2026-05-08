/**
 * Atlas API service layer — connects React frontend to FastAPI backend.
 * All endpoints are proxied through Vite (see vite.config.ts).
 */

// ── Types ────────────────────────────────────────────────────────────────

export interface Evidence {
  page: number;
  flag: 'green' | 'yellow' | 'red' | 'grey';
  claim_text: string;
  data_point: string;
  claimed_value: number | null;
  source_value: number | null;
  unit: string;
  source_file: string | null;
  source_sheet: string | null;
  source_cell: string | null;
  deviation_pct: number | null;
  explanation: string;
  paragraph_idx?: number;
  review_required?: boolean;
}

export interface Summary {
  green_count: number;
  yellow_count: number;
  red_count: number;
  grey_count: number;
  total: number;
  material_red_count?: number;
  review_required?: boolean;
  red_flags: { data_point: string; claimed: number; actual: number; deviation_pct: number; explanation: string }[];
  verdict: string;
  materiality_note: string;
}

export interface HealthStatus {
  status: string;
  mode: 'mock' | 'live';
  input_files: { filename: string; size_kb: number }[];
  input_file_count: number;
  ready: boolean;
}

export type SSEEventType =
  | 'status'
  | 'phase'
  | 'file_found'
  | 'todo'
  | 'agent_start'
  | 'agent_progress'
  | 'agent_done'
  | 'finding'
  | 'parse_start'
  | 'parse_done'
  | 'trace_start'
  | 'trace_item'
  | 'trace_done'
  | 'report_generating'
  | 'heartbeat'
  | 'complete'
  | 'error';

export interface SSEEvent {
  type: SSEEventType;
  data: Record<string, unknown>;
}

export interface UploadResult {
  status: string;
  files: { filename: string; size_kb: number }[];
  input_file_count: number;
  ready: boolean;
}

export interface AuditMetadata {
  document: string;
  standard: string;
  framework: string;
  pipeline: string;
  parser_mode: string;
  started_at: string;
  completed_at: string;
  total_pages: number;
  total_claims_found: number;
  total_findings: number;
}

export interface DocumentInventoryItem {
  filename: string;
  type: string;
  size_kb: number;
  role: string;
}

export interface AuditReport {
  audit_metadata: AuditMetadata;
  document_inventory: DocumentInventoryItem[];
  findings: Evidence[];
  summary: Summary;
  red_flags: Summary['red_flags'];
  review_required: boolean;
}

// ── REST endpoints ──────────────────────────────────────────────────────

export async function fetchHealth(): Promise<HealthStatus> {
  const resp = await fetch('/health');
  if (!resp.ok) throw new Error(`Health check failed: ${resp.status}`);
  return resp.json();
}

export async function fetchEvidence(): Promise<{ evidence: Evidence[]; summary: Summary }> {
  const resp = await fetch('/evidence');
  if (!resp.ok) throw new Error(`Evidence fetch failed: ${resp.status}`);
  return resp.json();
}

export async function triggerAudit(): Promise<{ mode: string; evidence: Evidence[]; summary: Summary; error?: string }> {
  const resp = await fetch('/audit', { method: 'POST' });
  if (!resp.ok) throw new Error(`Audit failed: ${resp.status}`);
  return resp.json();
}

export async function resetWorkspace(): Promise<Record<string, unknown>> {
  const resp = await fetch('/reset', { method: 'POST' });
  if (!resp.ok) throw new Error(`Reset failed: ${resp.status}`);
  return resp.json();
}

export async function uploadInputFiles(files: File[]): Promise<UploadResult> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file, file.name);
  });

  const resp = await fetch('/upload', {
    method: 'POST',
    body: formData,
  });

  if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`);
  return resp.json();
}

export async function fetchReport(): Promise<AuditReport> {
  const resp = await fetch('/report');
  if (!resp.ok) {
    let errorMessage = `Report fetch failed: ${resp.status}`;
    try {
      const payload = await resp.json() as { error?: string };
      if (typeof payload.error === 'string' && payload.error) {
        errorMessage = payload.error;
      }
    } catch {
      // Fall back to the HTTP status when the error payload is unavailable.
    }
    throw new Error(errorMessage);
  }
  return resp.json();
}

export async function downloadReportPackage(): Promise<AuditReport> {
  const report = await fetchReport();
  const fileDate = new Date().toISOString().slice(0, 10);
  const downloadName = `atlas-evidence-package-${fileDate}.json`;
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = downloadName;
  anchor.click();
  URL.revokeObjectURL(url);
  return report;
}

// ── SSE stream ──────────────────────────────────────────────────────────

export type SSECallback = (event: SSEEvent) => void;

export function connectSSE(onEvent: SSECallback, onError?: (err: Event) => void): EventSource {
  const es = new EventSource('/stream');

  const eventTypes: SSEEventType[] = [
    'status', 'phase', 'file_found', 'todo',
    'agent_start', 'agent_progress', 'agent_done',
    'finding', 'parse_start', 'parse_done',
    'trace_start', 'trace_item', 'trace_done',
    'report_generating', 'heartbeat',
    'complete', 'error',
  ];

  eventTypes.forEach((type) => {
    es.addEventListener(type, (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        onEvent({ type, data });
      } catch {
        onEvent({ type, data: { raw: event.data } });
      }
    });
  });

  es.onmessage = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      onEvent({ type: 'status', data });
    } catch {
      // ignore
    }
  };

  if (onError) es.onerror = onError;
  return es;
}