#!/usr/bin/env python3
"""
SMS Modem Client for XSBox/4G Systems LTE Router
Handles authentication, session management, and SMS polling/operations.
"""

import requests
import time
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import quote
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class SmsNotification:
    """Represents an SMS notification from the device."""
    phone_number: str
    is_new_message: bool
    is_send_success: bool
    
    @classmethod
    def parse(cls, data_str: str) -> Optional['SmsNotification']:
        """Parse notification string format: 'phone,notification_flag,send_flag'"""
        parts = data_str.split(',')
        if len(parts) != 3:
            return None
        
        phone, notif_flag, send_flag = parts
        return cls(
            phone_number=phone,
            is_new_message=(notif_flag == '0'),
            is_send_success=(send_flag == '0')
        )


class SmsModemClient:
    """Client for interacting with SMS modem router."""
    
    BASE_CGI_PATH = '/cgi-bin'
    AJAX_GET_ENDPOINT = f'{BASE_CGI_PATH}/ajax_get.cgi'
    SMS_ENDPOINT = f'{BASE_CGI_PATH}/sms.cgi'
    KEEP_ALIVE_ENDPOINT = f'{BASE_CGI_PATH}/keep_alive.cgi'
    
    POLL_INTERVAL = 3.0  # seconds
    KEEP_ALIVE_INTERVAL = 3.0  # seconds
    
    def __init__(self, base_url: str, username: str = '', password: str = ''):
        """
        Initialize SMS modem client.
        
        Args:
            base_url: Router base URL (e.g., 'http://192.168.1.1')
            username: Admin username (may be empty for some devices)
            password: Admin password
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        self.authenticated = False
        self.last_keep_alive = 0.0
        
    def _generate_sids(self) -> int:
        """Generate random session ID for requests."""
        return int(random.random() * 1000000)
    
    def authenticate(self) -> bool:
        """
        Authenticate with the router.
        
        Returns:
            True if authentication successful
        """
        try:
            # Check password endpoint
            params = {
                'which_ajax': 'check_password',
                'pram': quote(self.password),
                'username': quote(self.username),
                'sids': self._generate_sids()
            }
            
            url = f"{self.base_url}{self.AJAX_GET_ENDPOINT}"
            response = self.session.post(url, params=params, timeout=10)
            
            if response.text.strip() == '1':
                self.authenticated = True
                logger.info("Authentication successful")
                return True
            else:
                logger.error(f"Authentication failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def keep_alive(self) -> bool:
        """
        Send keep-alive request to maintain session.
        
        Returns:
            True if session is still valid
        """
        try:
            url = f"{self.base_url}{self.KEEP_ALIVE_ENDPOINT}"
            response = self.session.post(url, timeout=10)
            self.last_keep_alive = time.time()
            
            # Session invalid if response contains certain error indicators
            if 'error' in response.text.lower():
                self.authenticated = False
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Keep-alive error: {e}")
            return False
    
    def get_sms_notifications(self) -> List[SmsNotification]:
        """
        Poll for SMS notifications.
        
        Returns:
            List of SMS notifications (received messages and sent confirmations)
        """
        try:
            params = {
                'which_ajax': 'tmpdatabase',
                'pram': 'sms_new_msg_notify',
                'sids': self._generate_sids()
            }
            
            url = f"{self.base_url}{self.AJAX_GET_ENDPOINT}"
            response = self.session.post(url, params=params, timeout=10)
            
            # Response format: "phone1,flag1,flag2>phone2,flag1,flag2>..."
            notifications = []
            for entry in response.text.split('>'):
                if entry.strip():
                    notif = SmsNotification.parse(entry)
                    if notif:
                        notifications.append(notif)
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting SMS notifications: {e}")
            return []
    
    def acknowledge_sms_notifications(self, notifications: List[SmsNotification]) -> bool:
        """
        Acknowledge SMS notifications by updating their read/sent status.
        
        Args:
            notifications: List of notifications to acknowledge
            
        Returns:
            True if acknowledgment successful
        """
        if not notifications:
            return True
        
        try:
            # Build acknowledgment string
            # Format: "phone,1,original_send_flag>" for read messages
            # Format: "phone,original_notif_flag,1>" for sent confirmations
            ack_parts = []
            for notif in notifications:
                if notif.is_new_message:
                    # Mark message as read
                    ack_parts.append(f"{notif.phone_number},1,0")
                elif notif.is_send_success:
                    # Mark send as acknowledged
                    ack_parts.append(f"{notif.phone_number},0,1")
                else:
                    # Keep original flags
                    ack_parts.append(f"{notif.phone_number},1,1")
            
            ack_string = '>'.join(ack_parts) + '>'
            
            params = {
                'which_cgi': 'ajax_set_tmp_nv',
                'nv': 'sms_new_msg_notify',
                'pram': ack_string,
                'sids': self._generate_sids()
            }
            
            url = f"{self.base_url}{self.SMS_ENDPOINT}"
            response = self.session.post(url, params=params, timeout=10)
            
            return True
            
        except Exception as e:
            logger.error(f"Error acknowledging SMS: {e}")
            return False
    
    def poll_sms(self, callback, auto_acknowledge: bool = True, 
                  interval: Optional[float] = None) -> None:
        """
        Continuously poll for SMS notifications.
        
        Args:
            callback: Function to call with list of notifications
            auto_acknowledge: Automatically acknowledge notifications after callback
            interval: Polling interval in seconds (default: 3.0)
        """
        if not self.authenticated:
            logger.error("Not authenticated. Call authenticate() first.")
            return
        
        interval = interval or self.POLL_INTERVAL
        
        logger.info(f"Starting SMS polling (interval: {interval}s)")
        
        try:
            while True:
                # Keep session alive
                if (time.time() - self.last_keep_alive) > self.KEEP_ALIVE_INTERVAL:
                    if not self.keep_alive():
                        logger.error("Session expired, re-authenticating...")
                        if not self.authenticate():
                            logger.error("Re-authentication failed")
                            break
                
                # Poll for notifications
                notifications = self.get_sms_notifications()
                
                if notifications:
                    # Filter for new messages only (not send confirmations)
                    new_messages = [n for n in notifications if n.is_new_message]
                    send_confirmations = [n for n in notifications if n.is_send_success]
                    
                    if new_messages:
                        logger.info(f"Received {len(new_messages)} new message(s)")
                        for msg in new_messages:
                            logger.info(f"  From: {msg.phone_number}")
                    
                    if send_confirmations:
                        logger.info(f"Sent {len(send_confirmations)} message(s) successfully")
                    
                    # Call user callback
                    try:
                        callback(notifications)
                    except Exception as e:
                        logger.error(f"Error in callback: {e}")
                    
                    # Auto-acknowledge if enabled
                    if auto_acknowledge:
                        self.acknowledge_sms_notifications(notifications)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Polling stopped by user")
        except Exception as e:
            logger.error(f"Polling error: {e}")


def main():
    """Example usage of SMS modem client."""
    
    # Configuration
    ROUTER_URL = "http://192.168.1.1"  # Change to your router's IP
    USERNAME = ""  # May be empty for some devices
    PASSWORD = "admin"  # Change to your password
    
    # Initialize client
    client = SmsModemClient(ROUTER_URL, USERNAME, PASSWORD)
    
    # Authenticate
    if not client.authenticate():
        logger.error("Failed to authenticate")
        return
    
    # Define callback for notifications
    def on_sms_notification(notifications: List[SmsNotification]):
        """Handle SMS notifications."""
        for notif in notifications:
            if notif.is_new_message:
                print(f"📨 New SMS from: {notif.phone_number}")
                # Here you could:
                # - Store to database
                # - Forward to email
                # - Trigger other actions
                
            elif notif.is_send_success:
                print(f"✅ SMS sent successfully to: {notif.phone_number}")
    
    # Start polling
    client.poll_sms(on_sms_notification, auto_acknowledge=True)


if __name__ == "__main__":
    main()