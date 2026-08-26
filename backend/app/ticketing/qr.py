import hmac
import hashlib
import json
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC

from app.core.config import settings
from app.core.constants import QR_PAYLOAD_EXPIRY_HOURS


@dataclass
class QRVerificationResult:
    valid: bool
    ticket_id: int | None = None
    user_id: int | None = None
    error: str | None = None


class QRService:
    """HMAC-signed QR payload generation and verification."""

    def __init__(self):
        self.signing_key = settings.QR_SIGNING_KEY.encode()
        if not self.signing_key:
            raise ValueError("QR_SIGNING_KEY must be set in environment")

    def _create_signature(self, payload: dict) -> str:
        """Create HMAC-SHA256 signature for the payload."""
        payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        signature = hmac.new(self.signing_key, payload_bytes, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(signature).decode().rstrip("=")

    def _verify_signature(self, payload: dict, signature: str) -> bool:
        """Verify HMAC-SHA256 signature."""
        expected_signature = self._create_signature(payload)
        return hmac.compare_digest(expected_signature, signature)

    def generate_payload(self, ticket_id: int, user_id: int) -> str:
        """
        Generate a signed opaque QR payload.
        
        Payload contains only ticket_id and user_id with expiry and HMAC signature.
        No sensitive ticket data (fare, route, etc.) is included.
        """
        expires_at = datetime.now(UTC) + timedelta(hours=QR_PAYLOAD_EXPIRY_HOURS)
        
        payload = {
            "ticket_id": ticket_id,
            "user_id": user_id,
            "exp": int(expires_at.timestamp()),
        }
        
        signature = self._create_signature(payload)
        
        token_data = {
            "p": payload,
            "s": signature,
        }
        
        token_json = json.dumps(token_data, separators=(",", ":"))
        token_b64 = base64.urlsafe_b64encode(token_json.encode()).decode().rstrip("=")
        
        return token_b64

    def verify_payload(self, token: str) -> QRVerificationResult:
        """
        Verify a QR payload signature and extract ticket_id and user_id.
        
        Returns QRVerificationResult with valid flag and extracted data.
        """
        try:
            # Decode base64
            token_json = base64.urlsafe_b64decode(token + "==").decode()
            token_data = json.loads(token_json)
            
            payload = token_data.get("p")
            signature = token_data.get("s")
            
            if not payload or not signature:
                return QRVerificationResult(valid=False, error="Invalid token structure")
            
            # Verify signature
            if not self._verify_signature(payload, signature):
                return QRVerificationResult(valid=False, error="Invalid signature")
            
            # Check expiry
            exp = payload.get("exp")
            if exp is None:
                return QRVerificationResult(valid=False, error="Missing expiry")
            
            if datetime.now(UTC).timestamp() > exp:
                return QRVerificationResult(valid=False, error="Token expired")
            
            ticket_id = payload.get("ticket_id")
            user_id = payload.get("user_id")
            
            if not isinstance(ticket_id, int) or not isinstance(user_id, int):
                return QRVerificationResult(valid=False, error="Invalid payload data")
            
            return QRVerificationResult(
                valid=True,
                ticket_id=ticket_id,
                user_id=user_id,
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            return QRVerificationResult(valid=False, error=f"Invalid token: {str(e)}")