import { ESRS_COLORS } from '../constants/esrs';

export const EXTRACTS = [
  { 
    id: 'E1-001-X', 
    badge: 'ERROR', 
    title: 'Scope 2 market-based emissions — 4,200 tCO2e', 
    filename: 'emissions_reporting_v3.xlsx' 
  },
  { 
    id: 'E1-002-X', 
    badge: 'ERROR', 
    title: 'Scope 1+2 total — 6,050 tCO2e', 
    filename: 'audit_sum_2024.csv' 
  },
  { 
    id: 'E1-003-Y', 
    badge: 'OK', 
    title: 'Scope 1 GHG emissions — 1,850 tCO2e', 
    filename: 'sustainability_report_final.pdf' 
  },
  { 
    id: 'E1-004-Z', 
    badge: 'OK', 
    title: 'Renewable energy share — 67%', 
    filename: 'energy_mix_assessment.docx' 
  },
  { 
    id: 'E1-005-A', 
    badge: 'REVIEW', 
    title: 'Transition plan 2030 target', 
    filename: 'strategy_2030_draft.pdf' 
  },
  { 
    id: 'E1-006-B', 
    badge: 'OK', 
    title: 'Scope 3 category 1 — 18,400 tCO2e', 
    filename: 'supply_chain_impact.xlsx' 
  },
];

export const TRACE_DETAILS = [
  { fileName: 'EMISSIONS_DATA.XLSX', sheet: 'Market-Based', ref: 'B12', value: '4,020.00', deviation: '4.48%' },
  { fileName: 'ANNUAL_EMISSIONS.CSV', sheet: 'Total', ref: 'E42', value: '5,870.00', deviation: '3.07%' },
  { fileName: 'SCOPE_1_FINAL.PDF', sheet: 'p.54', ref: 'T_01', value: '1,850.00', deviation: '0.00%' },
  { fileName: 'ENERGY_PORTFOLIO.XLSX', sheet: 'Renewables', ref: 'A5', value: '67%', deviation: '0.00%' },
  { fileName: 'STRATEGY_DEPT.PDF', sheet: 'Targets', ref: 'Pg12', value: 'N/A', deviation: 'REVIEWED' },
];

export const FEED = [
  { agent: 'VALIDATOR', timestamp: '14:48:02', message: 'Calculated value mismatch in Scope 2. Reported: 4,200 vs Evidence: 4,020.' },
  { agent: 'TRACER', timestamp: '14:47:58', message: 'Source detected: emissions_reporting_v3.xlsx. Mapping vector B12.' },
  { agent: 'PARSER', timestamp: '14:47:45', message: 'Chunking E1 Climate chapter — Identified 24 distinct emissions indicators.' },
  { agent: 'ORCHESTRATOR', timestamp: '14:47:42', message: 'Initiating deep trace for Scope 1+2 totals inconsistency.' },
  { agent: 'ORCHESTRATOR', timestamp: '14:47:30', message: 'System ready. ESRS E1 Climate scope locked.' },
  { agent: 'SYSTEM', timestamp: '14:47:20', message: 'Audit session active. Security handshake successful.' },
];
