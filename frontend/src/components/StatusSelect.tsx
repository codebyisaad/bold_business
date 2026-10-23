import { STATUSES, type Status } from '../api/types.ts'
import { Field, controlClass } from './Field.tsx'

type Props = {
  value: Status | ''
  onChange: (value: Status | '') => void
}

export function StatusSelect({ value, onChange }: Props) {
  return (
    <Field label="Status">
      <select className={controlClass} value={value} onChange={(e) => onChange(e.target.value as Status | '')}>
        <option value="">All statuses</option>
        {STATUSES.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>
    </Field>
  )
}
