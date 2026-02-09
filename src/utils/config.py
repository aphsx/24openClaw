"""
Configuration module
Loads environment variables and provides config access
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # === BINANCE ===
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    
    # === AI PROVIDERS ===
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    KIMI_API_KEY = os.getenv('KIMI_API_KEY', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')  # FREE option!
    
    # === AI MODEL SELECTION ===
    PRIMARY_AI_MODEL = os.getenv('PRIMARY_AI_MODEL', 'groq')  # Default to free
    BACKUP_AI_MODEL = os.getenv('BACKUP_AI_MODEL', 'claude')
    
    # === DATABASE ===
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # === TELEGRAM ===
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # === SETTINGS ===
    CYCLE_INTERVAL_SECONDS = int(os.getenv('CYCLE_INTERVAL_SECONDS', '120'))  # 2 min for scalping
    MAX_POSITIONS = int(os.getenv('MAX_POSITIONS', '2'))  # Reduced for 20x
    DEFAULT_LEVERAGE = int(os.getenv('DEFAULT_LEVERAGE', '20'))
    DEFAULT_MARGIN = float(os.getenv('DEFAULT_MARGIN', '10'))
    
    # === SCALPING RISK PARAMETERS ===
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '3'))     # -3% for 20x
    TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', '5')) # +5% target
    TRAILING_STOP_ENABLED = os.getenv('TRAILING_STOP_ENABLED', 'false').lower() == 'true'
    MIN_ENTRY_SCORE = int(os.getenv('MIN_ENTRY_SCORE', '65'))  # Lower for scalping
    
    # === COINS TO TRACK ===
    TRACKED_COINS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT"
    ]
    
    # === PATHS ===
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / 'data'
    RAW_DATA_DIR = DATA_DIR / 'raw'
    PROCESSED_DATA_DIR = DATA_DIR / 'processed'
    LOGS_DIR = BASE_DIR / 'logs'
    
    @classmethod
    def validate(cls):
        """Validate required config values"""
        required = [
            ('BINANCE_API_KEY', cls.BINANCE_API_KEY),
            ('BINANCE_API_SECRET', cls.BINANCE_API_SECRET),
            ('SUPABASE_URL', cls.SUPABASE_URL),
            ('SUPABASE_KEY', cls.SUPABASE_KEY),
        ]
        
        missing = [name for name, value in required if not value]
        
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")
        
        return True


# Create singleton instance
config = Config()
