import type { Recruiter } from '../api/types.ts'
import { regionsLabel } from '../lib/format.ts'
import { Field, controlClass } from './Field.tsx'

export const NO_RECRUITER = '' // sends no X-Recruiter-Id header, so the API answers 401

type Props = {
  recruiters: Recruiter[]
  value: string
  onChange: (recruiterId: string) => void
  disabled?: boolean
}

export function RecruiterSelect({ recruiters, value, onChange, disabled }: Props) {
  return (
    <Field label="Recruiter">
      <select className={controlClass} value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
        <option value={NO_RECRUITER}>No recruiter (no header)</option>
        {recruiters.map((r) => (
          <option key={r.recruiter_id} value={r.recruiter_id}>
            {r.full_name} ({regionsLabel(r)})
          </option>
        ))}
      </select>
    </Field>
  )
}
