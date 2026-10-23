import { useEffect, useState } from 'react'
import type { Load } from '../api/types.ts'

// Runs `request` whenever `key` changes and returns its Load state. A response is only
// shown for the key it answered, so a slow old response never replaces a newer query,
// and an in-flight request is aborted when the key changes.
export function useRequest<T>(key: string | null, request: (signal: AbortSignal) => Promise<T>): Load<T> {
  const [result, setResult] = useState<{ key: string; load: Load<T> } | null>(null)

  useEffect(() => {
    if (key === null) return
    const controller = new AbortController()
    request(controller.signal)
      .then((data) => setResult({ key, load: { state: 'ready', data } }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setResult({ key, load: { state: 'error', error } })
      })
    return () => controller.abort()
    // `request` is rebuilt every render; `key` is what identifies the query.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return result !== null && result.key === key ? result.load : { state: 'loading' }
}
