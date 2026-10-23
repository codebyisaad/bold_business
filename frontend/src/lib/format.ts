import { ApiError } from '../api/client.ts'
import type { Recruiter } from '../api/types.ts'

const salaryFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })

// No currency symbol: the source data never says which currency it is.
export function formatSalary(value: string | null): string {
  return value === null ? '—' : salaryFormat.format(Number(value))
}

// Shown exactly as the API sends it (ISO). Never parsed into a Date, so no time-zone shift.
export function formatDate(value: string | null): string {
  return value ?? '—'
}

export function regionsLabel(recruiter: Recruiter): string {
  return recruiter.role === 'admin' ? 'All regions' : recruiter.assigned_regions.join(', ')
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return `401 Unauthorized: ${error.message}`
    if (error.status === 403) return `403 Forbidden: ${error.message}`
    if (error.status !== null) return `Error ${error.status}: ${error.message}`
    return error.message
  }
  return 'Something went wrong.'
}
