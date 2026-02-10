module.exports = {
    apps: [
        {
            name: 'clawbot-ai',
            script: 'main.py',
            interpreter: 'python3',
            cwd: __dirname,
            env: {
                NODE_ENV: 'production'
            },

            // Restart settings
            autorestart: true,
            max_restarts: 10,
            restart_delay: 5000,
            kill_timeout: 10000,  // Graceful shutdown (close Playwright etc.)

            // Logging
            log_file: './logs/combined.log',
            out_file: './logs/out.log',
            error_file: './logs/error.log',
            log_date_format: 'YYYY-MM-DD HH:mm:ss',
            merge_logs: true,

            // Performance — VPS 2-core 8GB
            max_memory_restart: '1G',  // Allow headroom for Playwright
            node_args: '--max-old-space-size=512',

            // Watch for changes (disable in production)
            watch: false,
            ignore_watch: ['logs', 'data', '__pycache__', '.git']
        }
    ]
};
