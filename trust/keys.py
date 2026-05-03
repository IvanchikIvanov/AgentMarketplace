from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

from ..contracts.common import MessageEnvelope


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _b64decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data.encode("ascii"))


@dataclass(frozen=True)
class SigningKeyPair:
    key_id: str
    private_key_b64: str
    public_key_b64: str


def generate_signing_keypair(*, key_id: str) -> SigningKeyPair:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_bytes = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return SigningKeyPair(
        key_id=key_id,
        private_key_b64=_b64encode(private_bytes),
        public_key_b64=_b64encode(public_bytes),
    )


def _canonical_message_bytes(envelope: MessageEnvelope) -> bytes:
    data = envelope.to_dict()
    metadata = dict(data.get("metadata") or {})
    metadata.pop("signature", None)
    metadata.pop("pubkey_id", None)
    data["metadata"] = metadata
    import json

    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sign_envelope(envelope: MessageEnvelope, *, private_key_b64: str, pubkey_id: str) -> MessageEnvelope:
    private_key = Ed25519PrivateKey.from_private_bytes(_b64decode(private_key_b64))
    signature = private_key.sign(_canonical_message_bytes(envelope))
    metadata = dict(envelope.metadata)
    metadata["signature"] = _b64encode(signature)
    metadata["pubkey_id"] = pubkey_id
    return MessageEnvelope(
        message_id=envelope.message_id,
        correlation_id=envelope.correlation_id,
        schema_version=envelope.schema_version,
        message_type=envelope.message_type,
        sender=envelope.sender,
        receiver=envelope.receiver,
        created_at=envelope.created_at,
        payload=dict(envelope.payload),
        metadata=metadata,
    )


def verify_envelope_signature(envelope: MessageEnvelope, *, public_key_b64: str) -> bool:
    signature = str(envelope.metadata.get("signature") or "")
    if not signature:
        return False
    public_key = Ed25519PublicKey.from_public_bytes(_b64decode(public_key_b64))
    try:
        public_key.verify(_b64decode(signature), _canonical_message_bytes(envelope))
        return True
    except (InvalidSignature, ValueError):
        return False


def key_fingerprint(public_key_b64: str) -> str:
    import hashlib

    digest = hashlib.sha256(_b64decode(public_key_b64)).hexdigest()
    return digest[:24]


def signed_metadata(pubkey_id: str, signature: str) -> dict[str, Any]:
    return {"pubkey_id": pubkey_id, "signature": signature}
