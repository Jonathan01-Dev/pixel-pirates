"""
Archipel — Module 2.3 : Web of Trust (TOFU)
Mémorise la clé Ed25519 PERMANENTE du pair — pas la clé éphémère X25519
→ évite les faux positifs MITM lors des reconnexions
"""

import json
import os
import hashlib
import time

TRUST_STORE_PATH = ".archipel/trust_store.json"


class TrustStore:
    def __init__(self, path: str = TRUST_STORE_PATH):
        self.path   = path
        self._store = {}
        self._load()

    def _load(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        try:
            with open(self.path) as f:
                self._store = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._store = {}

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self._store, f, indent=2)

    def _fingerprint(self, key_hex: str) -> str:
        return hashlib.sha256(key_hex.encode()).hexdigest()[:16]

    def verify(self, node_id: str, public_key_hex: str) -> str:
        """
        Vérifie l'identité d'un pair.
        Utilise node_id (clé Ed25519 permanente) — pas la clé éphémère X25519.
        Retourne : 'ok' | 'new' | 'mismatch' | 'revoked'
        """
        if node_id not in self._store:
            # Premier contact — TOFU
            self._store[node_id] = {
                "public_key":  public_key_hex,
                "fingerprint": self._fingerprint(public_key_hex),
                "first_seen":  time.time(),
                "last_seen":   time.time(),
                "trusted":     True,
                "revoked":     False,
                "signed_by":   [],
            }
            self._save()
            print(f"[TRUST] 🆕 TOFU — Nouveau pair : {node_id[:16]}… (empreinte: {self._fingerprint(public_key_hex)})")
            return "new"

        entry = self._store[node_id]

        if entry.get("revoked"):
            print(f"[TRUST] 🚫 Pair révoqué : {node_id[:16]}…")
            return "revoked"

        if entry["public_key"] != public_key_hex:
            print(f"[TRUST] ⚠️  ALERTE MITM — Clé différente pour {node_id[:16]}…")
            return "mismatch"

        self._store[node_id]["last_seen"] = time.time()
        self._save()
        return "ok"

    def revoke(self, node_id: str, reason: str = "compromission"):
        if node_id in self._store:
            self._store[node_id]["revoked"]       = True
            self._store[node_id]["revoke_reason"] = reason
            self._store[node_id]["revoke_time"]   = time.time()
            self._save()
            print(f"[TRUST] 🚫 Clé révoquée : {node_id[:16]}… ({reason})")

    def is_revoked(self, node_id: str) -> bool:
        return self._store.get(node_id, {}).get("revoked", False)

    def sign_peer(self, node_id: str, signer_node_id: str):
        if node_id in self._store:
            signers = self._store[node_id].get("signed_by", [])
            if signer_node_id not in signers:
                signers.append(signer_node_id)
                self._store[node_id]["signed_by"] = signers
                self._save()

    def trust_score(self, node_id: str) -> float:
        entry = self._store.get(node_id, {})
        if not entry or entry.get("revoked"):
            return 0.0
        return min(0.5 + len(entry.get("signed_by", [])) * 0.1, 1.0)

    def display(self):
        print("\n--- ARCHIPEL TRUST STORE ---")
        if not self._store:
            print("  (Aucun pair connu)")
        for node_id, entry in self._store.items():
            status = "🚫 RÉVOQUÉ" if entry.get("revoked") else "✅ Approuvé"
            print(f"  {node_id[:16]}… | Empreinte: {entry['fingerprint']} | Confiance: {self.trust_score(node_id):.1f} | {status}")
        print("----------------------------\n")

    def build_revocation_packet(self, node_id: str, my_signing_key, reason: str = "compromission") -> dict:
        """
        Construit un paquet de révocation signé Ed25519 à broadcaster sur le réseau.
        Conforme au Module 2.3 : 'broadcast un message signé de révocation'.
        """
        import time
        payload = {
            "type":      "REVOKE",
            "node_id":   node_id,
            "reason":    reason,
            "timestamp": time.time(),
        }
        if my_signing_key:
            import json
            msg_bytes = json.dumps(payload, sort_keys=True).encode()
            payload["signature"] = my_signing_key.sign(msg_bytes).signature.hex()
        self.revoke(node_id, reason)
        return payload

    def apply_revocation_packet(self, packet: dict) -> bool:
        """
        Applique un paquet de révocation reçu d'un autre nœud.
        Vérifie la signature Ed25519 avant d'accepter la révocation.
        """
        import json
        node_id   = packet.get("node_id")
        sig_hex   = packet.get("signature", "")
        if not node_id:
            return False
        entry = self._store.get(node_id)
        if entry and sig_hex:
            try:
                import nacl.signing, nacl.encoding
                verify_key = nacl.signing.VerifyKey(
                    bytes.fromhex(entry["public_key"]), encoder=nacl.encoding.RawEncoder
                )
                check = {k: v for k, v in packet.items() if k != "signature"}
                verify_key.verify(json.dumps(check, sort_keys=True).encode(), bytes.fromhex(sig_hex))
                self.revoke(node_id, packet.get("reason", "remote_revocation"))
                print(f"[TRUST] 📡 Révocation distante appliquée pour {node_id[:16]}…")
                return True
            except Exception as e:
                print(f"[TRUST] ❌ Signature révocation invalide : {e}")
                return False
        return False


if __name__ == "__main__":
    import os
    if os.path.exists(TRUST_STORE_PATH):
        os.remove(TRUST_STORE_PATH)

    print("\n🔐 Test Module 2.3 — Web of Trust\n")
    store  = TrustStore()
    node_a = "a" * 64
    key_a  = "aa" * 32
    key_a2 = "bb" * 32

    store.verify(node_a, key_a)
    assert store.verify(node_a, key_a) == "ok"
    print("  ✅ TOFU OK")
    assert store.verify(node_a, key_a2) == "mismatch"
    print("  ✅ Détection MITM OK")
    store.revoke(node_a)
    assert store.verify(node_a, key_a) == "revoked"
    print("  ✅ Révocation OK")
    print("\n✅ Tous les tests Module 2.3 passent !\n")
