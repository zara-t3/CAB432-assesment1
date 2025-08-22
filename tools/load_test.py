import asyncio, aiohttp, json, time

# --- hardcoded config ---
BASE = "http://ec2-13-239-254-23.ap-southeast-2.compute.amazonaws.com:8080/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJleHAiOjE3NTU5MDg3MTF9.zkQhMOXe_NXEED0RWY42s5DpKNkYGsZAAccH_gkyGuI" 
IMAGE_ID = "d1e59d6d-be2a-4dd0-a3db-9ba2b91bd184"

CONCURRENCY = 25   # number of concurrent requests per batch
REPEAT = 100         # how many times to repeat the batch

async def one(session):
    payload = {"image_id": IMAGE_ID, "extra_passes": 3, "blur_strength": 16}
    async with session.post(f"{BASE}/jobs", data=json.dumps(payload)) as r:
        if r.status != 200:
            print("bad:", r.status, await r.text())

async def run_batch(session):
    await asyncio.gather(*[one(session) for _ in range(CONCURRENCY)])

async def main():
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession(headers=headers) as s:
        for i in range(REPEAT):
            t0 = time.time()
            await run_batch(s)
            print(f"round {i+1}/{REPEAT} done in {round(time.time()-t0,2)} s")

if __name__ == "__main__":
    asyncio.run(main())
