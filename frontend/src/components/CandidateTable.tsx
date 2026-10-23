import type { Candidate } from '../api/types.ts'
import { formatDate, formatSalary } from '../lib/format.ts'

const COLUMNS = [
  { label: 'Name', numeric: false },
  { label: 'Email', numeric: false },
  { label: 'Region', numeric: false },
  { label: 'Role', numeric: false },
  { label: 'Status', numeric: false },
  { label: 'Salary', numeric: true },
  { label: 'Applied', numeric: false },
]

// Displays the rows exactly in the order the API returned them.
export function CandidateTable({ candidates }: { candidates: Candidate[] }) {
  return (
    <div className="overflow-x-auto rounded-md border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {COLUMNS.map((column) => (
              <th
                key={column.label}
                scope="col"
                className={`px-4 py-2 font-semibold text-slate-700 ${column.numeric ? 'text-right' : 'text-left'}`}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {candidates.map((c) => (
            <tr key={c.candidate_id} className="hover:bg-slate-50">
              <td className="px-4 py-2 text-slate-900">{c.first_name} {c.last_name}</td>
              <td className="px-4 py-2 text-slate-600">{c.email}</td>
              <td className="px-4 py-2 text-slate-600">{c.region_code}</td>
              <td className="px-4 py-2 text-slate-600">{c.desired_role ?? '—'}</td>
              <td className="px-4 py-2 text-slate-600">{c.status}</td>
              <td className="px-4 py-2 text-right tabular-nums text-slate-600">{formatSalary(c.salary_expectation)}</td>
              <td className="px-4 py-2 tabular-nums text-slate-600">{formatDate(c.applied_date)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
