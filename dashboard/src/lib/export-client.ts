'use client'

/** Client-side export helpers for downloading table/series data. */

export function downloadFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return ''
  const headers = Object.keys(rows[0])
  const escape = (v: unknown) => {
    let s = v == null ? '' : String(v)
    if (/^[=+\-@]/.test(s)) s = `'${s}`
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const lines = [headers.join(',')]
  for (const row of rows) lines.push(headers.map((h) => escape(row[h])).join(','))
  return lines.join('\n')
}

/** Export records in the two formats implemented entirely in the browser. */
export function exportRecords(
  rows: Record<string, unknown>[],
  format: 'csv' | 'json' | 'xlsx' | 'pdf',
  baseName: string,
) {
  if (format === 'json') {
    downloadFile(`${baseName}.json`, JSON.stringify(rows, null, 2), 'application/json')
    return
  }
  if (format !== 'csv') {
    throw new Error('PDF and XLSX exports are generated from the Reports page.')
  }
  const csv = toCsv(rows)
  downloadFile(`${baseName}.csv`, csv, 'text/csv')
}
