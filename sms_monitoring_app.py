#!/usr/bin/env python3
"""
Complete SMS Monitoring Application
Real-world example with logging, database storage, and notifications.
"""

import sqlite3
import logging
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from dataclasses import asdict

# Import our SMS client modules
from sms_modem_client import SmsModemClient, SmsNotification
from sms_advanced_client import AdvancedSmsClient, DeviceStatus


class SmsDatabase:
    """SQLite database for SMS storage."""

    def __init__(self, db_path: str = "sms_data.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Messages table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                message_type TEXT NOT NULL,
                received_at TIMESTAMP NOT NULL,
                acknowledged BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Device status history
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS device_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator TEXT,
                network_type TEXT,
                signal_level INTEGER,
                connected BOOLEAN,
                battery_level INTEGER,
                wan_ip TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def store_message(self, notification: SmsNotification) -> int:
        """Store SMS notification in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        msg_type = "received" if notification.is_new_message else "sent"

        cursor.execute(
            """
            INSERT INTO messages (phone_number, message_type, received_at)
            VALUES (?, ?, ?)
        """,
            (notification.phone_number, msg_type, datetime.now()),
        )

        msg_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return msg_id if msg_id is not None else 0

    def mark_acknowledged(self, msg_id: int):
        """Mark message as acknowledged."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE messages SET acknowledged = 1 WHERE id = ?
        """,
            (msg_id,),
        )

        conn.commit()
        conn.close()

    def store_device_status(self, status: DeviceStatus):
        """Store device status snapshot."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO device_status 
            (operator, network_type, signal_level, connected, battery_level, wan_ip)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                status.operator,
                status.network_type,
                status.signal_level,
                status.connected,
                status.battery_level,
                status.wan_ip,
            ),
        )

        conn.commit()
        conn.close()

    def get_recent_messages(self, limit: int = 10) -> List[dict]:
        """Get recent messages."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM messages 
            ORDER BY received_at DESC 
            LIMIT ?
        """,
            (limit,),
        )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def get_statistics(self) -> dict:
        """Get message statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total messages
        cursor.execute("SELECT COUNT(*) FROM messages")
        total = cursor.fetchone()[0]

        # Received vs sent
        cursor.execute(
            """
            SELECT message_type, COUNT(*) 
            FROM messages 
            GROUP BY message_type
        """
        )
        by_type = dict(cursor.fetchall())

        # Today's messages
        cursor.execute(
            """
            SELECT COUNT(*) FROM messages 
            WHERE DATE(received_at) = DATE('now')
        """
        )
        today = cursor.fetchone()[0]

        conn.close()

        return {
            "total": total,
            "received": by_type.get("received", 0),
            "sent": by_type.get("sent", 0),
            "today": today,
        }


class SmsMonitoringApp:
    """Complete SMS monitoring application."""

    def __init__(self, router_url: str, password: str, username: str = ""):
        self.router_url = router_url
        self.password = password
        self.username = username

        # Initialize components
        self.client = SmsModemClient(router_url, username, password)
        self.advanced_client = AdvancedSmsClient(router_url, username, password)
        self.db = SmsDatabase()

        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        # Status tracking
        self.last_status_check = 0
        self.status_check_interval = 10.0  # Check status every 10 seconds

    def setup_logging(self):
        """Configure logging to file and console."""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # File handler
        file_handler = logging.FileHandler("sms_monitor.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))

        # Root logger
        logging.basicConfig(
            level=logging.DEBUG, handlers=[file_handler, console_handler]
        )

    def connect(self) -> bool:
        """Establish connection to router."""
        self.logger.info(f"Connecting to router at {self.router_url}...")

        if not self.client.authenticate():
            self.logger.error("Authentication failed")
            return False

        if not self.advanced_client.authenticate():
            self.logger.error("Advanced client authentication failed")
            return False

        self.logger.info("✅ Connected successfully")

        # Get and log device info
        imei = self.advanced_client.get_imei()
        imsi = self.advanced_client.get_imsi()

        if imei:
            self.logger.info(f"Device IMEI: {imei}")
        if imsi:
            self.logger.info(f"SIM IMSI: {imsi}")

        return True

    def handle_sms_notifications(self, notifications: List[SmsNotification]):
        """Process SMS notifications."""
        for notif in notifications:
            if notif.is_new_message:
                self.logger.info(f"📨 New SMS from: {notif.phone_number}")

                # Store in database
                msg_id = self.db.store_message(notif)
                self.logger.debug(f"Stored message with ID: {msg_id}")

                # You could add additional actions here:
                # - Send email notification
                # - Trigger webhook
                # - Forward to another service

            elif notif.is_send_success:
                self.logger.info(f"✅ SMS sent successfully to: {notif.phone_number}")
                self.db.store_message(notif)

    def check_device_status(self):
        """Check and log device status."""
        current_time = time.time()

        if (current_time - self.last_status_check) < self.status_check_interval:
            return

        self.last_status_check = current_time

        status = self.advanced_client.get_device_status()

        if status:
            # Store in database
            self.db.store_device_status(status)

            # Log important changes
            if not status.connected:
                self.logger.warning("⚠️ Device disconnected from network")

            if status.signal_level < 2:
                self.logger.warning(f"⚠️ Low signal: {status.signal_level}/5")

            if status.battery_level < 20:
                self.logger.warning(f"⚠️ Low battery: {status.battery_level}%")

            if status.sms_status == "full":
                self.logger.warning("⚠️ SMS storage full!")

    def show_statistics(self):
        """Display message statistics."""
        stats = self.db.get_statistics()

        print("\n" + "=" * 60)
        print("SMS MONITORING STATISTICS")
        print("=" * 60)
        print(f"Total Messages:     {stats['total']}")
        print(f"  Received:         {stats['received']}")
        print(f"  Sent:             {stats['sent']}")
        print(f"Today's Messages:   {stats['today']}")
        print("=" * 60)

        # Recent messages
        recent = self.db.get_recent_messages(5)
        if recent:
            print("\nRecent Messages:")
            for msg in recent:
                print(
                    f"  {msg['received_at']}: {msg['message_type']} - {msg['phone_number']}"
                )
        print()

    def run(self):
        """Main application loop."""
        if not self.connect():
            return

        self.logger.info("Starting SMS monitoring...")

        # Show initial statistics
        self.show_statistics()

        # Start polling with our handler
        try:
            iteration = 0
            while True:
                # Check device status periodically
                self.check_device_status()

                # Poll for SMS
                notifications = self.client.get_sms_notifications()

                if notifications:
                    self.handle_sms_notifications(notifications)
                    self.client.acknowledge_sms_notifications(notifications)

                # Show stats every 100 iterations (~5 minutes at 3s intervals)
                iteration += 1
                if iteration % 100 == 0:
                    self.show_statistics()

                time.sleep(self.client.POLL_INTERVAL)

        except KeyboardInterrupt:
            self.logger.info("\n👋 Shutting down gracefully...")
            self.show_statistics()

        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)


def main():
    """Application entry point."""

    # Configuration - adjust these values
    ROUTER_URL = "http://192.168.1.1"
    PASSWORD = "admin"
    USERNAME = ""

    # Create and run application
    app = SmsMonitoringApp(ROUTER_URL, PASSWORD, USERNAME)
    app.run()


if __name__ == "__main__":
    main()
