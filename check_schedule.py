#!/usr/bin/env python3
from app import Config
from datetime import datetime, timedelta

now = datetime.now(Config.TZ)
tomorrow = now + timedelta(days=1)

print(f"Today: {now.strftime('%A %Y-%m-%d')} (weekday {now.weekday()})")
print(f"Tomorrow: {tomorrow.strftime('%A %Y-%m-%d')} (weekday {tomorrow.weekday()})")
print()
print("Weekly Schedule:")
for day, spec in sorted(Config.WEEKLY_PLAN.items()):
    day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][day]
    print(f'  {day_name}: Lesson {spec["IDLesson"]} at {spec["start"]} (BookingID: {spec["BookingID"]})')
print(f'\nSkipped days: {", ".join(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d] for d in sorted(Config.SKIP_WEEKDAYS))}')
print()
if tomorrow.weekday() in Config.SKIP_WEEKDAYS:
    print("✅ Tomorrow will be SKIPPED")
elif tomorrow.weekday() in Config.WEEKLY_PLAN:
    spec = Config.WEEKLY_PLAN[tomorrow.weekday()]
    booking_date = tomorrow + timedelta(days=7)
    print(f'✅ Tomorrow at 00:01 will book: Lesson {spec["IDLesson"]} for {booking_date.strftime("%Y-%m-%d")} at {spec["start"]}')
else:
    print("⚠️  No configuration for tomorrow")
