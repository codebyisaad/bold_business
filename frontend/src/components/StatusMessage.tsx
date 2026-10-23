type Props = {
  tone?: 'info' | 'error'
  children: React.ReactNode
}

// The loading, empty and error states share one look.
export function StatusMessage({ tone = 'info', children }: Props) {
  const styles = tone === 'error'
    ? 'border-red-300 bg-red-50 text-red-800'
    : 'border-slate-200 bg-slate-50 text-slate-600'
  return (
    <p role={tone === 'error' ? 'alert' : 'status'} className={`rounded-md border p-4 text-sm ${styles}`}>
      {children}
    </p>
  )
}
