# tools/simple_load_concurrent.py
import requests, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "http://ec2-16-176-230-218.ap-southeast-2.compute.amazonaws.com:8080/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJleHAiOjE3NTU4NDA4MjF9.bLKC1DBysjUcXpQHUrWKDV75UI6y_iAicKPt0cxuhDE"
IMAGE_ID = "c1c92407-74cb-426e-a4ca-693ae369e957"

CONCURRENCY = 5      # try 3–5 on small instances
TOTAL_JOBS  = 100    # total jobs across all threads
TIMEOUT_S   = 600

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
payload = {"image_id": IMAGE_ID, "extra_passes": 4, "blur_strength": 20}

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
