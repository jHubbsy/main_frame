"""Ed25519 signature verification for skills."""

from __future__ import annotations

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from mainframe.skills.manifest import SkillManifest


class SkillVerifier:
    """Verifies skill signatures against trusted publisher keys."""

    def __init__(self) -> None:
        self._trusted_keys: dict[str, Ed25519PublicKey] = {}

    def add_trusted_key(self, publisher: str, public_key: Ed25519PublicKey) -> None:
        self._trusted_keys[publisher] = public_key

    def add_trusted_key_bytes(self, publisher: str, public_key_bytes: bytes) -> None:
        key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        self._trusted_keys[publisher] = key

    def verify(self, skill: SkillManifest) -> bool:
        """Verify a skill's signature and content hash.

        Returns True if:
        1. The skill has a signature and content_hash
        2. The content_hash matches the actual body
        3. The signature is valid for the content_hash using the publisher's key
        """
        if not skill.is_signed:
            return False

        if not skill.verify_content_hash():
            return False

        if skill.publisher not in self._trusted_keys:
            return False

        public_key = self._trusted_keys[skill.publisher]
        try:
            sig_bytes = base64.b64decode(skill.signature)
            public_key.verify(sig_bytes, skill.content_hash.encode())
            return True
        except (InvalidSignature, Exception):
            return False


def generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Generate a new ed25519 keypair for skill signing."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def sign_skill(skill: SkillManifest, private_key: Ed25519PrivateKey) -> tuple[str, str]:
    """Sign a skill's content. Returns (signature_b64, content_hash)."""
    content_hash = skill.compute_content_hash()
    sig_bytes = private_key.sign(content_hash.encode())
    signature = base64.b64encode(sig_bytes).decode()
    return signature, content_hash
