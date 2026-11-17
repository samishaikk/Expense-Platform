import argparse
import random
import time
from datetime import datetime
from getpass import getpass
from pathlib import Path

import httpx

TIMELINE_FILE = Path("incident/timeline.txt")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def make_logger():
    TIMELINE_FILE.parent.mkdir(exist_ok=True)

    def log(message: str) -> None:
        line = f"{now()}  {message}"
        print(line)
        with TIMELINE_FILE.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    return log


def pick_request(rng: random.Random, faulty: bool):
    roll = rng.random()
    if faulty:
        if roll < 0.40:
            return "/debug/fault", {"fail": "true"}
        if roll < 0.70:
            return "/debug/fault", {"delay_ms": 800}
    normal = ["/expenses", "/expenses", "/health", "/ready"]
    return rng.choice(normal), None


def run_phase(client, headers, name, seconds, faulty, rng, interval, log):
    log(f"PHASE {name} START ({seconds}s)")
    counts = {}
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        path, params = pick_request(rng, faulty)
        try:
            code = client.get(path, params=params, headers=headers).status_code
        except httpx.HTTPError:
            code = "conn-error"
        counts[code] = counts.get(code, 0) + 1
        time.sleep(interval)
    log(f"PHASE {name} END  status counts: {dict(sorted(counts.items(), key=lambda kv: str(kv[0])))}")


def main():
    parser = argparse.ArgumentParser(description="Scripted traffic for the incident run")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", required=True)
    parser.add_argument("--baseline", type=int, default=120)
    parser.add_argument("--fault", type=int, default=180)
    parser.add_argument("--recovery", type=int, default=120)
    parser.add_argument("--interval", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    password = getpass("Password: ")
    log = make_logger()
    rng = random.Random(args.seed)

    with httpx.Client(base_url=args.base_url, timeout=10) as client:
        login = client.post("/auth/login", data={"username": args.email, "password": password})
        if login.status_code != 200:
            print(f"Login failed ({login.status_code}). Check the email and password.")
            return
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        log(f"RUN START seed={args.seed}")
        run_phase(client, headers, "baseline", args.baseline, False, rng, args.interval, log)
        run_phase(client, headers, "fault", args.fault, True, rng, args.interval, log)
        run_phase(client, headers, "recovery", args.recovery, False, rng, args.interval, log)
        log("RUN END")


if __name__ == "__main__":
    main()