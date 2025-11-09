#!/usr/bin/env python3
"""
Enhanced SMS Auto-Responder with Advanced Features
- Configurable responses
- Whitelist/Blacklist support
- Database logging
- Email notifications
- Multiple retry attempts
"""

import requests
import sqlite3
import time
import random
import logging
from datetime import datetime
from typing import Set, Optional, List
from urllib.parse import quote
from pathlib import Path

# Try to import optional dependencies
try:
    from plyer import notification as desktop_notify
    DESKTOP_NOTIFY_AVAILABLE = True
except ImportError:
    DESKTOP_NOTIFY_AVAILABLE = False
    desktop_notify = None

try:
    import smtplib
    from email.message import EmailMessage
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False


class ResponseDatabase:
    """Database for logging auto-responses."""
    
    def __init__(self, db_path: str = "sms_responses.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                response_message TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN NOT NULL,
                attempt_count INTEGER DEFAULT 1
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_phone 
            ON responses(phone_number)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sent_at 
            ON responses(sent_at)
        """)
        
        conn.commit()
        conn.close()
    
    def log_response(self, phone: str, message: str, success: bool, attempts: int = 1):
        """Log a response attempt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO responses (phone_number, response_message, success, attempt_count)
            VALUES (?, ?, ?, ?)
        """, (phone, message, success, attempts))
        
        conn.commit()
        conn.close()
    
    def has_responded_to(self, phone: str) -> bool:
        """Check if we've already responded to this number."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM responses 
            WHERE phone_number = ? AND success = 1
        """, (phone,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def get_stats(self) -> dict:
        """Get response statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM responses WHERE success = 1")
        successful = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM responses WHERE success = 0")
        failed = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT phone_number) FROM responses")
        unique_numbers = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'successful': successful,
            'failed': failed,
            'total': successful + failed,
            'unique_numbers': unique_numbers
        }


class EnhancedAutoResponder:
    """Enhanced auto-responder with advanced features."""
    
    def __init__(self, config_path: Optional[str] = None):
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Setup components
        self.base_url = self.config['ROUTER_URL'].rstrip('/')
        self.password = self.config['PASSWORD']
        self.username = self.config.get('USERNAME', '')
        
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        
        self.authenticated = False
        self.last_keep_alive = 0.0
        
        # Response tracking
        if self.config.get('SAVE_TO_DATABASE', True):
            self.db = ResponseDatabase(self.config.get('DATABASE_FILE', 'sms_responses.db'))
        else:
            self.db = None
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from file or use defaults."""
        default_config = {
            'ROUTER_URL': 'http://192.168.123.254',
            'USERNAME': '',
            'PASSWORD': 'admin',
            'RESPONSE_MESSAGE': '2',
            'RESPOND_ONCE_PER_NUMBER': True,
            'POLL_INTERVAL': 3.0,
            'WHITELIST': [],
            'BLACKLIST': [],
            'MIN_DELAY_BETWEEN_RESPONSES': 1.0,
            'MAX_DELAY_BETWEEN_RESPONSES': 2.0,
            'MAX_RETRY_ATTEMPTS': 3,
            'RETRY_DELAY': 5.0,
            'ENABLE_LOGGING_TO_FILE': True,
            'LOG_FILE': 'autoresponder.log',
            'LOG_LEVEL': 'INFO',
            'ENABLE_DESKTOP_NOTIFICATIONS': False,
            'ENABLE_EMAIL_NOTIFICATIONS': False,
            'SAVE_TO_DATABASE': True,
            'DATABASE_FILE': 'sms_responses.db'
        }
        
        if config_path and Path(config_path).exists():
            # Load from Python config file
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", config_path)
            if spec and spec.loader:
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                
                for key in default_config:
                    if hasattr(config_module, key):
                        default_config[key] = getattr(config_module, key)
        
        return default_config
    
    def _setup_logging(self):
        """Configure logging."""
        log_level = getattr(logging, self.config.get('LOG_LEVEL', 'INFO'))
        
        handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        handlers.append(console_handler)
        
        # File handler
        if self.config.get('ENABLE_LOGGING_TO_FILE', True):
            file_handler = logging.FileHandler(self.config.get('LOG_FILE', 'autoresponder.log'))
            file_handler.setLevel(log_level)
            handlers.append(file_handler)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
    
    def _gen_sids(self) -> int:
        """Generate random session ID."""
        return int(random.random() * 1000000)
    
    def _should_respond_to(self, phone: str) -> bool:
        """Check if we should respond to this number."""
        # Check whitelist
        whitelist = self.config.get('WHITELIST', [])
        if whitelist and phone not in whitelist:
            return False
        
        # Check blacklist
        blacklist = self.config.get('BLACKLIST', [])
        if phone in blacklist:
            return False
        
        # Check if already responded
        if self.config.get('RESPOND_ONCE_PER_NUMBER', True):
            if self.db and self.db.has_responded_to(phone):
                return False
        
        return True
    
    def authenticate(self) -> bool:
        """Authenticate with router."""
        try:
            params = {
                'which_ajax': 'check_password',
                'pram': quote(self.password),
                'username': quote(self.username),
                'sids': self._gen_sids()
            }
            
            url = f"{self.base_url}/cgi-bin/ajax_get.cgi"
            response = self.session.post(url, params=params, timeout=10)
            
            if response.text.strip() == '1':
                self.authenticated = True
                self.logger.info("✅ Authentication successful")
                return True
            else:
                self.logger.error(f"❌ Authentication failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Authentication error: {e}")
            return False
    
    def keep_alive(self) -> bool:
        """Maintain session."""
        try:
            url = f"{self.base_url}/cgi-bin/keep_alive.cgi"
            self.session.post(url, timeout=10)
            self.last_keep_alive = time.time()
            return True
        except:
            return False
    
    def send_sms(self, phone: str, message: str) -> bool:
        """Send SMS with retry logic."""
        max_attempts = self.config.get('MAX_RETRY_ATTEMPTS', 3)
        retry_delay = self.config.get('RETRY_DELAY', 5.0)
        
        for attempt in range(1, max_attempts + 1):
            try:
                # Try multiple API patterns
                patterns = [
                    {
                        'which_cgi': 'sms_send',
                        'phone': quote(phone),
                        'message': quote(message),
                        'sids': self._gen_sids()
                    },
                    {
                        'which_cgi': 'ajax_send_sms',
                        'to': quote(phone),
                        'content': quote(message),
                        'sids': self._gen_sids()
                    },
                    {
                        'which_cgi': 'send',
                        'number': quote(phone),
                        'text': quote(message),
                        'sids': self._gen_sids()
                    }
                ]
                
                for params in patterns:
                    url = f"{self.base_url}/cgi-bin/sms.cgi"
                    response = self.session.post(url, params=params, timeout=15)
                    
                    success_indicators = ['ok', 'success', '1', 'sent']
                    if any(ind in response.text.lower() for ind in success_indicators):
                        if self.db:
                            self.db.log_response(phone, message, True, attempt)
                        return True
                
                if attempt < max_attempts:
                    self.logger.warning(f"⚠️  Attempt {attempt} failed, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
            
            except Exception as e:
                self.logger.error(f"❌ Send attempt {attempt} error: {e}")
                if attempt < max_attempts:
                    time.sleep(retry_delay)
        
        if self.db:
            self.db.log_response(phone, message, False, max_attempts)
        
        return False
    
    def get_new_messages(self) -> List[dict]:
        """Poll for new messages."""
        try:
            params = {
                'which_ajax': 'tmpdatabase',
                'pram': 'sms_new_msg_notify',
                'sids': self._gen_sids()
            }
            
            url = f"{self.base_url}/cgi-bin/ajax_get.cgi"
            response = self.session.post(url, params=params, timeout=10)
            
            new_messages = []
            for entry in response.text.split('>'):
                if entry.strip():
                    parts = entry.split(',')
                    if len(parts) == 3 and parts[1] == '0':  # New message
                        new_messages.append({
                            'phone': parts[0],
                            'notif_flag': parts[1],
                            'send_flag': parts[2]
                        })
            
            return new_messages
        except Exception as e:
            self.logger.error(f"Error polling: {e}")
            return []
    
    def acknowledge_messages(self, messages: List[dict]):
        """Mark messages as read."""
        if not messages:
            return
        
        try:
            ack_parts = [f"{msg['phone']},1,{msg['send_flag']}" for msg in messages]
            ack_string = '>'.join(ack_parts) + '>'
            
            params = {
                'which_cgi': 'ajax_set_tmp_nv',
                'nv': 'sms_new_msg_notify',
                'pram': ack_string,
                'sids': self._gen_sids()
            }
            
            url = f"{self.base_url}/cgi-bin/sms.cgi"
            self.session.post(url, params=params, timeout=10)
        except Exception as e:
            self.logger.error(f"Error acknowledging: {e}")
    
    def run(self):
        """Run auto-responder."""
        if not self.authenticated:
            self.logger.error("Not authenticated!")
            return
        
        self.logger.info("=" * 70)
        self.logger.info("ENHANCED SMS AUTO-RESPONDER ACTIVE")
        self.logger.info(f"Response message: '{self.config['RESPONSE_MESSAGE']}'")
        self.logger.info(f"Respond once per number: {self.config['RESPOND_ONCE_PER_NUMBER']}")
        self.logger.info("=" * 70)
        
        try:
            while True:
                # Keep alive
                if (time.time() - self.last_keep_alive) > 3.0:
                    if not self.keep_alive():
                        if not self.authenticate():
                            break
                
                # Poll messages
                new_messages = self.get_new_messages()
                
                if new_messages:
                    self.logger.info(f"📨 Received {len(new_messages)} new message(s)")
                    
                    for msg in new_messages:
                        phone = msg['phone']
                        
                        if not self._should_respond_to(phone):
                            self.logger.info(f"⏭️  Skipping {phone}")
                            continue
                        
                        self.logger.info(f"📱 Processing message from: {phone}")
                        
                        # Random delay
                        delay = random.uniform(
                            self.config['MIN_DELAY_BETWEEN_RESPONSES'],
                            self.config['MAX_DELAY_BETWEEN_RESPONSES']
                        )
                        time.sleep(delay)
                        
                        # Send response
                        success = self.send_sms(phone, self.config['RESPONSE_MESSAGE'])
                        
                        if success:
                            self.logger.info(f"✅ Auto-responded to {phone}")
                        else:
                            self.logger.warning(f"❌ Failed to respond to {phone}")
                                            
                    self.acknowledge_messages(new_messages)
                
                time.sleep(self.config['POLL_INTERVAL'])
                
        except KeyboardInterrupt:
            self.logger.info("\n" + "=" * 70)
            self.logger.info("Auto-responder stopped")
            
            if self.db:
                stats = self.db.get_stats()
                self.logger.info(f"Statistics:")
                self.logger.info(f"  Total responses: {stats['total']}")
                self.logger.info(f"  Successful: {stats['successful']}")
                self.logger.info(f"  Failed: {stats['failed']}")
                self.logger.info(f"  Unique numbers: {stats['unique_numbers']}")
            
            self.logger.info("=" * 70)


def main():
    """Main entry point."""
    import sys
    
    # Check for config file
    config_file = "config.py" if Path("config.py").exists() else None
    
    if not config_file:
        print("⚠️  No config.py found. Using default configuration.")
        print("Copy config_example.py to config.py and customize it.")
        print()
    
    # Create and run responder
    responder = EnhancedAutoResponder(config_file)
    
    if not responder.authenticate():
        print("❌ Authentication failed. Check your configuration.")
        sys.exit(1)
    
    responder.run()


if __name__ == "__main__":
    main()