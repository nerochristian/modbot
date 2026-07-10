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
      script: 'dashboard/server.js',
      interpreter: 'node',
      cwd: __dirname,
      env: {
        NODE_ENV: 'production',
        PORT: process.env.DASHBOARD_PORT || '10547',
        HOSTNAME: '0.0.0.0',
      },
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
    },
  ],
}
