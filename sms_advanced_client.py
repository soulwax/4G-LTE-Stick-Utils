#!/usr/bin/env python3
"""
Advanced SMS Modem Client with extended features:
- SMS inbox/outbox reading
- SMS sending
- Device status monitoring
- Network information
"""

import requests
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NetworkType(Enum):
    """Network connection types."""
    NO_SERVICE = "no_service"
    GSM = "gsm"
    GPRS = "gprs"
    EDGE = "edge"
    WCDMA = "wcdma"
    HSDPA = "hsdpa"
    HSUPA = "hsupa"
    HSPA = "hspa"
    HSPA_PLUS = "hspa+"
    DC_HSPA_PLUS = "dc_hspa+"
    LTE = "lte"
    UMTS = "umts"


class SimStatus(Enum):
    """SIM card status."""
    SIM_READY = "sim_ready"
    PIN_ENABLE = "pin_enable"
    PIN_DISABLE = "pin_disable"
    NEED_PIN = "need_pin"
    NEED_PUK = "need_puk"
    PUK_LOCK = "puk_lock"
    NO_SIMCARD = "no_simcard"
    NOT_READY = "not_ready"
    NOT_INVALID = "not_invalid"


@dataclass
class DeviceStatus:
    """Complete device status information."""
    sim_status: str = ""
    pin_attempts_left: int = 0
    puk_attempts_left: int = 0
    operator: str = ""
    roaming: bool = False
    signal_level: int = 0
    network_type: str = ""
    connected: bool = False
    session_sent: int = 0
    session_recv: int = 0
    session_time: int = 0
    wan_ip: str = ""
    wan_netmask: str = ""
    wan_dns: str = ""
    wan_gateway: str = ""
    battery_level: int = 0
    battery_charging: bool = False
    device_time: str = ""
    sms_status: str = ""
    
    @classmethod
    def parse(cls, data_str: str) -> 'DeviceStatus':
        """
        Parse device status from comma-separated string.
        
        Format (index):
        [0]SIM status, [1]PIN count, [2]PUK count,
        [3]Operator, [4]roaming status, [5]signal level,
        [6]Network type, [7]Connection status, [8]Session Send, [9]Session Recv, [10]Session time,
        [11]WAN ip, [12]WAN netmask, [13]WAN DNS, [14]WAN gateway,
        [15]wifinum1, [16]wifinum2,
        [17]battery, [18]current device time, [19]sms status
        """
        parts = data_str.split(',')
        if len(parts) < 20:
            return cls()
        
        return cls(
            sim_status=parts[0],
            pin_attempts_left=int(parts[1]) if parts[1].isdigit() else 0,
            puk_attempts_left=int(parts[2]) if parts[2].isdigit() else 0,
            operator=parts[3],
            roaming=(parts[4] == 'roaming'),
            signal_level=int(parts[5]) if parts[5].isdigit() else 0,
            network_type=parts[6],
            connected=(parts[7] == 'connected'),
            session_sent=int(parts[8]) if parts[8].isdigit() else 0,
            session_recv=int(parts[9]) if parts[9].isdigit() else 0,
            session_time=int(parts[10]) if parts[10].isdigit() else 0,
            wan_ip=parts[11],
            wan_netmask=parts[12],
            wan_dns=parts[13],
            wan_gateway=parts[14],
            battery_level=int(parts[17]) if parts[17].isdigit() else 0,
            device_time=parts[18],
            sms_status=parts[19] if len(parts) > 19 else ""
        )


@dataclass
class SmsMessage:
    """SMS message details."""
    index: int
    phone_number: str
    content: str
    timestamp: str
    read: bool = False
    box_type: str = "inbox"  # inbox, outbox, draft


class AdvancedSmsClient:
    """Extended SMS client with full device interaction."""
    
    def __init__(self, base_url: str, username: str = '', password: str = ''):
        from sms_modem_client import SmsModemClient
        self.client = SmsModemClient(base_url, username, password)
        self.base_url = base_url.rstrip('/')
    
    def authenticate(self) -> bool:
        """Authenticate with router."""
        return self.client.authenticate()
    
    def get_device_status(self) -> Optional[DeviceStatus]:
        """
        Get complete device status including network, SIM, and battery info.
        
        Returns:
            DeviceStatus object or None on error
        """
        try:
            params = {
                'which_ajax': 'ajax_get_wm_wcdma_data',
                'sids': self.client._generate_sids()
            }
            
            url = f"{self.base_url}{self.client.AJAX_GET_ENDPOINT}"
            response = self.client.session.post(url, params=params, timeout=10)
            
            if response.status_code == 200 and response.text:
                return DeviceStatus.parse(response.text)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            return None
    
    def get_ajax_param(self, param_name: str, ajax_type: str = 'database') -> Optional[str]:
        """
        Get a parameter value via AJAX.
        
        Args:
            param_name: Parameter name (e.g., 'wlan_ap0_ssid', 'wm_imsi_tmp_nv')
            ajax_type: Type of AJAX query ('database' or 'tmpdatabase')
            
        Returns:
            Parameter value or None
        """
        try:
            params = {
                'which_ajax': ajax_type,
                'pram': param_name,
                'sids': self.client._generate_sids()
            }
            
            url = f"{self.base_url}{self.client.AJAX_GET_ENDPOINT}"
            response = self.client.session.post(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting parameter {param_name}: {e}")
            return None
    
    def get_wifi_info(self) -> Dict[str, str]:
        """
        Get WiFi configuration info.
        
        Returns:
            Dictionary with WiFi settings
        """
        info = {}
        
        # Get primary WiFi SSID
        ssid = self.get_ajax_param('wlan_ap0_ssid')
        if ssid:
            info['ssid'] = ssid
        
        # Get secondary WiFi SSID (5GHz)
        ssid_5g = self.get_ajax_param('wlan_ap1_ssid')
        if ssid_5g:
            info['ssid_5g'] = ssid_5g
        
        return info
    
    def get_imei(self) -> Optional[str]:
        """Get device IMEI."""
        return self.get_ajax_param('wm_wcdma_imei_nv', 'tmpdatabase')
    
    def get_imsi(self) -> Optional[str]:
        """Get SIM card IMSI."""
        return self.get_ajax_param('wm_imsi_tmp_nv', 'tmpdatabase')
    
    def parse_operator_name(self, raw_data: str) -> str:
        """
        Parse operator name from encoded format.
        
        The operator name may come in formats:
        - Plain text: "Operator Name"
        - Comma-separated char codes: "<1,2,3,...>"
        - UCS-2 hex: "<UCS2hexstring>"
        """
        if not raw_data or '>' not in raw_data:
            return raw_data.split('>')[0] if '>' in raw_data else raw_data
        
        parts = raw_data.split('<')
        if len(parts) < 2:
            return raw_data.split('>')[0]
        
        encoded = parts[1].split(',')
        
        if len(encoded) > 1:
            # Comma-separated character codes
            result = ''
            for code in encoded:
                if code.strip():
                    try:
                        result += chr(int(code))
                    except ValueError:
                        pass
            return result
        
        # UCS-2 hex format
        ucs2_str = parts[1]
        if ucs2_str.startswith('UCS2'):
            ucs2_str = ucs2_str[4:]
        
        result = ''
        for i in range(0, len(ucs2_str), 4):
            try:
                char_code = int(ucs2_str[i:i+4], 16)
                if char_code != 0xFFFF and char_code != 0xFF:
                    result += chr(char_code)
            except (ValueError, OverflowError):
                pass
        
        return result


def monitor_device(client: AdvancedSmsClient, interval: float = 5.0):
    """
    Monitor device status continuously.
    
    Args:
        client: Authenticated AdvancedSmsClient instance
        interval: Polling interval in seconds
    """
    import time
    
    logger.info("Starting device monitoring...")
    
    try:
        while True:
            status = client.get_device_status()
            
            if status:
                print(f"\n{'='*60}")
                print(f"Operator: {status.operator}")
                print(f"Network: {status.network_type.upper()} {'(Connected)' if status.connected else '(Disconnected)'}")
                print(f"Signal: {status.signal_level}/5 bars")
                print(f"Roaming: {'Yes' if status.roaming else 'No'}")
                print(f"SIM: {status.sim_status}")
                print(f"Battery: {status.battery_level}% {'(Charging)' if status.battery_charging else ''}")
                print(f"WAN IP: {status.wan_ip}")
                print(f"Data: ↓{status.session_recv} ↑{status.session_sent} bytes")
                print(f"SMS Status: {status.sms_status}")
                print(f"{'='*60}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped")


def example_usage():
    """Demonstrate advanced client usage."""
    
    # Configuration
    ROUTER_URL = "http://192.168.1.1"
    PASSWORD = "admin"
    
    # Initialize advanced client
    client = AdvancedSmsClient(ROUTER_URL, password=PASSWORD)
    
    if not client.authenticate():
        print("Authentication failed!")
        return
    
    print("✅ Authenticated successfully\n")
    
    # Get device information
    print("📱 Device Information:")
    print(f"   IMEI: {client.get_imei()}")
    print(f"   IMSI: {client.get_imsi()}")
    
    # Get WiFi info
    wifi = client.get_wifi_info()
    print(f"\n📶 WiFi Information:")
    for key, value in wifi.items():
        print(f"   {key}: {value}")
    
    # Get current status
    status = client.get_device_status()
    if status:
        print(f"\n📊 Current Status:")
        print(f"   Operator: {status.operator}")
        print(f"   Network: {status.network_type}")
        print(f"   Signal: {status.signal_level}/5")
        print(f"   Connected: {status.connected}")
    
    # Start monitoring (comment out for non-interactive use)
    # monitor_device(client, interval=10.0)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    example_usage()