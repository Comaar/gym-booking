# Gym Booking Automation

A lightweight automation tool that books gym classes automatically based on a predefined weekly schedule.

Designed to run unattended on a low power device such as a Raspberry Pi Zero 2 W, the system handles authentication, scheduling, retries, and logging with minimal overhead.

---

## Overview

This project automates recurring class bookings by:

- authenticating with a web based booking system  
- scheduling bookings for the following week  
- executing requests at a precise time  
- handling transient failures with retries  
- logging all operations for visibility  

The goal is simple: remove manual booking friction while keeping the system predictable and reliable.

---

## Key Features

- automated daily execution via scheduler (cron or launchd)  
- token based authentication with refresh handling  
- configurable weekly booking plan  
- timezone aware execution (default Europe/Rome)  
- configurable skip days  
- retry logic for failed requests  
- persistent session handling  
- structured logging  

---

## Architecture

```text
.
├── app.py                      # core logic: authentication and booking
├── run_booking.py              # scheduled entry point
├── check_schedule.py           # schedule preview utility
├── com.marco.gymbooking.plist  # macOS scheduler config (optional)
├── requirements.txt            # dependencies
├── .env.example                # config template
└── README.md
```


## How It Works
- the scheduler triggers the script at a fixed time
- the system checks whether the current day is eligible
- if valid, it prepares a booking request for the next week
- authentication is handled using stored credentials or session data
- the booking request is executed
- retries are performed if needed
- results are written to the log
