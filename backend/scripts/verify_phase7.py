"""Real HTTP verification of Phase 7 using TestClient (no server needed)."""
import sys

from app.main import create_app
from fastapi.testclient import TestClient

RESULTS = []


def check(name, passed, detail=""):
    RESULTS.append((name, passed))
    marker = "PASS" if passed else "FAIL"
    msg = f"  [{marker}] {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)


def main():
    app = create_app()
    with TestClient(app) as c:
        print("\n=== Phase 7 Real HTTP Verification ===\n")

        # 1. Register user
        r = c.post("/api/v1/auth/register", json={
            "email": "ticket_tester@example.com",
            "password": "securepass123",
            "full_name": "Ticket Tester",
        })
        check("Register user", r.status_code == 201, f"status={r.status_code}")

        # 2. Login
        r = c.post("/api/v1/auth/login", json={
            "email": "ticket_tester@example.com",
            "password": "securepass123",
        })
        check("Login", r.status_code == 200)
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # 3. Register 2nd user
        c.post("/api/v1/auth/register", json={
            "email": "other_user@example.com",
            "password": "otherpass123",
        })
        r2 = c.post("/api/v1/auth/login", json={
            "email": "other_user@example.com",
            "password": "otherpass123",
        })
        other_h = {"Authorization": f"Bearer {r2.json()['access_token']}"}
        check("Register 2nd user", r2.status_code == 200)

        # 4. Fare quote
        r = c.post("/api/v1/fares/quote", json={"ride_leg_count": 2})
        f = r.json()
        check("Fare quote endpoint", r.status_code == 200)
        check("Fare total=70", f["total"] == 70.0, f"total={f['total']}")
        check("Fare base=50", f["base_fare"] == 50.0)
        check("Fare per_leg=20", f["per_leg_fare"] == 20.0)
        check("Fare currency=PKR", f["currency"] == "PKR")

        # 5. 0-leg fare
        r = c.post("/api/v1/fares/quote", json={"ride_leg_count": 0})
        check("0-leg fare=0", r.json()["total"] == 0.0)

        # 6. Purchase ticket
        r = c.post("/api/v1/tickets", json={
            "journey_data": {"legs": [{"type": "ride", "route_id": 5}]},
            "ride_leg_count": 1,
        }, headers=h)
        t = r.json()
        check("Purchase ticket", r.status_code == 201)
        check("Status ACTIVE", t["status"] == "ACTIVE")
        check("Fare charged=50", t["fare_charged"] == 50.0)
        qr = t["qr_payload"]
        tid = t["id"]
        check("QR payload present", qr is not None and len(qr) > 10)
        check("expires_at set", t["expires_at"] is not None)
        check("used_at is None", t["used_at"] is None)

        # 7. No auth purchase
        r = c.post("/api/v1/tickets", json={"journey_data": {}, "ride_leg_count": 1})
        check("No auth purchase=401", r.status_code == 401)

        # 8. List tickets
        r = c.get("/api/v1/tickets", headers=h)
        check("List tickets", r.status_code == 200)
        check("List has tickets", len(r.json()["tickets"]) >= 1)

        # 9. Get ticket
        r = c.get(f"/api/v1/tickets/{tid}", headers=h)
        check("Get ticket", r.status_code == 200)
        check("Get ticket matches ID", r.json()["id"] == tid)

        # 10. Validate
        r = c.post("/api/v1/tickets/validate", json={"qr_payload": qr}, headers=h)
        v = r.json()
        check("Validate ticket", r.status_code == 200)
        check("Validation valid=true", v["valid"] is True)
        check("Validation status=USED", v["status"] == "USED")
        check("Validation ticket_id matches", v["ticket_id"] == tid)

        # 11. Replay protection
        r = c.post("/api/v1/tickets/validate", json={"qr_payload": qr}, headers=h)
        v2 = r.json()
        check("Replay valid=false", v2["valid"] is False)
        check("Replay reason has 'used'", "used" in (v2.get("reason") or "").lower())

        # 12. Verify ticket is USED in DB
        r = c.get(f"/api/v1/tickets/{tid}", headers=h)
        check("Ticket status USED", r.json()["status"] == "USED")
        check("Ticket used_at set", r.json()["used_at"] is not None)

        # 13. Unauthorized access
        r = c.get(f"/api/v1/tickets/{tid}", headers=other_h)
        check("Other user can't get ticket=404", r.status_code == 404)

        # 14. Other user empty list
        r = c.get("/api/v1/tickets", headers=other_h)
        check("Other user has 0 tickets", len(r.json()["tickets"]) == 0)

        # 15. Purchase + revoke
        r = c.post("/api/v1/tickets", json={
            "journey_data": {"legs": []},
            "ride_leg_count": 2,
        }, headers=h)
        rtid = r.json()["id"]
        rqr = r.json()["qr_payload"]
        r = c.post(f"/api/v1/tickets/{rtid}/revoke", headers=h)
        check("Revoke ticket", r.status_code == 200)
        check("Ticket REVOKED", r.json()["status"] == "REVOKED")

        # 16. Validate revoked
        r = c.post("/api/v1/tickets/validate", json={"qr_payload": rqr}, headers=h)
        check("Revoked valid=false", r.json()["valid"] is False)
        check("Revoked reason='revoked'", "revoked" in (r.json().get("reason") or "").lower())

        # 17. Tampered QR
        r = c.post("/api/v1/tickets", json={"journey_data": {}, "ride_leg_count": 1}, headers=h)
        oqr = r.json()["qr_payload"]
        r = c.post("/api/v1/tickets/validate", json={"qr_payload": oqr[:-5] + "XXXXX"}, headers=h)
        check("Tampered QR valid=false", r.json()["valid"] is False)

        # 18. Invalid token
        r = c.post("/api/v1/tickets/validate", json={"qr_payload": "garbage"}, headers=h)
        check("Invalid token valid=false", r.json()["valid"] is False)

        # 19. Validate no auth
        r = c.post("/api/v1/tickets/validate", json={"qr_payload": oqr})
        check("Validate no auth=401", r.status_code == 401)

        # 20. Not found
        r = c.get("/api/v1/tickets/999999", headers=h)
        check("Not found=404", r.status_code == 404)

        # 21. 2-leg fare check
        r = c.post("/api/v1/fares/quote", json={"ride_leg_count": 2})
        check("2-leg fare=70", r.json()["total"] == 70.0)

        # Summary
        passed = sum(1 for _, p in RESULTS if p)
        failed = sum(1 for _, p in RESULTS if not p)
        print(f"\n{'=' * 60}")
        print(f"RESULTS: {passed} passed, {failed} failed, {len(RESULTS)} total")
        print(f"{'=' * 60}")
        return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)