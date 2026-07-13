const path = require('node:path')
const fs = require('node:fs')
const { parseEnv } = require('node:util')

let fileEnv = {}
try {
  fileEnv = parseEnv(fs.readFileSync(path.join(__dirname, '.env'), 'utf8'))
} catch (error) {
  if (error?.code !== 'ENOENT') throw error
}
// The checked deployment environment must override values inherited from an
// older PM2 process; otherwise an HTTPS migration can retain stale HTTP flags.
const rootEnv = { ...process.env, ...fileEnv }
const dashboardDatabaseUrl = rootEnv.DASHBOARD_DATABASE_URL
  || `file:${path.join(__dirname, 'dashboard', 'data', 'dashboard.db').replace(/\\/g, '/')}`
const botDatabaseUrl = rootEnv.BOT_DATABASE_URL || rootEnv.DATABASE_URL

module.exports = {
  apps: [
    {
      name: 'modbot',
      script: 'bot.py',
      interpreter: 'python3',
      cwd: __dirname,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
    },
    {
      name: 'modbot-dashboard',
      script: 'dashboard/.next/standalone/server.js',
      interpreter: 'node',
      cwd: __dirname,
      env: {
        ...rootEnv,
        NODE_ENV: 'production',
        PORT: rootEnv.DASHBOARD_PORT || '10547',
        HOSTNAME: rootEnv.DASHBOARD_HOSTNAME || '127.0.0.1',
        DATABASE_URL: dashboardDatabaseUrl,
        DASHBOARD_DATABASE_URL: dashboardDatabaseUrl,
        BOT_DATABASE_URL: botDatabaseUrl,
        AUTH_SECRET: rootEnv.AUTH_SECRET || rootEnv.SESSION_SECRET,
      },
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
    },
  ],
}
