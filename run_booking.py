#!/Users/Marco/miniconda3/envs/n8n_env/bin/python

import sys
import time
import logging
import os
import traceback
from pathlib import Path

import requests

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging BEFORE importing app (to override app.py's basicConfig)
log_file = Path(__file__).parent / "gym_booking.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler(sys.stdout)  # Log anche su console
    ],
    force=True  # Force reconfiguration even if already configured
)

from app import build_booking_payload, do_booking, ensure_auth
from datetime import datetime
from app import Config

# Use root logger to capture all messages
logger = logging.getLogger()


def get_raspberry_temperature_c() -> str:
    """Read Raspberry Pi CPU temperature from sysfs when available."""
    thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")
    try:
        if thermal_path.exists():
            raw_value = thermal_path.read_text().strip()
            temp_c = float(raw_value) / 1000.0
            return f"{temp_c:.1f}C"
    except Exception:
        logger.debug("Unable to read Raspberry Pi temperature", exc_info=True)
    return "N/A"


def send_telegram_message(message: str) -> None:
    """Send a Telegram notification if bot token and chat id are configured."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not bot_token or not chat_id:
        logger.info("Telegram not configured: missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
    }

    try:
        response = requests.post(url, json=payload, timeout=Config.TIMEOUT)
        if response.status_code >= 400:
            logger.warning("Telegram send failed with status %s: %s", response.status_code, response.text[:200])
    except Exception:
        logger.warning("Telegram send failed", exc_info=True)


def notify_outcome(status_label: str, now: datetime, slot: str, details: str) -> None:
    """Build and send a standardized Telegram outcome message."""
    temperature = get_raspberry_temperature_c()
    status_map = {
        "SUCCESS": ("✅", "Prenotazione completata"),
        "SKIPPED": ("⏭️", "Nessuna prenotazione prevista oggi"),
        "ALREADY_BOOKED": ("ℹ️", "Lezione gia prenotata"),
        "ERROR": ("❌", "Errore durante esecuzione"),
    }
    status_emoji, status_text = status_map.get(status_label, ("📣", status_label))

    message = (
        "🏋️ Gym Booking Bot - Report\n"
        f"{status_emoji} Esito: {status_text}\n"
        f"🕒 Ora run: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
        f"📅 Slot: {slot}\n"
        f"🌡️ Temperatura Raspberry: {temperature}\n"
        f"📝 Dettagli: {details}"
    )
    send_telegram_message(message)

def main():
    """Execute booking for today"""
    now = datetime.now(Config.TZ)
    
    logger.info("="*60)
    logger.info(f"🚀 SCRIPT STARTED - {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info("="*60)
    logger.info(f"📅 Weekday: {now.strftime('%A')} ({now.weekday()})")
    logger.info(f"📍 Working directory: {Path(__file__).parent}")
    logger.info(f"🔧 Python: {sys.executable}")
    logger.info(f"⏰ Execution time: {now.strftime('%H:%M:%S')}")
    logger.info(f"🆔 Process ID: {os.getpid()}")
    
    # Build payload
    logger.info("")
    logger.info("[STEP 1] Building booking payload...")
    try:
        mode, payload = build_booking_payload(now)
    except Exception as exc:
        error_msg = f"Payload build failed: {exc}"
        logger.exception(error_msg)
        notify_outcome("ERROR", now, "N/A", error_msg)
        logger.info("="*60)
        return 1
    
    if mode == "skip":
        logger.info(f"⏭️  No class scheduled for {now.strftime('%A')}")
        logger.info(f"✓ Script completed successfully (no action needed)")
        notify_outcome("SKIPPED", now, "N/A", "No class scheduled for this weekday")
        logger.info("="*60)
        return 0
    
    slot = f"{payload['StartTime']} -> {payload['EndTime']} (IDLesson={payload['IDLesson']})"

    logger.info(f"✓ Payload created")
    logger.info(f"📋 Target booking: {payload['StartTime']} - {payload['EndTime']}")
    logger.info(f"   IDLesson: {payload['IDLesson']}, BookingID: {payload['BookingID']}")
    
    # Ensure authenticated
    logger.info("")
    logger.info("[STEP 2] Authenticating...")
    if not ensure_auth():
        logger.error("❌ Authentication failed")
        notify_outcome("ERROR", now, slot, "Authentication failed")
        logger.info("="*60)
        return 1
    logger.info("✓ Authentication successful")
    
    # Execute booking with retry logic
    logger.info("")
    logger.info("[STEP 3] Executing booking...")
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            logger.info(f"🔄 Retry attempt {attempt}/{max_retries}...")
            time.sleep(2)  # Wait before retry
        
        result = do_booking(payload)
        
        if result["ok"]:
            logger.info(f"✅ Booking successful! (attempt {attempt})")
            notify_outcome("SUCCESS", now, slot, f"Booking successful on attempt {attempt}")
            logger.info("="*60)
            return 0
        else:
            # Extract error message from response
            response = result.get('response', {})
            error_msg = (
                result.get('error') or 
                response.get('Comment') or 
                response.get('ErrorMessage') or 
                'Unknown error'
            )
            
            # Se è già prenotato, non serve ritentare
            if "doppia" in error_msg.lower() or "già" in error_msg.lower():
                logger.warning(f"⚠️  {error_msg} - No retry needed")
                notify_outcome("ALREADY_BOOKED", now, slot, error_msg)
                logger.info("="*60)
                return 0
            
            logger.error(f"❌ Booking failed (attempt {attempt}): {error_msg}")
            if attempt == max_retries:
                logger.error(f"   HTTP Status: {result.get('status', 'N/A')}")
                logger.error(f"   Full response: {response}")
                notify_outcome(
                    "ERROR",
                    now,
                    slot,
                    f"Booking failed after {max_retries} attempts. System error: {error_msg}",
                )
    
    logger.error("❌ All retry attempts failed")
    logger.info("="*60)
    return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        now = datetime.now(Config.TZ)
        details = f"Unhandled exception: {exc}"
        logger.exception(details)
        tb = traceback.format_exc(limit=5)
        notify_outcome("ERROR", now, "N/A", f"{details}. Traceback: {tb}")
        sys.exit(1)
