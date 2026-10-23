import { http, recruiterHeaders, toApiError } from './client.ts'
import { ENDPOINTS } from './endpoints.ts'
import type { Recruiter } from './types.ts'

export async function listRecruiters(recruiterId: string, signal?: AbortSignal): Promise<Recruiter[]> {
  try {
    const response = await http.get<Recruiter[]>(ENDPOINTS.recruiters, {
      headers: recruiterHeaders(recruiterId),
      signal,
    })
    return response.data
  } catch (error) {
    throw toApiError(error)
  }
}
