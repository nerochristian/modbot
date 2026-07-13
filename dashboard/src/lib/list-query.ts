export type ListQuery = {
  page: number
  pageSize: number
  sort: string
  order: 'asc' | 'desc'
  q: string
  filters: Record<string, string>
}

/**
 * Parse standard list query params for server-side pagination/sort/filter.
 * Recognized: page, pageSize, sort, order, q. Any `filter.<field>=value` pair
 * is collected into `filters`.
 */
export function parseListQuery(
  url: URL,
  opts?: { defaultSort?: string; maxPageSize?: number },
): ListQuery {
  const sp = url.searchParams
  const parsePositiveInteger = (value: string | null, fallback: number) => {
    const parsed = Number(value)
    return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : fallback
  }
  const page = parsePositiveInteger(sp.get('page'), 1)
  const maxPageSize = opts?.maxPageSize ?? 100
  const pageSize = Math.min(maxPageSize, parsePositiveInteger(sp.get('pageSize'), 10))
  const sort = sp.get('sort') || opts?.defaultSort || 'createdAt'
  const order = sp.get('order') === 'asc' ? 'asc' : 'desc'
  const q = (sp.get('q') || '').trim()

  const filters: Record<string, string> = {}
  for (const [key, value] of sp.entries()) {
    if (key.startsWith('filter.') && value) {
      filters[key.slice('filter.'.length)] = value
    }
  }

  return { page, pageSize, sort, order, q, filters }
}

export type Paginated<T> = {
  data: T[]
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export function paginate<T>(data: T[], total: number, query: ListQuery): Paginated<T> {
  return {
    data,
    page: query.page,
    pageSize: query.pageSize,
    total,
    totalPages: Math.max(1, Math.ceil(total / query.pageSize)),
  }
}
