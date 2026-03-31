"""
Streamlined authentication and booking system
Clean, minimal, production-ready code
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from pydantic import BaseModel
from zoneinfo import ZoneInfo

# Load environment
load_dotenv()

# Configuration
class Config:
    BASE_URL = os.getenv("TS_BASE_URL", "https://inforyou.teamsystem.com/ondechiare").rstrip("/")
    COMPANY_ID = int(os.getenv("TS_COMPANY_ID", "2"))
    LOGIN = os.getenv("TS_LOGIN", "")
    PASSWORD = os.getenv("TS_PASSWORD", "")
    IYESURL = os.getenv("TS_IYESURL", "")
    # TEMPORARY: Hardcoded app-token until we find how to generate it
    # Get this from browser DevTools → Cookies → app-token
    APP_TOKEN = os.getenv("TS_APP_TOKEN", "")
    TZ = ZoneInfo(os.getenv("APP_TIMEZONE", "Europe/Rome"))
    COOKIE_FILE = Path(os.getenv("COOKIE_FILE", "./session_cookies.json"))
    TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "15"))
    
    # Weekly schedule: weekday (0=Mon) → class details
    WEEKLY_PLAN = {
        0: {"IDLesson": 11414, "start": "19:40", "end": "08:30", "BookingID": 2598}, # Lunedì
        1: {"IDLesson": 11406, "start": "18:50", "end": "19:40", "BookingID": 80}, # Martedì
        2: {"IDLesson": 11407, "start": "18:50", "end": "19:40", "BookingID": 80}, # Mercoledì
        3: {"IDLesson": 11415, "start": "19:40", "end": "20:30", "BookingID": 2598}, # Giovedì
    }
    SKIP_WEEKDAYS = {4, 5, 6}  # Fri, Sat, Sun

# Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("gym-booker")

# HTTP Session
session = requests.Session()
session.headers.update({
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json; charset=utf-8",
    "Origin": "https://inforyou.teamsystem.com",
    "Referer": f"{Config.BASE_URL}/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
})

# Cookie persistence
def save_cookies():
    """Save session cookies to file"""
    data = [
        {
            "name": c.name,
            "value": c.value,
            "domain": c.domain,
            "path": c.path,
            "secure": c.secure,
        }
        for c in session.cookies
    ]
    Config.COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = Config.COOKIE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(Config.COOKIE_FILE)
    logger.debug(f"Saved {len(data)} cookies")

def load_cookies():
    """Load cookies from file"""
    if not Config.COOKIE_FILE.exists():
        logger.info("No cookie file found, starting fresh")
        return
    
    data = json.loads(Config.COOKIE_FILE.read_text())
    for item in data:
        session.cookies.set(
            name=item["name"],
            value=item["value"],
            domain=item.get("domain"),
            path=item.get("path", "/"),
        )
    logger.info(f"Loaded {len(data)} cookies")

def sync_token_headers():
    """Sync cookies to headers (app-token, auth-token)"""
    for cookie in session.cookies:
        if cookie.name == "app-token":
            session.headers["apptoken"] = cookie.value
        elif cookie.name == "auth-token":
            session.headers["authtoken"] = cookie.value

def is_authenticated() -> bool:
    """Check if we have valid auth-token"""
    sync_token_headers()
    return any(c.name == "auth-token" for c in session.cookies)

def login() -> Dict:
    """
    Perform authentication with IYESUrl header and AppToken
    """
    if not Config.LOGIN or not Config.PASSWORD:
        raise ValueError("TS_LOGIN and TS_PASSWORD must be set")
    
    if not Config.IYESURL:
        raise ValueError("TS_IYESURL must be set in .env")
    
    if not Config.APP_TOKEN:
        raise ValueError("TS_APP_TOKEN must be set in .env (get from browser DevTools)")
    
    logger.info("Attempting login...")
    
    # Step 1: Get initial cookies (lbl, etc.)
    session.get(f"{Config.BASE_URL}/", timeout=Config.TIMEOUT)
    
    # Step 2: Set IYESUrl header (CRITICAL - backend reads this!)
    session.headers["IYESUrl"] = Config.IYESURL
    
    # Step 3: Set AppToken header and cookie
    session.headers["AppToken"] = Config.APP_TOKEN
    session.cookies.set("app-token", Config.APP_TOKEN, domain=".teamsystem.com", path="/")
    session.cookies.set("iyesurl", Config.IYESURL, domain=".teamsystem.com", path="/")
    
    # Step 4: Additional cookies
    session.cookies.set("lang", "en", domain=".teamsystem.com", path="/")
    session.cookies.set("cookie-acceptance", "accepted", domain=".teamsystem.com", path="/")
    
    # Step 5: Authenticate
    url = f"{Config.BASE_URL}/api/v1/security/webauthenticate"
    params = {
        "login": Config.LOGIN,
        "password": Config.PASSWORD,
        "companyid": str(Config.COMPANY_ID),
        "confirmlink": f"{Config.BASE_URL}/account-verification/",
    }
    
    response = session.get(url, params=params, timeout=Config.TIMEOUT)
    
    result = {"status": response.status_code}
    try:
        data = response.json()
        result["response"] = data
        result["successful"] = data.get("Successful", False)
        
        # Extract auth-token from response Item field
        if result["successful"] and data.get("Item"):
            auth_token = data["Item"]
            session.cookies.set("auth-token", auth_token, domain=".teamsystem.com", path="/")
            session.headers["authtoken"] = auth_token
            logger.info("✅ Extracted auth-token from login response")
    except:
        result["response"] = response.text[:200]
        result["successful"] = False
    
    sync_token_headers()
    save_cookies()
    
    result["authenticated"] = is_authenticated()
    
    if result["authenticated"]:
        logger.info("✅ Login successful")
    else:
        logger.error(f"❌ Login failed: {result.get('response', {}).get('ErrorMessage', 'Unknown error')}")
    
    return result
    
    if result["authenticated"]:
        logger.info("✅ Login successful")
    else:
        logger.error(f"❌ Login failed: {result.get('response', {}).get('ErrorMessage', 'Unknown error')}")
    
    return result

def ensure_auth() -> bool:
    """Ensure we're authenticated, login if needed"""
    load_cookies()
    if is_authenticated():
        logger.debug("Already authenticated")
        return True
    
    result = login()
    return result["authenticated"]

def build_booking_payload(now: datetime) -> Tuple[str, Optional[Dict]]:
    """Build booking payload for current weekday"""
    weekday = now.weekday()
    
    if weekday in Config.SKIP_WEEKDAYS or weekday not in Config.WEEKLY_PLAN:
        return "skip", None
    
    spec = Config.WEEKLY_PLAN[weekday]
    if spec["BookingID"] <= 0:
        raise ValueError(f"BookingID not configured for weekday {weekday}")
    
    # Book for next week same day
    target_date = (now + timedelta(days=7)).date()
    
    return "book", {
        "BookingID": spec["BookingID"],
        "IDLesson": spec["IDLesson"],
        "StartTime": f"{target_date}T{spec['start']}:00",
        "EndTime": f"{target_date}T{spec['end']}:00",
        "BookNr": spec.get("BookNr", 1),
        "Type": spec.get("Type", 0),
        "IDDurata": spec.get("IDDurata", 0),
        "Note": spec.get("Note", ""),
    }

def do_booking(payload: Dict) -> Dict:
    """Execute booking request"""
    if not ensure_auth():
        return {"ok": False, "error": "Authentication failed"}
    
    # Ensure IYESUrl header is set (backend needs this for internal requests)
    session.headers["IYESUrl"] = Config.IYESURL
    session.headers["Referer"] = f"{Config.BASE_URL}/planning/{Config.COMPANY_ID}"
    url = f"{Config.BASE_URL}/api/v1/webbooking/book"
    
    logger.info(f"Booking: {payload['IDLesson']} at {payload['StartTime']}")
    logger.debug(f"POST {url}")
    logger.debug(f"Payload: {payload}")
    
    try:
        response = session.post(url, json=payload, timeout=Config.TIMEOUT)
        result = {"ok": False, "status": response.status_code}
        
        try:
            data = response.json()
            result["response"] = data
            result["ok"] = data.get("Successful", False)
            
            if not result["ok"]:
                error_msg = data.get("ErrorMessage") or data.get("Comment") or data.get("Item") or "Unknown error"
                logger.error(f"❌ Booking failed: {error_msg}")
        except:
            result["response"] = response.text[:200]
            logger.error(f"❌ Booking failed (non-JSON response): {response.text[:200]}")
        
        if result["ok"]:
            logger.info("✅ Booking successful")
        
        return result
        
    except Exception as e:
        logger.exception("Booking request failed")
        return {"ok": False, "error": str(e)}

# FastAPI
app = FastAPI(title="Gym Booking Automation", version="2.0")

@app.get("/health")
def health():
    return {
        "ok": True,
        "authenticated": is_authenticated(),
        "config": {
            "base_url": Config.BASE_URL,
            "company_id": Config.COMPANY_ID,
            "timezone": str(Config.TZ),
            "has_iyesurl": bool(Config.IYESURL),
        },
    }

@app.post("/login")
def login_endpoint():
    result = login()
    return {"ok": result["authenticated"], "result": result}

class BookingRequest(BaseModel):
    BookingID: int
    IDLesson: int
    StartTime: str
    EndTime: str
    BookNr: int = 1
    Type: int = 0
    IDDurata: int = 0
    Note: str = ""

@app.post("/book")
def book(req: BookingRequest):
    result = do_booking(req.model_dump())
    return result

@app.post("/run")
def run(simulate_weekday: Optional[int] = Query(None, ge=0, le=6)):
    """Run booking for today (or simulated weekday)"""
    now = datetime.now(Config.TZ)
    
    if simulate_weekday is not None:
        # Simulate a different weekday
        delta = (simulate_weekday - now.weekday()) % 7
        now = now + timedelta(days=delta)
    
    mode, payload = build_booking_payload(now)
    
    if mode == "skip":
        return {
            "ok": True,
            "skipped": True,
            "reason": "No class scheduled for this day",
            "weekday": now.weekday(),
        }
    
    result = do_booking(payload)
    return {
        "ok": result["ok"],
        "skipped": False,
        "weekday": now.weekday(),
        "payload": payload,
        "result": result,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
