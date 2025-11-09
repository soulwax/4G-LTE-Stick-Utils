# SMS Auto-Responder Configuration
# Copy this to config.py and customize your settings

# Router Configuration
ROUTER_URL = "http://192.168.123.254"
USERNAME = ""  # Usually empty for this router model
PASSWORD = "admin"  # CHANGE THIS to your router password

# Auto-Response Settings
RESPONSE_MESSAGE = "2"  # Message to auto-reply with
RESPOND_ONCE_PER_NUMBER = True  # Only respond once per phone number
POLL_INTERVAL = 3.0  # Seconds between checks (3s recommended)

# Advanced Settings
ENABLE_LOGGING_TO_FILE = True
LOG_FILE = "autoresponder.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# Whitelist/Blacklist (optional)
# Leave empty to respond to all numbers
WHITELIST = []  # Only respond to these numbers: ["+1234567890", "+0987654321"]
BLACKLIST = []  # Never respond to these numbers: ["+spam123456"]

# Response Delay
MIN_DELAY_BETWEEN_RESPONSES = 1.0  # Minimum seconds between sending responses
MAX_DELAY_BETWEEN_RESPONSES = 2.0  # Maximum seconds (randomized)

# Notification Settings
ENABLE_DESKTOP_NOTIFICATIONS = False  # Requires: pip install plyer
ENABLE_EMAIL_NOTIFICATIONS = False
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "from_email": "your_email@gmail.com",
    "password": "your_app_password",
    "to_email": "notify@example.com"
}

# Database Settings
SAVE_TO_DATABASE = True
DATABASE_FILE = "sms_responses.db"

# Retry Settings
MAX_RETRY_ATTEMPTS = 3  # Times to retry sending if it fails
RETRY_DELAY = 5.0  # Seconds to wait before retrying