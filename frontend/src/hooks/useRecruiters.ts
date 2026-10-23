import { listRecruiters } from '../api/recruiters.ts'
import type { Load, Recruiter } from '../api/types.ts'
import { useRequest } from './useRequest.ts'

// Loaded once, as the starting identity; switching recruiters does not reload it.
export function useRecruiters(asRecruiterId: string): Load<Recruiter[]> {
  return useRequest(asRecruiterId, (signal) => listRecruiters(asRecruiterId, signal))
}
