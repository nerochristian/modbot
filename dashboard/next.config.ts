import type { NextConfig } from 'next'
import path from 'node:path'

const nextConfig: NextConfig = {
  // Pin the file-tracing root to this app so Next doesn't infer the parent
  // repository as the workspace root (it contains its own lockfile).
  outputFileTracingRoot: path.join(__dirname),
}

export default nextConfig
