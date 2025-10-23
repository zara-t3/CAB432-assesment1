import requests, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://n11544309.cab432.com/api/v1"
TOKEN = "eyJraWQiOiJwUHhrNmJGVm9kbVhBamtBSTgwdStFU0UySUlVeGhIcFVkdmlWUERoOTdZPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI4OTBlODQ1OC1kMGQxLTcwMjgtYTU0NS0yMTE5ODI0NGM1NDQiLCJjb2duaXRvOmdyb3VwcyI6WyJ1c2VyIl0sImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5hcC1zb3V0aGVhc3QtMi5hbWF6b25hd3MuY29tXC9hcC1zb3V0aGVhc3QtMl92dDZDdVV6Z2wiLCJ2ZXJzaW9uIjoyLCJjbGllbnRfaWQiOiJyNGpidmV1bnRta2I3czVtNmNvdGQ2ZXJlIiwib3JpZ2luX2p0aSI6Ijc1MGQ2ODI3LTY2ODktNDc4ZS1iZjk1LWIyMTZlZDU1NTJjYyIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwiLCJhdXRoX3RpbWUiOjE3NjA4NDY2MzAsImV4cCI6MTc2MDg1MDIzMCwiaWF0IjoxNzYwODQ2NjMwLCJqdGkiOiIyOGNkY2YxZi04OTM4LTQ3NWUtYTM0Zi03ZTcxZDYxODkwYjgiLCJ1c2VybmFtZSI6Imdvb2dsZV8xMDA1NzE2NzY4MzY5MTc5NDcxMDkifQ.HqY9RSG_QV45eq2W70SjlvBvT9RGmm1FpnDczKUrZlaY-eIqOCPBJGLOOmKtG_RA3xkFkhp37tiftiqdFaozYb8zc_LrgTBkD9T0KQupUcnjCFQUc6OKDZe7X3Ernk1EOchjEqzTmkZvG562ZY54EJQeaiI5a7fwBKejJ8FMFr8wIw6umdSx6KB0z1yEkbTgJhvdgIoMfktzppn6GxRX_PZaew9VGg7nxum4nIB8PfwReWI_P2QcbyNyuwi3esiPi1iL5-SMDEkibqftjbsf9DHVc-0XX4116dv-UW4-eGQCJHGPRfu0xzSjlW7NZ8q-Y6DqUqeUsLsPt5dLNBCQ6w"
IMAGE_ID = "8d19e028-216d-4e21-bd27-640ab7778df8"

# CHANGED: Better settings for auto-scaling
CONCURRENCY = 20    # Queue up many jobs at once
TOTAL_JOBS = 60     # 60 jobs is enough (1000 would take hours!)
TIMEOUT_S = 600

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# CHANGED: More CPU-intensive settings
payload = {"image_id": IMAGE_ID, "extra_passes": 8, "blur_strength": 30}

def one_job(idx):
    t0 = time.time()
    r = requests.post(f"{BASE}/jobs", json=payload, headers=headers, timeout=TIMEOUT_S)
    dt = round((time.time()-t0)*1000)
    return idx, r.status_code, dt

print("=" * 80)
print("AUTO-SCALING LOAD TEST")
print("=" * 80)
print(f"Creating {TOTAL_JOBS} jobs with concurrency {CONCURRENCY}")
print(f"Settings: extra_passes=8, blur_strength=30 (HIGH CPU)")
print()
print("NOW OPEN THESE TABS IN AWS CONSOLE:")
print("  1. ECS -> Cluster -> Service -> Tasks (watch count)")
print("  2. SQS -> Your queue (watch messages)")
print("  3. CloudWatch -> Metrics (watch CPU)")
print("=" * 80)
print()

t0 = time.time()
ok = bad = 0

with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
    futs = [ex.submit(one_job, i+1) for i in range(TOTAL_JOBS)]
    for fut in as_completed(futs):
        i, status, dt = fut.result()
        if status == 200: 
            ok += 1
            print(f"✓ Job {i:3d}/{TOTAL_JOBS} -> {status} in {dt}ms")
        else: 
            bad += 1
            print(f"✗ Job {i:3d}/{TOTAL_JOBS} -> {status} in {dt}ms")

elapsed = round(time.time()-t0, 2)

print()
print("=" * 80)
print(f"ALL {TOTAL_JOBS} JOBS QUEUED IN {elapsed} SECONDS!")
print(f"Success: {ok} | Failed: {bad}")
print("=" * 80)
print()
print("WHAT TO WATCH NOW (for next 20 minutes):")
print("  T+0-3 min:  CPU climbs, 1 task processing")
print("  T+4-5 min:  CPU hits 70%, auto-scaling triggers")
print("  T+5-6 min:  2nd task starts (REFRESH ECS PAGE)")
print("  T+8-10 min: 3rd task starts (REFRESH ECS PAGE)")
print("  T+15 min:   All jobs done, CPU drops")
print("  T+20 min:   Scales back to 1 task")
print()
print("REFRESH YOUR BROWSER TABS EVERY 30 SECONDS!")
print("=" * 80)