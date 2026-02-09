module.exports = {
    apps: [
        {
            name: 'jarvis-v5',
            script: 'main.py',
            interpreter: 'python',
            cwd: __dirname,
            env: {
                NODE_ENV: 'production'
            },

            // Restart settings
            autorestart: true,
            max_restarts: 10,
            restart_delay: 5000,

            // Logging
            log_file: './logs/combined.log',
            out_file: './logs/out.log',
            error_file: './logs/error.log',
            log_date_format: 'YYYY-MM-DD HH:mm:ss',

            // Performance
            max_memory_restart: '500M',

            // Watch for changes (disable in production)
            watch: false,
            ignore_watch: ['logs', 'data', '__pycache__', '.git']
        }
    ]
};
