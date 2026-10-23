import { listCandidates } from '../api/candidates.ts'
import type { CandidatePage, CandidateQuery, Load } from '../api/types.ts'
import { useRequest } from './useRequest.ts'

// `enabled` is false until the page is ready to ask (e.g. the recruiter list has loaded).
export function useCandidates(recruiterId: string | null, query: CandidateQuery, enabled: boolean): Load<CandidatePage> {
  const key = enabled ? JSON.stringify([recruiterId, query]) : null
  return useRequest(key, (signal) => listCandidates(recruiterId, query, signal))
}
