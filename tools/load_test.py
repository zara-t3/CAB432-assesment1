import asyncio, aiohttp, os, json, time
BASE = os.environ.get("BASE", "http://localhost:8080/api/v1")
TOKEN = os.environ["TOKEN"]             # set this from a login response
IMAGE_ID = os.environ["IMAGE_ID"]       # existing uploaded image id
CONCURRENCY = int(os.environ.get("N", "10"))

async def one(session):
    payload = {"image_id": IMAGE_ID, "extra_passes": 2, "blur_strength": 16}
    async with session.post(f"{BASE}/jobs", data=json.dumps(payload)) as r:
        if r.status != 200:
            print("bad:", r.status, await r.text())

async def main():
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession(headers=headers) as s:
        t0 = time.time()
        await asyncio.gather(*[one(s) for _ in range(CONCURRENCY)])
        print("done in", round(time.time()-t0, 2), "s")

if __name__ == "__main__":
    asyncio.run(main())
