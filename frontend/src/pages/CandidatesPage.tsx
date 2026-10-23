import { useState } from 'react'
import type { Status } from '../api/types.ts'
import { CandidateTable } from '../components/CandidateTable.tsx'
import { Pagination } from '../components/Pagination.tsx'
import { NO_RECRUITER, RecruiterSelect } from '../components/RecruiterSelect.tsx'
import { SearchInput } from '../components/SearchInput.tsx'
import { StatusMessage } from '../components/StatusMessage.tsx'
import { StatusSelect } from '../components/StatusSelect.tsx'
import { DEFAULT_RECRUITER_ID, PAGE_SIZE, SEARCH_DELAY_MS } from '../config.ts'
import { useCandidates } from '../hooks/useCandidates.ts'
import { useDebouncedValue } from '../hooks/useDebouncedValue.ts'
import { useRecruiters } from '../hooks/useRecruiters.ts'
import { errorMessage, regionsLabel } from '../lib/format.ts'

export function CandidatesPage() {
  const recruiters = useRecruiters(DEFAULT_RECRUITER_ID)
  const [recruiterId, setRecruiterId] = useState(DEFAULT_RECRUITER_ID)
  const [searchInput, setSearchInput] = useState('')
  const search = useDebouncedValue(searchInput.trim(), SEARCH_DELAY_MS)
  const [status, setStatus] = useState<Status | ''>('')
  const [page, setPage] = useState(1)

  // Any change to who is asking or what is asked starts again at page 1.
  const [lastFilters, setLastFilters] = useState({ recruiterId, search, status })
  if (lastFilters.recruiterId !== recruiterId || lastFilters.search !== search || lastFilters.status !== status) {
    setLastFilters({ recruiterId, search, status })
    setPage(1)
  }

  const candidates = useCandidates(
    recruiterId === NO_RECRUITER ? null : recruiterId,
    { search, status, page, pageSize: PAGE_SIZE },
    recruiters.state === 'ready',
  )

  const roster = recruiters.state === 'ready' ? recruiters.data : []
  const selected = roster.find((r) => r.recruiter_id === recruiterId)

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">Candidates</h1>
        <p className="mt-1 text-sm text-slate-500">
          {selected
            ? <>Viewing as <strong className="text-slate-700">{selected.full_name}</strong> · {regionsLabel(selected)}</>
            : 'No recruiter selected'}
        </p>
      </header>

      <section className="mb-4 flex flex-wrap items-end gap-4">
        <RecruiterSelect
          recruiters={roster}
          value={recruiterId}
          onChange={setRecruiterId}
          disabled={recruiters.state !== 'ready'}
        />
        <SearchInput value={searchInput} onChange={setSearchInput} />
        <StatusSelect value={status} onChange={setStatus} />
      </section>

      {recruiters.state === 'loading' && <StatusMessage>Loading recruiters…</StatusMessage>}
      {recruiters.state === 'error' && <StatusMessage tone="error">{errorMessage(recruiters.error)}</StatusMessage>}
      {recruiters.state === 'ready' && candidates.state === 'loading' && <StatusMessage>Loading candidates…</StatusMessage>}
      {candidates.state === 'error' && <StatusMessage tone="error">{errorMessage(candidates.error)}</StatusMessage>}
      {candidates.state === 'ready' && candidates.data.items.length === 0 && (
        <StatusMessage>No candidates match.</StatusMessage>
      )}
      {candidates.state === 'ready' && candidates.data.items.length > 0 && (
        <>
          <CandidateTable candidates={candidates.data.items} />
          <Pagination
            page={candidates.data.page}
            pageSize={candidates.data.page_size}
            total={candidates.data.total}
            onPage={setPage}
          />
        </>
      )}
    </main>
  )
}
