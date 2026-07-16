import { readFile } from 'node:fs/promises'
import path from 'node:path'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

const TRANSCRIPT_FILENAME = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,118}\.html$/

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ filename: string }> },
) {
  const { filename } = await params
  if (!TRANSCRIPT_FILENAME.test(filename) || path.basename(filename) !== filename) {
    return new Response('Not found', { status: 404 })
  }

  const roots = process.env.TRANSCRIPT_STORAGE_DIR
    ? [process.env.TRANSCRIPT_STORAGE_DIR]
    : [
        path.join(process.cwd(), 'data', 'transcripts'),
        path.join(process.cwd(), '..', 'data', 'transcripts'),
        path.join(process.cwd(), '..', '..', '..', 'data', 'transcripts'),
      ]

  for (const root of roots) {
    try {
      const transcript = await readFile(path.join(/*turbopackIgnore: true*/ root, filename))
      return new Response(new Uint8Array(transcript), {
        headers: {
          'Cache-Control': 'private, no-store',
          'Content-Security-Policy': "default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; sandbox",
          'Content-Type': 'text/html; charset=utf-8',
          'X-Content-Type-Options': 'nosniff',
        },
      })
    } catch (error) {
      const code = (error as NodeJS.ErrnoException).code
      if (code === 'ENOENT' || code === 'EISDIR') continue
      console.error('Failed to read transcript', error)
      return new Response('Unable to load transcript', { status: 500 })
    }
  }
  return new Response('Not found', { status: 404 })
}
