import { type Evidence } from '../services/api';

export function getEvidenceKey(item: Evidence, index: number): string {
  if (item.claim_id) return item.claim_id;

  return [
    item.data_point,
    item.page ?? 'no-page',
    item.paragraph_idx ?? 'no-paragraph',
    item.source_file ?? 'no-file',
    item.source_cell ?? 'no-cell',
    item.claimed_value ?? 'no-claimed-value',
    item.source_value ?? 'no-source-value',
    index,
  ].join('-');
}