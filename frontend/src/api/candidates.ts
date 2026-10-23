import { http, recruiterHeaders, toApiError } from './client.ts'
import { ENDPOINTS } from './endpoints.ts'
import type { CandidatePage, CandidateQuery } from './types.ts'

// The server filters, scopes and pages; the browser only displays what comes back.
export async function listCandidates(
  recruiterId: string | null,
  query: CandidateQuery,
  signal?: AbortSignal,
): Promise<CandidatePage> {
  try {
    const response = await http.get<CandidatePage>(ENDPOINTS.candidates, {
      headers: recruiterHeaders(recruiterId),
      params: {
        page: query.page,
        page_size: query.pageSize,
        search: query.search || undefined,
        status: query.status || undefined,
      },
      signal,
    })
    return response.data
  } catch (error) {
    throw toApiError(error)
  }
}
