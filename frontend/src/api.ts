// Everything the page knows about the backend: types and the two requests.
// The server does all filtering, scoping and paging; the browser only displays.

const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const STATUSES = ['active', 'screening', 'interviewing', 'withdrawn', 'hired', 'rejected'] as const
export type Status = (typeof STATUSES)[number]

export type Recruiter = {
  recruiter_id: string
  full_name: string
  role: 'admin' | 'recruiter'
  assigned_regions: string[] // ["*"] for an admin
}

export type Candidate = {
  candidate_id: string
  first_name: string
  last_name: string
  email: string
  region_code: string
  status: Status
  salary_expectation: string | null // decimal sent as a string, e.g. "95000.00"
  applied_date: string | null // ISO YYYY-MM-DD
}

export type CandidatePage = {
  items: Candidate[]
  total: number
  page: number
  page_size: number
}

export type CandidateQuery = {
  recruiterId: string | null
  search: string
  status: Status | ''
  page: number
  pageSize: number
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function getJson<T>(path: string, recruiterId: string | null, signal?: AbortSignal): Promise<T> {
  const headers: Record<string, string> = {}
  if (recruiterId) headers['X-Recruiter-Id'] = recruiterId
  const response = await fetch(`${API_URL}${path}`, { headers, signal })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : response.statusText
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
}

export function listRecruiters(signal?: AbortSignal): Promise<Recruiter[]> {
  return getJson('/api/v1/recruiters', null, signal)
}

export function listCandidates(query: CandidateQuery, signal?: AbortSignal): Promise<CandidatePage> {
  const params = new URLSearchParams({ page: String(query.page), page_size: String(query.pageSize) })
  if (query.search) params.set('search', query.search)
  if (query.status) params.set('status', query.status)
  return getJson(`/api/v1/candidates?${params}`, query.recruiterId, signal)
}
