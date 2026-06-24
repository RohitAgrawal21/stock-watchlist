"""
scheduler.py — Auto-refresh the watchlist once a day after market close.

Run this in the background (keep the window open, or wrap with the .vbs/.bat):
    python scheduler.py

Default: every day at 18:30 IST (after NSE close). Edit HOUR/MINUTE below.
"""

from __future__ import annotations

import datetime as dt

from apscheduler.schedulers.blocking import BlockingScheduler

from refresh import refresh_all

HOUR = 18      # 24h clock, local machine time
MINUTE = 30


def job():
    print(f"[{dt.datetime.now():%Y-%m-%d %H:%M}] Scheduled refresh starting...")
    try:
        refresh_all(verbose=True)
        print("Scheduled refresh done.\n")
    except Exception as e:  # noqa: BLE001
        print(f"Refresh error: {e}\n")


if __name__ == "__main__":
    sched = BlockingScheduler()
    sched.add_job(job, "cron", hour=HOUR, minute=MINUTE)
    print(f"Scheduler running — daily refresh at {HOUR:02d}:{MINUTE:02d}. "
          f"Ctrl+C to stop.")
    job()  # run once on startup so you have fresh data immediately
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")
