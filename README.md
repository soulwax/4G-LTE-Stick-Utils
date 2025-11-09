# SMS Modem Router Client

Python implementation for interacting with XSBox/4G Systems LTE modem routers for SMS operations and device monitoring.

## 🎯 Features

- ✅ **Authentication & Session Management** - Automatic login and session keep-alive
- 📱 **SMS Polling** - Real-time monitoring for incoming messages
- 📊 **Device Status** - Network, signal, battery, and connection info
- 🔄 **Auto-acknowledgment** - Automatic message read receipts
- 🛡️ **Error Handling** - Robust reconnection and error recovery
- 📝 **Production Ready** - Clean, maintainable code following best practices

## 📋 Requirements

```bash
pip install requests
```

Python 3.7+ required

## 🚀 Quick Start

### Basic SMS Monitoring

```python
from sms_modem_client import SmsModemClient, SmsNotification
from typing import List

# Initialize client
client = SmsModemClient(
    base_url="http://192.168.1.1",
    username="",  # Often empty
    password="admin"
)

# Authenticate
if not client.authenticate():
    print("Authentication failed!")
    exit(1)

# Define callback
def handle_sms(notifications: List[SmsNotification]):
    for notif in notifications:
        if notif.is_new_message:
            print(f"📨 New SMS from: {notif.phone_number}")
        elif notif.is_send_success:
            print(f"✅ SMS sent to: {notif.phone_number}")

# Start polling (runs forever)
client.poll_sms(handle_sms, auto_acknowledge=True)
```

### Device Status Monitoring

```python
from sms_advanced_client import AdvancedSmsClient

client = AdvancedSmsClient(
    base_url="http://192.168.1.1",
    password="admin"
)

if client.authenticate():
    # Get device info
    print(f"IMEI: {client.get_imei()}")
    print(f"IMSI: {client.get_imsi()}")
    
    # Get current status
    status = client.get_device_status()
    if status:
        print(f"Operator: {status.operator}")
        print(f"Network: {status.network_type}")
        print(f"Signal: {status.signal_level}/5 bars")
        print(f"Battery: {status.battery_level}%")
        print(f"Connected: {status.connected}")
```

## 📚 Documentation

### Core Classes

#### `SmsModemClient`

Primary client for SMS operations.

**Methods:**

- `authenticate()` - Login to router
- `keep_alive()` - Maintain session
- `get_sms_notifications()` - Fetch SMS notifications
- `acknowledge_sms_notifications(notifications)` - Mark as read
- `poll_sms(callback, auto_acknowledge=True, interval=3.0)` - Continuous polling

#### `AdvancedSmsClient`

Extended client with device information.

**Methods:**

- `get_device_status()` - Complete status (network, battery, etc.)
- `get_imei()` - Device IMEI
- `get_imsi()` - SIM IMSI
- `get_wifi_info()` - WiFi configuration
- `get_ajax_param(param_name, ajax_type)` - Generic parameter retrieval

#### `SmsNotification`

SMS notification data structure.

**Attributes:**

- `phone_number` (str) - Sender/recipient phone number
- `is_new_message` (bool) - True if new incoming SMS
- `is_send_success` (bool) - True if outgoing SMS sent successfully

#### `DeviceStatus`

Complete device status information.

**Attributes:**

- `sim_status` - SIM card state
- `operator` - Network operator name
- `signal_level` - Signal strength (0-5)
- `network_type` - Connection type (gsm/3g/lte/etc.)
- `connected` - Connection state
- `battery_level` - Battery percentage
- `wan_ip` - WAN IP address
- And more...

## 🔧 Configuration

### Common Router Addresses

- `192.168.1.1` (most common)
- `192.168.8.1` (alternative)

### Default Credentials

- Username: `` (empty) or `admin`
- Password: `admin`

### Customization

```python
client = SmsModemClient(
    base_url="http://192.168.1.1",
    username="",
    password="admin"
)

# Custom polling interval
client.poll_sms(callback, interval=5.0)  # 5 seconds

# Manual acknowledgment
client.poll_sms(callback, auto_acknowledge=False)

# Custom keep-alive interval
client.KEEP_ALIVE_INTERVAL = 5.0
```

## 📖 Examples

### Example 1: SMS Logger to File

```python
import json
from datetime import datetime
from sms_modem_client import SmsModemClient

def log_sms(notifications):
    for notif in notifications:
        if notif.is_new_message:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "from": notif.phone_number,
                "type": "received"
            }
            
            with open("sms_log.jsonl", "a") as f:
                f.write(json.dumps(entry) + "\n")

client = SmsModemClient("http://192.168.1.1", password="admin")
client.authenticate()
client.poll_sms(log_sms)
```

### Example 2: SMS to Email Forward

```python
import smtplib
from email.message import EmailMessage

def forward_to_email(notifications):
    for notif in notifications:
        if notif.is_new_message:
            msg = EmailMessage()
            msg['Subject'] = f'New SMS from {notif.phone_number}'
            msg['From'] = 'router@example.com'
            msg['To'] = 'you@example.com'
            msg.set_content(f'Received SMS from {notif.phone_number}')
            
            with smtplib.SMTP('localhost') as smtp:
                smtp.send_message(msg)

client = SmsModemClient("http://192.168.1.1", password="admin")
client.authenticate()
client.poll_sms(forward_to_email)
```

### Example 3: Webhook Integration

```python
import requests

def webhook_notify(notifications):
    for notif in notifications:
        if notif.is_new_message:
            requests.post('https://your-webhook.com/sms', json={
                'phone': notif.phone_number,
                'timestamp': datetime.now().isoformat(),
                'event': 'new_sms'
            })

client = SmsModemClient("http://192.168.1.1", password="admin")
client.authenticate()
client.poll_sms(webhook_notify)
```

### Example 4: Database Storage

```python
import sqlite3

def store_in_db(notifications):
    conn = sqlite3.connect('sms.db')
    cursor = conn.cursor()
    
    for notif in notifications:
        if notif.is_new_message:
            cursor.execute(
                'INSERT INTO messages (phone, received_at) VALUES (?, ?)',
                (notif.phone_number, datetime.now())
            )
    
    conn.commit()
    conn.close()

client = SmsModemClient("http://192.168.1.1", password="admin")
client.authenticate()
client.poll_sms(store_in_db)
```

### Example 5: Device Monitoring Dashboard

```python
from sms_advanced_client import AdvancedSmsClient
import time

client = AdvancedSmsClient("http://192.168.1.1", password="admin")
client.authenticate()

while True:
    status = client.get_device_status()
    
    print(f"\033[2J\033[H")  # Clear screen
    print("=" * 60)
    print(f"Operator: {status.operator}")
    print(f"Network: {status.network_type.upper()}")
    print(f"Signal: {'█' * status.signal_level}{'░' * (5-status.signal_level)} {status.signal_level}/5")
    print(f"Battery: {status.battery_level}%")
    print(f"Data: ↓ {status.session_recv} ↑ {status.session_sent} bytes")
    print(f"Status: {'🟢 Connected' if status.connected else '🔴 Disconnected'}")
    print("=" * 60)
    
    time.sleep(5)
```

## 🔒 Security Notes

⚠️ **Important Security Considerations:**

1. **No HTTPS:** Router uses HTTP - credentials sent in cleartext
2. **Local Network Only:** Use on trusted/private networks
3. **Change Default Password:** Immediately change from `admin`
4. **Firewall:** Don't expose router admin interface to internet
5. **Session Cookies:** Can be hijacked on shared networks

**Best Practices:**

- Use VPN for remote access
- Restrict admin access to specific IP addresses
- Monitor for unauthorized access
- Regular password changes

## 🐛 Troubleshooting

### Authentication Fails

```python
# Check credentials
client = SmsModemClient("http://192.168.1.1", password="admin")
if not client.authenticate():
    print("Check: password, network connection, router IP")
```

### No SMS Notifications

```python
# Verify device status
status = client.get_device_status()
print(f"SIM Status: {status.sim_status}")  # Should be "sim_ready"
print(f"SMS Status: {status.sms_status}")  # Check if full
```

### Session Expires

```python
# Increase keep-alive frequency
client.KEEP_ALIVE_INTERVAL = 2.0  # More frequent
```

### Connection Lost

```python
# Add reconnection logic
def poll_with_reconnect():
    while True:
        try:
            client.poll_sms(callback)
        except Exception as e:
            print(f"Error: {e}, reconnecting...")
            time.sleep(5)
            if client.authenticate():
                continue
            else:
                break
```

## 📊 API Endpoints Reference

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete API details.

**Key Endpoints:**

- `/cgi-bin/ajax_get.cgi?which_ajax=check_password` - Authentication
- `/cgi-bin/ajax_get.cgi?which_ajax=tmpdatabase&pram=sms_new_msg_notify` - SMS polling
- `/cgi-bin/sms.cgi?which_cgi=ajax_set_tmp_nv` - SMS acknowledgment
- `/cgi-bin/ajax_get.cgi?which_ajax=ajax_get_wm_wcdma_data` - Device status
- `/cgi-bin/keep_alive.cgi` - Session maintenance

## 🤝 Contributing

Contributions welcome! Key areas:

- SMS sending functionality
- SMS inbox/outbox reading
- Enhanced error handling
- Additional device models

## 📝 License

This code is provided as-is for educational and personal use.

## ⚙️ System Requirements

- Python 3.7+
- `requests` library
- Network access to router
- Compatible router model (XSBox/4G Systems LTE series)

## 🔍 Supported Devices

Tested on:

- XSBox Go+ LTE150.2
- 4G Systems LTE routers
- Similar router models with same CGI interface

## 📞 Support

For issues and questions:

1. Check [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
2. Review examples in this README
3. Verify router compatibility

---

**Note:** This implementation is based on reverse-engineering the web interface and may not work with all firmware versions or router models. Always test in a controlled environment first.
