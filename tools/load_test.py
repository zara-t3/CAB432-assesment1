import requests, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "http://ec2-52-62-70-139.ap-southeast-2.compute.amazonaws.com:8080/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJleHAiOjE3NTY2MDc1NDl9.Bme8j64tjsHAUK9DTUbt6KOCemy5jP2uJ3f4AErtelI"
IMAGE_ID = "624f854a-6b89-41c7-ac8b-cbd5e3eccd88"

CONCURRENCY = 2
TOTAL_JOBS  = 1000
TIMEOUT_S   = 600

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
payload = {"image_id": IMAGE_ID, "extra_passes": 4, "blur_strength": 22}

def one_job(idx):
    t0 = time.time()
    r = requests.post(f"{BASE}/jobs", data=json.dumps(payload), headers=headers, timeout=TIMEOUT_S)
    dt = round((time.time()-t0)*1000)
    return idx, r.status_code, dt

t0 = time.time()
ok = bad = 0
with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
    futs = [ex.submit(one_job, i+1) for i in range(TOTAL_JOBS)]
    for fut in as_completed(futs):
        i, status, dt = fut.result()
        if status == 200: ok += 1
        else: bad += 1
        print(f"job {i}/{TOTAL_JOBS} -> {status} in {dt}ms")
print(f"done {ok} ok, {bad} bad in {round(time.time()-t0,2)}s")
