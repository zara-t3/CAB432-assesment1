# Simple in-memory “DB” to get moving; swap to SQLite later if you want.
IMAGES = {}  # id -> {owner, orig_path, processed_path, created_at}
JOBS   = {}  # id -> {owner, image_id, steps, repeat, status, output_path, duration_ms, created_at}
