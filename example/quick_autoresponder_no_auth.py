#!/usr/bin/env python3
"""
SMS Auto-Responder (No Authentication)
For routers that don't require login - direct API access

Usage:
  python3 sms_autoresponder_noauth.py
"""


# ===== CONFIGURATION - EDIT THIS SECTION =====
ROUTER_URL = "http://192.168.123.254"
RESPONSE_MESSAGE = "2"       # Your auto-response
RESPOND_ONCE = True          # Only respond once per number
POLL_INTERVAL = 3            # Seconds between checks
# ============================================


import requests
import time
import random
import logging
from urllib.parse import quote


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
log = logging.getLogger(__name__)


def gen_id():
    """Generate random session ID."""
    return int(random.random() * 1000000)


def test_connection(session, base_url):
    """Test if router is reachable."""
    try:
        # Try to get any basic info to verify connection
        url = f"{base_url}/cgi-bin/ajax_get.cgi"
        params = {
            'which_ajax': 'tmpdatabase',
            'pram': 'sms_new_msg_notify',
            'sids': gen_id()
        }
        
        r = session.post(url, params=params, timeout=10)
        
        if r.status_code == 200:
            log.info("✅ Router connection established (no auth required)")
            return True
        else:
            log.error(f"❌ Connection failed - status {r.status_code}")
            return False
    except Exception as e:
        log.error(f"❌ Connection error: {e}")
        return False


def get_new_messages(session, base_url):
    """Check for new SMS messages."""
    try:
        url = f"{base_url}/cgi-bin/ajax_get.cgi"
        params = {
            'which_ajax': 'tmpdatabase',
            'pram': 'sms_new_msg_notify',
            'sids': gen_id()
        }
        
        r = session.post(url, params=params, timeout=10)
        
        if r.status_code != 200:
            return []
        
        new_msgs = []
        for entry in r.text.split('>'):
            if entry.strip():
                parts = entry.split(',')
                if len(parts) >= 3 and parts[1] == '0':  # New message (unread)
                    new_msgs.append(parts[0])  # Phone number
        
        return new_msgs
    except Exception as e:
        log.debug(f"Error getting messages: {e}")
        return []


def send_sms(session, base_url, phone, message):
    """Send SMS response using direct API call."""
    # Multiple patterns to try based on common router APIs
    patterns = [
        # Pattern 1: Standard send
        {
            'url': f"{base_url}/cgi-bin/sms.cgi",
            'params': {
                'which_cgi': 'sms_send',
                'phone': phone,
                'message': message,
                'sids': gen_id()
            }
        },
        # Pattern 2: Ajax send
        {
            'url': f"{base_url}/cgi-bin/ajax_get.cgi",
            'params': {
                'which_ajax': 'send_sms',
                'to': phone,
                'content': message,
                'sids': gen_id()
            }
        },
        # Pattern 3: Direct SMS API
        {
            'url': f"{base_url}/cgi-bin/sms.cgi",
            'params': {
                'which_cgi': 'send',
                'number': phone,
                'text': message,
                'sids': gen_id()
            }
        },
        # Pattern 4: Encoded parameters
        {
            'url': f"{base_url}/cgi-bin/sms.cgi",
            'params': {
                'which_cgi': 'sms_send',
                'pram': f"{phone}|{message}",
                'sids': gen_id()
            }
        }
    ]
    
    for i, pattern in enumerate(patterns, 1):
        try:
            # URL-encode all parameter values
            encoded_params = {k: quote(str(v)) if k != 'sids' else str(v) 
                            for k, v in pattern['params'].items()}
            
            r = session.post(pattern['url'], params=encoded_params, timeout=15)
            
            # Check various success indicators
            success_indicators = ['ok', 'success', '1', 'sent', 'true']
            if any(indicator in r.text.lower() for indicator in success_indicators):
                log.debug(f"SMS sent using pattern {i}")
                return True
            
        except Exception as e:
            log.debug(f"Pattern {i} failed: {e}")
            continue
    
    return False


def acknowledge_messages(session, base_url, phones):
    """Mark messages as read."""
    try:
        # Build acknowledgment string
        ack_str = '>'.join([f"{p},1,1" for p in phones]) + '>'
        
        params = {
            'which_cgi': 'ajax_set_tmp_nv',
            'nv': 'sms_new_msg_notify',
            'pram': ack_str,
            'sids': gen_id()
        }
        
        url = f"{base_url}/cgi-bin/sms.cgi"
        session.post(url, params=params, timeout=10)
        
        log.debug(f"Acknowledged {len(phones)} message(s)")
    except Exception as e:
        log.debug(f"Failed to acknowledge messages: {e}")


def keep_alive(session, base_url):
    """Optional keep-alive ping."""
    try:
        session.get(f"{base_url}/cgi-bin/keep_alive.cgi", timeout=5)
    except:
        pass


def main():
    """Main loop."""
    session = requests.Session()
    responded = set()  # Track numbers we've already responded to
    
    log.info("=" * 60)
    log.info("SMS AUTO-RESPONDER (NO AUTHENTICATION)")
    log.info(f"Router: {ROUTER_URL}")
    log.info(f"Response: '{RESPONSE_MESSAGE}'")
    log.info(f"Poll interval: {POLL_INTERVAL}s")
    log.info("=" * 60)
    
    # Test connection
    if not test_connection(session, ROUTER_URL):
        log.error("⛔ Cannot connect to router - check ROUTER_URL")
        return
    
    log.info("🚀 Auto-responder started - monitoring for new SMS...")
    log.info("")
    
    last_keepalive = time.time()
    
    try:
        while True:
            # Optional keep-alive
            if (time.time() - last_keepalive) > 30:
                keep_alive(session, ROUTER_URL)
                last_keepalive = time.time()
            
            # Check for new messages
            new_messages = get_new_messages(session, ROUTER_URL)
            
            if new_messages:
                log.info(f"📨 Received {len(new_messages)} new message(s)")
                
                for phone in new_messages:
                    # Skip if we already responded to this number
                    if RESPOND_ONCE and phone in responded:
                        log.info(f"⏭️  {phone} - already responded, skipping")
                        continue
                    
                    log.info(f"📱 New message from: {phone}")
                    
                    # Send auto-response
                    if send_sms(session, ROUTER_URL, phone, RESPONSE_MESSAGE):
                        log.info(f"✅ Auto-replied to {phone}: '{RESPONSE_MESSAGE}'")
                        responded.add(phone)
                    else:
                        log.warning(f"⚠️  Failed to send response to {phone}")
                    
                    # Small delay between sends
                    time.sleep(1)
                
                # Mark messages as read
                acknowledge_messages(session, ROUTER_URL, new_messages)
                log.info("")
            
            # Wait before next check
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        log.info("")
        log.info("=" * 60)
        log.info("🛑 Auto-responder stopped")
        log.info(f"📊 Total unique numbers responded to: {len(responded)}")
        if responded:
            log.info(f"📋 Numbers: {', '.join(sorted(responded))}")
        log.info("=" * 60)


if __name__ == "__main__":
    main()
