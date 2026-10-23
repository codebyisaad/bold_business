import axios, { isAxiosError } from 'axios'
import { API_URL } from '../config.ts'

export const http = axios.create({ baseURL: API_URL, timeout: 15_000 })

// Every scoped request names its caller. No id means no header, and the API answers 401.
export function recruiterHeaders(recruiterId: string | null): Record<string, string> {
  return recruiterId ? { 'X-Recruiter-Id': recruiterId } : {}
}

export class ApiError extends Error {
  status: number | null // null when the API could not be reached

  constructor(status: number | null, message: string) {
    super(message)
    this.status = status
  }
}

// Turn an axios failure into an ApiError carrying the HTTP status and the API's `detail`.
export function toApiError(error: unknown): ApiError {
  if (isAxiosError(error) && error.response) {
    const detail = (error.response.data as { detail?: unknown } | undefined)?.detail
    return new ApiError(error.response.status, typeof detail === 'string' ? detail : error.message)
  }
  return new ApiError(null, 'Could not reach the API. Is the backend running?')
}
