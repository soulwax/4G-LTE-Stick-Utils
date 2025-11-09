# SMS Modem Router API Documentation

## System Overview

This router (XSBox Go+ LTE150.2 / 4G Systems) uses a CGI-based API for all operations. The web interface communicates via AJAX requests to various CGI endpoints.

## Authentication & Session Management

### Authentication Flow

1. **Check Password**

   ```r
   POST /cgi-bin/ajax_get.cgi?which_ajax=check_password&pram={password}&username={username}&sids={random_id}
   ```

   - **Parameters:**
     - `which_ajax`: `check_password`
     - `pram`: URL-encoded password
     - `username`: URL-encoded username (may be empty)
     - `sids`: Random 6-digit session ID (0-999999)

   - **Response:**
     - `1`: Success
     - `0` or `-1`: Failed

   - **Notes:** Session cookies are set upon successful authentication

2. **Session Management**

   ```r
   POST /cgi-bin/ajax_session?sid={session_id}
   ```

   - Validates session
   - Use `sid=logout` to terminate session

3. **Keep Alive**

   ```r
   POST /cgi-bin/keep_alive.cgi
   ```

   - **Purpose:** Maintain active session
   - **Frequency:** Every 3 seconds
   - **Response:** Returns session validity status

---

## SMS Operations

### 1. Poll for New SMS Notifications

**Endpoint:**

```r
POST /cgi-bin/ajax_get.cgi?which_ajax=tmpdatabase&pram=sms_new_msg_notify&sids={random_id}
```

**Purpose:** Get notifications for received SMS and sent SMS confirmations

**Response Format:**

```r
phone_number1,notification_flag,send_flag>phone_number2,notification_flag,send_flag>...
```

**Flag Values:**

- `notification_flag`:
  - `0`: New unread message
  - `1`: Message has been read/acknowledged
  
- `send_flag`:
  - `0`: SMS sent successfully (needs acknowledgment)
  - `1`: Send notification acknowledged

**Example Response:**

```r
+1234567890,0,1>+0987654321,1,0>
```

This indicates:

- One new message from +1234567890
- One successfully sent message to +0987654321

**Polling:**

- Recommended interval: 3 seconds
- Includes random `sids` parameter for cache-busting

### 2. Acknowledge SMS Notifications

**Endpoint:**

```r
POST /cgi-bin/sms.cgi?which_cgi=ajax_set_tmp_nv&nv=sms_new_msg_notify&pram={data}&sids={random_id}
```

**Purpose:** Mark messages as read or acknowledge sent notifications

**Parameters:**

- `which_cgi`: `ajax_set_tmp_nv`
- `nv`: `sms_new_msg_notify`
- `pram`: Updated notification string with modified flags
- `sids`: Random session ID

**Data Format:**
Same as response format, but with updated flags:

```r
phone_number,1,0>phone_number,0,1>
```

**Example Flow:**

1. Receive notification: `+1234567890,0,1>`
2. Mark as read: `+1234567890,1,1>`

---

## Device Status & Information

### Get Complete Device Status

**Endpoint:**

```r
POST /cgi-bin/ajax_get.cgi?which_ajax=ajax_get_wm_wcdma_data&sids={random_id}
```

**Response Format:** Comma-separated values

```plaintext
[0]  SIM status (sim_ready, need_pin, no_simcard, etc.)
[1]  PIN attempts remaining
[2]  PUK attempts remaining
[3]  Operator name
[4]  Roaming status (home/roaming)
[5]  Signal level (0-5)
[6]  Network type (gsm/gprs/edge/3g/lte/no_service)
[7]  Connection status (connected/disconnected)
[8]  Session data sent (bytes)
[9]  Session data received (bytes)
[10] Session duration (seconds)
[11] WAN IP address
[12] WAN netmask
[13] WAN DNS
[14] WAN gateway
[15] WiFi clients count (2.4GHz)
[16] WiFi clients count (5GHz)
[17] Battery level/status
[18] Device time (YY-MM-DD HH:MM:SS)
[19] SMS status (none/unread/full)
[20] IP family type
[21] IPv6 address
[22] IPv6 DNS
[23] IPv6 gateway
[24] FOTA update available (0/1)
```

**Network Types:**

- `no_service`: No network
- `gsm`: 2G GSM
- `gprs`: 2G GPRS
- `edge`: 2.5G EDGE
- `wcdma/umts`: 3G
- `hsdpa/hsupa/hspa`: 3G+
- `hspa+`: Enhanced 3G
- `dc_hspa+`: Dual-carrier 3G
- `lte`: 4G LTE

### Get Generic Parameters

**Endpoint:**

```r
POST /cgi-bin/ajax_get.cgi?which_ajax={type}&pram={parameter}&sids={random_id}
```

**Types:**

- `database`: Persistent configuration
- `tmpdatabase`: Runtime/temporary values

**Common Parameters:**

- `wlan_ap0_ssid`: Primary WiFi SSID
- `wlan_ap1_ssid`: Secondary WiFi SSID (5GHz)
- `wm_wcdma_imei_nv`: Device IMEI
- `wm_imsi_tmp_nv`: SIM IMSI

---

## Operator Name Encoding

The system supports three operator name formats:

### 1. Plain Text

```r
Vodafone
```

### 2. Comma-Separated Character Codes

```r
<86,111,100,97,102,111,110,101>
```

Decode: Convert each number to ASCII character

### 3. UCS-2 Hexadecimal

```r
<UCS20056006F006400610066006F006E0065>
```

Decode: Parse 4-character hex chunks as Unicode codepoints

- Skip `0xFFFF` and `0xFF` (padding)

---

## Request Parameters

### Session ID Generation

```python
import random
sids = int(random.random() * 1000000)  # 0-999999
```

### URL Encoding

- Use proper URL encoding for special characters in parameters
- Username and password must be escaped

---

## Typical Usage Flow

### 1. Initial Setup

```r
1. POST /cgi-bin/ajax_get.cgi (check_password)
2. Receive session cookies
3. Start keep-alive loop (every 3s)
```

### 2. SMS Polling Loop

```r
Every 3 seconds:
1. POST /cgi-bin/ajax_get.cgi (sms_new_msg_notify)
2. Parse response for new messages
3. Process notifications
4. POST /cgi-bin/sms.cgi (acknowledge)
```

### 3. Status Monitoring

```r
Every 3-10 seconds:
1. POST /cgi-bin/ajax_get.cgi (ajax_get_wm_wcdma_data)
2. Parse device status
3. Update UI/logs
```

---

## Error Handling

### Session Expiry

- Keep-alive returns error
- Authentication returns `0`
- Re-authenticate required

### Connection Loss

- Multiple failed requests (>10)
- Display connection lost message
- Stop all AJAX polling

### SMS Storage Full

- Status field shows: `sms_status = "full"`
- Clear old messages to receive new ones

---

## Security Considerations

1. **No HTTPS:** Router typically uses HTTP only
2. **Session Hijacking:** Cookie-based sessions vulnerable on shared networks
3. **CSRF Protection:** Minimal or absent
4. **Password Storage:** Transmitted in cleartext over HTTP

**Recommendations:**

- Use on trusted/private networks only
- Change default password
- Consider VPN if remote access needed

---

## Advanced Features

### Battery Status Parsing

```r
battery_value format: "{type}_{level}"
Types: ac, usb, full, err
Level: 0-100 (percentage)
```

### Signal Strength

- Values: 0-5 (bars)
- 0 = No signal
- 5 = Maximum signal

### Connection Time

- In seconds since connection established
- Resets on disconnect/reconnect

---

## Code Examples

### Python - Basic SMS Polling

```python
import requests
import time

session = requests.Session()
base_url = "http://192.168.1.1"

# Authenticate
response = session.post(
    f"{base_url}/cgi-bin/ajax_get.cgi",
    params={
        'which_ajax': 'check_password',
        'pram': 'admin',
        'username': '',
        'sids': 123456
    }
)

# Poll for SMS
while True:
    response = session.post(
        f"{base_url}/cgi-bin/ajax_get.cgi",
        params={
            'which_ajax': 'tmpdatabase',
            'pram': 'sms_new_msg_notify',
            'sids': int(time.time() * 1000000) % 1000000
        }
    )
    
    for entry in response.text.split('>'):
        if entry:
            phone, notif, send = entry.split(',')
            if notif == '0':
                print(f"New SMS from: {phone}")
    
    time.sleep(3)
```

### Bash/cURL - Get Device Status

```bash
#!/bin/bash
ROUTER="http://192.168.1.1"
SIDS=$((RANDOM % 1000000))

# Get status
curl -X POST "$ROUTER/cgi-bin/ajax_get.cgi?which_ajax=ajax_get_wm_wcdma_data&sids=$SIDS"
```

---

## Limitations

1. **No Direct SMS Read:** API only provides notifications, not message content
2. **No Bulk Operations:** Single message operations only
3. **Limited Error Info:** Responses are minimal (success/fail)
4. **No SMS Sending via API:** Notification system only tracks status
5. **Session Management:** Manual keep-alive required

---

## Troubleshooting

### Issue: Not Receiving Notifications

- Check authentication status
- Verify keep-alive is running
- Ensure SMS notifications are enabled on device
- Check SIM card status

### Issue: Session Expires Quickly

- Increase keep-alive frequency
- Check for concurrent logins
- Verify network stability

### Issue: Cannot Parse Operator Name

- Use all three decoding methods
- Check for mixed encoding formats
- Fallback to raw string

---

## Additional Resources

- Device typically accessible at: `192.168.1.1` or `192.168.8.1`
- Default credentials often: `admin` / `admin`
- Web interface: `http://192.168.1.1/home.html`
