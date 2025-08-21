import asyncio, aiohttp, os, json, time, argparse

# --- parse args ---
p = argparse.ArgumentParser()
p.add_argument("--host", required=True)
p.add_argument("--token", required=True)
p.add_argument("--image-id", required=True)
p.add_argument("--n", type=int, default=10)
p.add_argument("--repeat", type=int, default=1)
args = p.parse_args()

BASE = args.host
TOKEN = args.token
IMAGE_ID = args.image_id
CONCURRENCY = args.n
REPEAT = args.repeat

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
