export type DataStatus = 'fresh' | 'stale' | 'unavailable';

export interface ResponseMeta {
  data_status: DataStatus;
  fetched_at?: string | null;
}

export const REFRESH_HEADER = 'X-AtmosMind-Refresh';

export function hasResponseMeta(meta: ResponseMeta | null | undefined): boolean {
  return meta != null && typeof meta.data_status === 'string';
}
