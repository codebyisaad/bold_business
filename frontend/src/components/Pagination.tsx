type Props = {
  page: number
  pageSize: number
  total: number
  onPage: (page: number) => void
}

const buttonClass =
  'rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50'

export function Pagination({ page, pageSize, total, onPage }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <nav className="mt-3 flex items-center justify-end gap-3 text-sm text-slate-600" aria-label="Pagination">
      <button type="button" className={buttonClass} onClick={() => onPage(page - 1)} disabled={page <= 1}>
        Previous
      </button>
      <span>Page {page} of {pages} · {total} candidates</span>
      <button type="button" className={buttonClass} onClick={() => onPage(page + 1)} disabled={page >= pages}>
        Next
      </button>
    </nav>
  )
}
