# SMS Auto-Responder

Automatically responds with "2" (or any custom message) to every incoming SMS on your router at `http://192.168.123.254`.

## 🚀 Quick Start

### Basic Version

```bash
# Install dependencies
pip install requests

# Run the auto-responder
python3 sms_autoresponder.py
```

That's it! The script will:

1. Authenticate with your router
2. Monitor for incoming SMS messages
3. Automatically reply with "2" to each sender
4. Track which numbers it has responded to

### Enhanced Version

```bash
# Copy configuration file
cp config_example.py config.py

# Edit config.py with your settings
nano config.py

# Run enhanced version
python3 sms_autoresponder_enhanced.py
```

## 📋 Features

### Basic Auto-Responder (`sms_autoresponder.py`)

✅ **Simple & Reliable**

- Automatic "2" response to all incoming SMS
- Prevents duplicate responses to same number
- Session management with auto-reconnect
- Detailed logging
- Multiple retry patterns for SMS sending

### Enhanced Auto-Responder (`sms_autoresponder_enhanced.py`)

✅ **All basic features plus:**

- **Configuration file** - Easy customization
- **Database logging** - SQLite storage of all responses
- **Whitelist/Blacklist** - Control who gets responses
- **Retry logic** - Multiple attempts if sending fails
- **Statistics** - Track success/failure rates
- **Notifications** - Desktop & email alerts (optional)
- **Random delays** - More natural response timing

## ⚙️ Configuration

### Basic Configuration

Edit the top of `sms_autoresponder.py`:

```python
ROUTER_URL = "http://192.168.123.254"
PASSWORD = "admin"  # Change to your router password
USERNAME = ""       # Usually empty
```

### Enhanced Configuration

Edit `config.py` (copy from `config_example.py`):

```python
# Router Settings
ROUTER_URL = "http://192.168.123.254"
PASSWORD = "your_password_here"

# Response Settings
RESPONSE_MESSAGE = "2"  # Your auto-response
RESPOND_ONCE_PER_NUMBER = True  # Prevent spam

# Optional: Whitelist (only these numbers)
WHITELIST = ["+1234567890", "+9876543210"]

# Optional: Blacklist (never these numbers)
BLACKLIST = ["+spam123456"]

# Timing
MIN_DELAY_BETWEEN_RESPONSES = 1.0  # seconds
MAX_DELAY_BETWEEN_RESPONSES = 2.0  # seconds
POLL_INTERVAL = 3.0  # Check for new messages every 3s

# Retry Settings
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 5.0

# Database
SAVE_TO_DATABASE = True
DATABASE_FILE = "sms_responses.db"
```

## 📊 How It Works

```r
┌─────────────────────────────────────────────────────────┐
│  1. SMS arrives → Router stores notification            │
│  2. Script polls every 3 seconds                        │
│  3. Detects new message from +1234567890               │
│  4. Checks: Not in blacklist? Not responded before?    │
│  5. Sends "2" to +1234567890                           │
│  6. Logs response in database                           │
│  7. Marks message as acknowledged                       │
└─────────────────────────────────────────────────────────┘
```

### API Flow

1. **Authentication**

   ```r
   POST /cgi-bin/ajax_get.cgi?which_ajax=check_password&pram=admin&...
   → Response: "1" (success)
   ```

2. **Poll for messages** (every 3 seconds)

   ```r
   POST /cgi-bin/ajax_get.cgi?which_ajax=tmpdatabase&pram=sms_new_msg_notify
   → Response: "+1234567890,0,1>+9876543210,0,1>"
   ```

3. **Send auto-response**

   ```r
   POST /cgi-bin/sms.cgi?which_cgi=sms_send&phone=+1234567890&message=2
   → Response: "ok" or "success"
   ```

4. **Acknowledge** (mark as read)

   ```r
   POST /cgi-bin/sms.cgi?which_cgi=ajax_set_tmp_nv&nv=sms_new_msg_notify&pram=...
   ```

5. **Keep session alive** (every 3 seconds)

   ```r
   POST /cgi-bin/keep_alive.cgi
   ```

## 🔧 Usage Examples

### Example 1: Basic Auto-Responder

```python
from sms_autoresponder import SmsAutoResponder

# Initialize
responder = SmsAutoResponder(
    base_url="http://192.168.123.254",
    password="admin"
)

# Authenticate and run
if responder.authenticate():
    responder.run(respond_once=True)
```

### Example 2: Custom Response Message

```python
responder = SmsAutoResponder(
    base_url="http://192.168.123.254",
    password="admin"
)

# Change response message
responder.RESPONSE_MESSAGE = "Thank you for your message!"

if responder.authenticate():
    responder.run()
```

### Example 3: Respond Multiple Times

```python
# Allow multiple responses to same number
if responder.authenticate():
    responder.run(respond_once=False)  # Will respond every time
```

### Example 4: Enhanced with Whitelist

Create `config.py`:

```python
ROUTER_URL = "http://192.168.123.254"
PASSWORD = "admin"
RESPONSE_MESSAGE = "2"

# Only respond to these numbers
WHITELIST = [
    "+1234567890",
    "+9876543210"
]
```

Run:

```bash
python3 sms_autoresponder_enhanced.py
```

### Example 5: View Statistics

```python
from sms_autoresponder_enhanced import ResponseDatabase

db = ResponseDatabase("sms_responses.db")
stats = db.get_stats()

print(f"Total responses: {stats['total']}")
print(f"Successful: {stats['successful']}")
print(f"Failed: {stats['failed']}")
print(f"Unique numbers: {stats['unique_numbers']}")
```

## 📁 Files Overview

```sh
sms_autoresponder.py          # Basic auto-responder (recommended for simple use)
sms_autoresponder_enhanced.py # Advanced with config & database
config_example.py              # Configuration template
config.py                      # Your custom config (create this)
sms_responses.db              # SQLite database (auto-created)
autoresponder.log             # Log file (auto-created)
```

## 🔍 Monitoring & Logging

### Console Output

```sh
2025-11-09 20:00:00 - INFO - Authenticating to http://192.168.123.254...
2025-11-09 20:00:00 - INFO - ✅ Authentication successful
2025-11-09 20:00:00 - INFO - ================================================================
2025-11-09 20:00:00 - INFO - SMS AUTO-RESPONDER ACTIVE
2025-11-09 20:00:00 - INFO - Will respond with: '2'
2025-11-09 20:00:00 - INFO - ================================================================
2025-11-09 20:00:15 - INFO - 📨 Received 1 new message(s)
2025-11-09 20:00:15 - INFO - 📱 New message from: +1234567890
2025-11-09 20:00:16 - INFO - 📤 SMS sent successfully to +1234567890
2025-11-09 20:00:16 - INFO - ✅ Auto-responded to +1234567890
```

### Log File

All activity is logged to `autoresponder.log`:

```sh
2025-11-09 20:00:00 - INFO - Authentication successful
2025-11-09 20:00:15 - INFO - New message from: +1234567890
2025-11-09 20:00:16 - INFO - Auto-responded to +1234567890
2025-11-09 20:00:30 - INFO - New message from: +9876543210
2025-11-09 20:00:30 - INFO - ⏭️  Skipping +9876543210 (already responded)
```

### Database Queries

```bash
# View all responses
sqlite3 sms_responses.db "SELECT * FROM responses ORDER BY sent_at DESC LIMIT 10;"

# Count successful responses
sqlite3 sms_responses.db "SELECT COUNT(*) FROM responses WHERE success = 1;"

# List unique numbers responded to
sqlite3 sms_responses.db "SELECT DISTINCT phone_number FROM responses;"

# Get response rate
sqlite3 sms_responses.db "SELECT 
    COUNT(*) as total,
    SUM(success) as successful,
    ROUND(100.0 * SUM(success) / COUNT(*), 2) as success_rate
FROM responses;"
```

## 🛠️ Troubleshooting

### Problem: Authentication fails

**Solution:**

```bash
# 1. Check router is accessible
ping 192.168.123.254

# 2. Try accessing web interface
curl http://192.168.123.254/home.html

# 3. Verify password in config
# Edit config.py or script
PASSWORD = "your_correct_password"
```

### Problem: SMS not sending

**Possible causes:**

1. **Router doesn't support SMS sending API**
   - Check router model documentation
   - Try accessing SMS interface manually via web

2. **Network/SIM issues**
   - Check SIM card is inserted and active
   - Verify network connection in web interface

3. **API endpoint different**
   - Script tries multiple patterns automatically
   - Check logs for actual API responses

**Debug:**

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Then run script - you'll see all API calls
```

### Problem: Responding multiple times to same number

**Solution:**

```python
# Make sure respond_once is True
responder.run(respond_once=True)

# Or in config.py
RESPOND_ONCE_PER_NUMBER = True
```

### Problem: Session expires

**Solution:**

- Script automatically handles this
- If issues persist, reduce POLL_INTERVAL:

```python
POLL_INTERVAL = 2.0  # Check more frequently
```

## 🔒 Security Considerations

⚠️ **Important:**

- Router uses HTTP (not HTTPS) - credentials sent in cleartext
- Only run on trusted/private networks
- Change default password immediately
- Don't expose router admin interface to internet

**Best practices:**

```python
# 1. Use strong password
PASSWORD = "veryStrongP@ssw0rd123!"

# 2. Use whitelist for sensitive applications
WHITELIST = ["+trusted_number"]

# 3. Monitor logs regularly
tail -f autoresponder.log

# 4. Backup database periodically
cp sms_responses.db sms_responses_backup_$(date +%Y%m%d).db
```

## 📊 Statistics & Reporting

### View Stats During Runtime

Press `Ctrl+C` to stop gracefully and see stats:

```r
============================================================
Auto-responder stopped
Total numbers responded to: 5
Responded to:
  • +1234567890
  • +2345678901
  • +3456789012
  • +4567890123
  • +5678901234
============================================================
```

### Enhanced Stats (with database)

```python
from sms_autoresponder_enhanced import ResponseDatabase

db = ResponseDatabase()
stats = db.get_stats()

print("📊 Response Statistics:")
print(f"   Total attempts: {stats['total']}")
print(f"   ✅ Successful: {stats['successful']}")
print(f"   ❌ Failed: {stats['failed']}")
print(f"   📱 Unique numbers: {stats['unique_numbers']}")
print(f"   📈 Success rate: {stats['successful']/stats['total']*100:.1f}%")
```

## 🚀 Running as Service

### Linux (systemd)

Create `/etc/systemd/system/sms-autoresponder.service`:

```ini
[Unit]
Description=SMS Auto-Responder
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/autoresponder
ExecStart=/usr/bin/python3 /path/to/sms_autoresponder.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sms-autoresponder
sudo systemctl start sms-autoresponder
sudo systemctl status sms-autoresponder
```

### Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY sms_autoresponder.py .
RUN pip install requests

CMD ["python3", "sms_autoresponder.py"]
```

Run:

```bash
docker build -t sms-autoresponder .
docker run -d --name sms-responder sms-autoresponder
docker logs -f sms-responder
```

## 🎯 Use Cases

1. **Customer Service** - Auto-acknowledge support requests
2. **Voting Systems** - Confirm vote receipt with "2"
3. **Subscription Confirmations** - Automatic opt-in responses
4. **Event RSVPs** - Confirm attendance
5. **Survey Participation** - Initial engagement response

## ⚠️ Important Notes

1. **SMS Sending API** - The router's exact SMS sending API may vary by firmware version
2. **Script tries multiple patterns** automatically to find the right one
3. **First run** - May take a few attempts to find working API pattern
4. **Test first** - Send yourself a test SMS to verify it works
5. **Monitor logs** - Check for any errors or issues

## 📝 License

Provided as-is for educational and personal use.

## 🤝 Support

If you encounter issues:

1. Check logs: `tail -f autoresponder.log`
2. Enable debug mode in script
3. Verify router web interface works manually
4. Check SIM card and network status
