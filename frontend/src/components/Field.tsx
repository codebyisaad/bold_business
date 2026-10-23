type Props = {
  label: string
  children: React.ReactNode
}

// A labelled control in the toolbar.
export function Field({ label, children }: Props) {
  return (
    <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
      {label}
      {children}
    </label>
  )
}

export const controlClass =
  'min-w-52 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-normal normal-case tracking-normal text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200 disabled:bg-slate-100'
