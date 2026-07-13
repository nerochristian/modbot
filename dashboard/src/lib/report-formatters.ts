import { strToU8, zipSync } from 'fflate'
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib'

export type ReportFormat = 'csv' | 'json' | 'pdf' | 'xlsx'
export type ReportRow = Record<string, unknown>

function headersFor(rows: ReportRow[]): string[] {
  const headers = new Set<string>()
  for (const row of rows) Object.keys(row).forEach((key) => headers.add(key))
  return [...headers]
}

export function neutralizeSpreadsheetFormula(value: unknown): unknown {
  if (typeof value !== 'string') return value
  return /^[\t\r ]*[=+\-@]/.test(value) ? `'${value}` : value
}

function csvCell(value: unknown): string {
  const safe = neutralizeSpreadsheetFormula(value)
  const serialized = safe == null ? '' : typeof safe === 'object' ? JSON.stringify(safe) : String(safe)
  return /[",\r\n]/.test(serialized) ? `"${serialized.replace(/"/g, '""')}"` : serialized
}

export function reportRowsToCsv(rows: ReportRow[]): string {
  const headers = headersFor(rows)
  if (headers.length === 0) return 'no data\r\n'
  return [
    headers.map(csvCell).join(','),
    ...rows.map((row) => headers.map((header) => csvCell(row[header])).join(',')),
  ].join('\r\n') + '\r\n'
}

export function reportRowsToJson(rows: ReportRow[]): string {
  return `${JSON.stringify(rows, null, 2)}\n`
}

function xmlEscape(value: string): string {
  return value
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

function excelColumn(index: number): string {
  let value = index + 1
  let column = ''
  while (value > 0) {
    value -= 1
    column = String.fromCharCode(65 + (value % 26)) + column
    value = Math.floor(value / 26)
  }
  return column
}

function xlsxCell(reference: string, raw: unknown, style = ''): string {
  const value = neutralizeSpreadsheetFormula(raw)
  if (typeof value === 'number' && Number.isFinite(value)) {
    return `<c r="${reference}"${style}><v>${value}</v></c>`
  }
  if (typeof value === 'boolean') return `<c r="${reference}" t="b"${style}><v>${value ? 1 : 0}</v></c>`
  const text = value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value)
  return `<c r="${reference}" t="inlineStr"${style}><is><t xml:space="preserve">${xmlEscape(text)}</t></is></c>`
}

export async function reportRowsToXlsx(name: string, rows: ReportRow[]): Promise<Buffer> {
  const headers = headersFor(rows)
  const headerRow = `<row r="1">${headers.map((header, index) =>
    xlsxCell(`${excelColumn(index)}1`, header.replace(/_/g, ' ').replace(/^\w/, (letter) => letter.toUpperCase()), ' s="1"'),
  ).join('')}</row>`
  const dataRows = rows.map((row, rowIndex) => {
    const number = rowIndex + 2
    return `<row r="${number}">${headers.map((header, columnIndex) =>
      xlsxCell(`${excelColumn(columnIndex)}${number}`, row[header]),
    ).join('')}</row>`
  }).join('')
  const lastCell = headers.length > 0 ? `${excelColumn(headers.length - 1)}${Math.max(1, rows.length + 1)}` : 'A1'
  const columns = headers.map((header, index) =>
    `<col min="${index + 1}" max="${index + 1}" width="${Math.min(60, Math.max(14, header.length + 4))}" customWidth="1"/>`,
  ).join('')
  const sheetName = (name.replace(/[\\/*?:[\]]/g, ' ').trim().slice(0, 31) || 'Report')
  const files: Record<string, Uint8Array> = {
    '[Content_Types].xml': strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
      <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
        <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
        <Default Extension="xml" ContentType="application/xml"/>
        <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
        <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
        <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
      </Types>`),
    '_rels/.rels': strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
      <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
        <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
      </Relationships>`),
    'xl/workbook.xml': strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
      <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
        <sheets><sheet name="${xmlEscape(sheetName)}" sheetId="1" r:id="rId1"/></sheets>
      </workbook>`),
    'xl/_rels/workbook.xml.rels': strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
      <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
        <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
        <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
      </Relationships>`),
    'xl/styles.xml': strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
      <styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
        <fonts count="2"><font/><font><b/><color rgb="FFFFFFFF"/></font></fonts>
        <fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF2743E6"/><bgColor indexed="64"/></patternFill></fill></fills>
        <borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs>
        <cellXfs count="2"><xf xfId="0"/><xf xfId="0" fontId="1" fillId="1" applyFont="1" applyFill="1"/></cellXfs>
      </styleSheet>`),
    'xl/worksheets/sheet1.xml': strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
      <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
        <dimension ref="A1:${lastCell}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
        <cols>${columns}</cols><sheetData>${headerRow}${dataRows}</sheetData>
        ${headers.length > 0 ? `<autoFilter ref="A1:${lastCell}"/>` : ''}
      </worksheet>`),
  }
  return Buffer.from(zipSync(files, { level: 6 }))
}

function wrapText(text: string, width = 105): string[] {
  const normalized = text.replace(/\s+/g, ' ').trim()
  if (!normalized) return ['']
  const lines: string[] = []
  let remaining = normalized
  while (remaining.length > width) {
    let split = remaining.lastIndexOf(' ', width)
    if (split < width / 2) split = width
    lines.push(remaining.slice(0, split))
    remaining = remaining.slice(split).trimStart()
  }
  lines.push(remaining)
  return lines
}

export async function reportRowsToPdf(name: string, rows: ReportRow[]): Promise<Buffer> {
  const document = await PDFDocument.create()
  const regular = await document.embedFont(StandardFonts.Helvetica)
  const bold = await document.embedFont(StandardFonts.HelveticaBold)
  const pageSize: [number, number] = [612, 792]
  let page = document.addPage(pageSize)
  let y = 752
  const addLine = (text: string, options?: { bold?: boolean; size?: number; color?: ReturnType<typeof rgb> }) => {
    const size = options?.size ?? 8
    if (y < 42) {
      page = document.addPage(pageSize)
      y = 752
    }
    page.drawText(text, {
      x: 36,
      y,
      size,
      font: options?.bold ? bold : regular,
      color: options?.color ?? rgb(0.12, 0.14, 0.2),
    })
    y -= size + 5
  }
  addLine(name, { bold: true, size: 16, color: rgb(0.15, 0.26, 0.9) })
  addLine(`Generated ${new Date().toISOString()} · ${rows.length} records`, { size: 9 })
  y -= 8
  if (rows.length === 0) addLine('No data matched this report.')
  rows.forEach((row, index) => {
    addLine(`Record ${index + 1}`, { bold: true, size: 9 })
    for (const [key, raw] of Object.entries(row)) {
      const value = raw == null ? '' : typeof raw === 'object' ? JSON.stringify(raw) : String(raw)
      for (const line of wrapText(`${key.replace(/_/g, ' ')}: ${value}`)) addLine(line)
    }
    y -= 5
  })
  return Buffer.from(await document.save())
}

export async function buildReportArtifact(format: ReportFormat, name: string, rows: ReportRow[]) {
  if (format === 'json') {
    return { body: Buffer.from(reportRowsToJson(rows)), contentType: 'application/json; charset=utf-8', extension: 'json' }
  }
  if (format === 'xlsx') {
    return { body: await reportRowsToXlsx(name, rows), contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', extension: 'xlsx' }
  }
  if (format === 'pdf') {
    return { body: await reportRowsToPdf(name, rows), contentType: 'application/pdf', extension: 'pdf' }
  }
  return { body: Buffer.from(reportRowsToCsv(rows)), contentType: 'text/csv; charset=utf-8', extension: 'csv' }
}
