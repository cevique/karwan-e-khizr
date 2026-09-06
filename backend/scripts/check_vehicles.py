import httpx

r = httpx.get("http://localhost:8000/api/v1/transit/realtime/vehicles")
data = r.json()
vehicles = data["vehicles"]
print(f"Vehicles: {len(vehicles)}")
for v in vehicles[:5]:
    print(f"  id={v['id']} label={v['label']} lat={v['latitude']:.4f} lon={v['longitude']:.4f} status={v['status']}")
