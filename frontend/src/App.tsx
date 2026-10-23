import { useEffect, useState } from 'react'
import {
  ApiError,
  STATUSES,
  listCandidates,
  listRecruiters,
  type CandidatePage,
  type Recruiter,
  type Status,
} from './api.ts'

const PAGE_SIZE = 25
const SEARCH_DELAY_MS = 300
const NO_RECRUITER = '' // sends no X-Recruiter-Id header, so the API answers 401

type Load<T> =
  | { state: 'loading' }
  | { state: 'error'; error: unknown }
  | { state: 'ready'; data: T }

const salaryFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })

function regionsLabel(recruiter: Recruiter): string {
  return recruiter.role === 'admin' ? 'All regions' : recruiter.assigned_regions.join(', ')
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return `401 Unauthorized: ${error.message}`
    if (error.status === 403) return `403 Forbidden: ${error.message}`
    return `Error ${error.status}: ${error.message}`
  }
  return 'Could not reach the API. Is the backend running?'
}

export default function App() {
  const [recruiters, setRecruiters] = useState<Load<Recruiter[]>>({ state: 'loading' })
  const [recruiterId, setRecruiterId] = useState(NO_RECRUITER)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<Status | ''>('')
  const [page, setPage] = useState(1)
  // The last response and the query it answered. It is "loading" whenever the current
  // query differs, so a stale response is never shown for a new query.
  const [result, setResult] = useState<{ key: string; load: Load<CandidatePage> } | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    listRecruiters(controller.signal)
      .then((data) => {
        setRecruiters({ state: 'ready', data })
        if (data.length > 0) setRecruiterId(data[0].recruiter_id)
      })
      .catch((error) => {
        if (!controller.signal.aborted) setRecruiters({ state: 'error', error })
      })
    return () => controller.abort()
  }, [])

  // Wait for typing to pause before asking the server; a new search starts at page 1.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [searchInput])

  const queryKey = JSON.stringify([recruiterId, search, status, page])
  const candidates: Load<CandidatePage> =
    result?.key === queryKey ? result.load : { state: 'loading' }

  useEffect(() => {
    if (recruiters.state !== 'ready') return
    const controller = new AbortController()
    listCandidates({ recruiterId: recruiterId || null, search, status, page, pageSize: PAGE_SIZE }, controller.signal)
      .then((data) => setResult({ key: queryKey, load: { state: 'ready', data } }))
      .catch((error) => {
        if (!controller.signal.aborted) setResult({ key: queryKey, load: { state: 'error', error } })
      })
    return () => controller.abort()
  }, [recruiters.state, queryKey, recruiterId, search, status, page])

  function changeRecruiter(id: string) {
    setRecruiterId(id)
    setPage(1)
  }

  function changeStatus(value: Status | '') {
    setStatus(value)
    setPage(1)
  }

  const selected = recruiters.state === 'ready'
    ? recruiters.data.find((r) => r.recruiter_id === recruiterId)
    : undefined

  return (
    <main>
      <h1>Candidates</h1>

      <section className="controls">
        <label>
          Recruiter
          <select
            value={recruiterId}
            onChange={(e) => changeRecruiter(e.target.value)}
            disabled={recruiters.state !== 'ready'}
          >
            <option value={NO_RECRUITER}>No recruiter (no header)</option>
            {recruiters.state === 'ready' &&
              recruiters.data.map((r) => (
                <option key={r.recruiter_id} value={r.recruiter_id}>
                  {r.full_name} ({regionsLabel(r)})
                </option>
              ))}
          </select>
        </label>

        <label>
          Search
          <input
            type="search"
            value={searchInput}
            placeholder="Name or email"
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </label>

        <label>
          Status
          <select value={status} onChange={(e) => changeStatus(e.target.value as Status | '')}>
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
      </section>

      <p className="scope">
        {selected
          ? <>Viewing as <strong>{selected.full_name}</strong> · {regionsLabel(selected)}</>
          : 'No recruiter selected'}
      </p>

      {recruiters.state === 'loading' && <p className="message">Loading recruiters…</p>}
      {recruiters.state === 'error' && <p className="message error">{errorMessage(recruiters.error)}</p>}
      {recruiters.state === 'ready' && <Results load={candidates} page={page} onPage={setPage} />}
    </main>
  )
}

function Results({ load, page, onPage }: { load: Load<CandidatePage>; page: number; onPage: (page: number) => void }) {
  if (load.state === 'loading') return <p className="message">Loading candidates…</p>
  if (load.state === 'error') return <p className="message error" role="alert">{errorMessage(load.error)}</p>

  const { items, total, page_size } = load.data
  if (items.length === 0) return <p className="message">No candidates match.</p>

  const pages = Math.max(1, Math.ceil(total / page_size))
  return (
    <>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Region</th>
            <th>Status</th>
            <th className="number">Salary</th>
            <th>Applied</th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr key={c.candidate_id}>
              <td>{c.first_name} {c.last_name}</td>
              <td>{c.email}</td>
              <td>{c.region_code}</td>
              <td>{c.status}</td>
              <td className="number">
                {c.salary_expectation === null ? '—' : salaryFormat.format(Number(c.salary_expectation))}
              </td>
              <td>{c.applied_date ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <nav className="pagination">
        <button onClick={() => onPage(page - 1)} disabled={page <= 1}>Previous</button>
        <span>Page {page} of {pages} · {total} candidates</span>
        <button onClick={() => onPage(page + 1)} disabled={page >= pages}>Next</button>
      </nav>
    </>
  )
}
