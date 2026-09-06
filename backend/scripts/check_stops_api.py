import httpx

r = httpx.get("http://localhost:8000/api/v1/transit/stops?limit=500")
data = r.json()
stops = data["stops"]
with_loc = [s for s in stops if s.get("lat") and s.get("lon")]
print(f"Total stops returned: {len(stops)}")
print(f"With coordinates: {len(with_loc)}")
if stops:
    print(f"First: {stops[0]}")
