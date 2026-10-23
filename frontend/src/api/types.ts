// Every shape the backend sends or accepts. Mirrors backend/app/domain/schemas.py.

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
  search: string
  status: Status | ''
  page: number
  pageSize: number
}

// The result of a request, as components see it.
export type Load<T> =
  | { state: 'loading' }
  | { state: 'error'; error: unknown }
  | { state: 'ready'; data: T }
