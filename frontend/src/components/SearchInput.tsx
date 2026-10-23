import { Field, controlClass } from './Field.tsx'

type Props = {
  value: string
  onChange: (value: string) => void
}

export function SearchInput({ value, onChange }: Props) {
  return (
    <Field label="Search">
      <input
        type="search"
        className={controlClass}
        value={value}
        placeholder="Name or email"
        onChange={(e) => onChange(e.target.value)}
      />
    </Field>
  )
}
