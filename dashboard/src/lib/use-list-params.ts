'use client'

import { useMemo, useState } from 'react'

export type ListParams = {
  page: number
  pageSize: number
  sort: string
  order: 'asc' | 'desc'
  q: string
  filters: Record<string, string>
}

/**
 * Local state for a server-driven list view, plus a serialized query string.
 * Setting search/filters/sort resets to page 1; toggling a sort column flips
 * order. Feed `queryString` into the list API.
 */
export function useListParams(initial?: Partial<ListParams>) {
  const [params, setParams] = useState<ListParams>({
    page: 1,
    pageSize: 10,
    sort: 'createdAt',
    order: 'desc',
    q: '',
    filters: {},
    ...initial,
  })

  const api = useMemo(
    () => ({
      params,
      setPage: (page: number) => setParams((p) => ({ ...p, page })),
      setPageSize: (pageSize: number) => setParams((p) => ({ ...p, pageSize, page: 1 })),
      setQuery: (q: string) => setParams((p) => ({ ...p, q, page: 1 })),
      setFilter: (key: string, value: string) =>
        setParams((p) => {
          const filters = { ...p.filters }
          if (value) filters[key] = value
          else delete filters[key]
          return { ...p, filters, page: 1 }
        }),
      clearFilters: () => setParams((p) => ({ ...p, filters: {}, q: '', page: 1 })),
      toggleSort: (column: string) =>
        setParams((p) => ({
          ...p,
          sort: column,
          order: p.sort === column && p.order === 'desc' ? 'asc' : 'desc',
          page: 1,
        })),
      setState: (state: Partial<ListParams>) => setParams((p) => ({ ...p, ...state })),
    }),
    [params],
  )

  const queryString = useMemo(() => {
    const sp = new URLSearchParams()
    sp.set('page', String(params.page))
    sp.set('pageSize', String(params.pageSize))
    sp.set('sort', params.sort)
    sp.set('order', params.order)
    if (params.q) sp.set('q', params.q)
    for (const [k, v] of Object.entries(params.filters)) sp.set(`filter.${k}`, v)
    return sp.toString()
  }, [params])

  const activeFilterCount = Object.keys(params.filters).length + (params.q ? 1 : 0)

  return { ...api, queryString, activeFilterCount }
}
