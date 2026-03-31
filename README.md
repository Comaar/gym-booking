# Gym Booking Automation

Automated booking service for recurring gym classes. The application runs on a fixed schedule, applies booking rules from configuration, and submits booking requests with built-in retry and logging.

## Executive Summary

This project removes manual daily booking activity by running a deterministic booking workflow:

1. Trigger once per day at a configured time.
2. Evaluate booking policy for the current weekday.
3. Build and submit a request for the next eligible class.
4. Record outcomes for operational traceability.

The design favors reliability, low operational overhead, and straightforward maintenance.

## Core Capabilities

- Scheduled unattended execution (`cron` or `launchd`)
- Configuration-driven weekly planning and skip-day rules
- Token/session-based authentication handling
- Bounded retries for transient API/network failures
- Timezone-aware scheduling (default: `Europe/Rome`)
- Persistent structured logging for diagnostics

## System Design

### Component Responsibilities

- `run_booking.py`: Orchestrates a single booking cycle (entry point from scheduler).
- `app.py`: Contains domain logic (policy checks, payload creation, auth and booking calls, retry policy).
- `check_schedule.py`: Read-only utility to validate what will be booked.
- `com.marco.gymbooking.plist`: macOS scheduler definition (`launchd`).
- `.env` and `.env.example`: Runtime configuration and credential contract.

### Runtime Sequence

1. Scheduler invokes `run_booking.py`.
2. Application resolves local time and weekday.
3. Policy layer checks if booking is allowed for that day.
4. Integration layer prepares and sends booking request.
5. Retry handler executes bounded retries when applicable.
6. Logger persists success/failure details and run metadata.

### Reliability and Control Strategy

- Deterministic execution window to avoid missed/duplicate runs.
- Explicit policy gate (`WEEKLY_PLAN` + skip days) before outbound requests.
- Retry-on-transient-failure only, with controlled attempt limits.
- Local session persistence to reduce unnecessary re-authentication.

## Repository Layout

```text
.
├── app.py
├── run_booking.py
├── check_schedule.py
├── com.marco.gymbooking.plist
├── requirements.txt
├── .env.example
└── README.md
```

## Installation and Configuration

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Create `.env` from `.env.example` and provide required values.

### 3. Configure booking policy

Update `WEEKLY_PLAN` and skip-day settings in `app.py` to match your schedule.

## Scheduler Configuration

### Example: Raspberry Pi with cron

```bash
crontab -e
```

```cron
1 0 * * 1-4 sleep $(shuf -i 0-179 -n 1) && /usr/bin/python3 /home/pi/gym-booking/run_booking.py
```

## Operations

Run booking flow manually:

```bash
python3 run_booking.py
```

Preview next execution behavior:

```bash
python3 check_schedule.py
```

View live logs:

```bash
tail -f gym_booking.log
```

## Security and Compliance

- Store secrets only in `.env`.
- Never commit credentials, tokens, or session artifacts.
- Keep `.gitignore` aligned with all local sensitive files.

## Usage Scope

Intended for personal, non-commercial use.
