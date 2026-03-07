"""
Archipel — Identité PKI Ed25519
Génère ou charge la paire de clés du nœud.
"""

import os
import hashlib
import secrets

# Import PyNaCl optionally — si absent, on bascule en fallback non-signant
try:
    import nacl.signing  # type: ignore[reportMissingImports]
    import nacl.encoding  # type: ignore[reportMissingImports]
    HAVE_PYNACL = True
except Exception:
    HAVE_PYNACL = False

KEY_PATH = ".archipel/private_key.key"  # Hors racine, protégé par .gitignore


def get_my_identity():
    """
    Retourne (signing_key, public_key_hex).
    - signing_key     : objet nacl pour signer des messages (None si fallback)
    - public_key_hex  : identifiant unique du nœud sur le réseau
    """
    os.makedirs(".archipel", exist_ok=True)

    seed_bytes = None  # ← variable commune pour éviter la double lecture

    if not os.path.exists(KEY_PATH):
        # Génération d'une nouvelle paire de clés Ed25519 (ou fallback)
        if HAVE_PYNACL:
            signing_key = nacl.signing.SigningKey.generate()
            seed_bytes  = signing_key.encode(encoder=nacl.encoding.RawEncoder)
            with open(KEY_PATH, "wb") as f:
                f.write(seed_bytes)
        else:
            # Fallback non sécurisé : stocke un seed pseudo-aléatoire
            seed_bytes  = secrets.token_bytes(32)
            signing_key = None
            with open(KEY_PATH, "wb") as f:
                f.write(seed_bytes)

        # Permissions restrictives (Linux/Mac)
        try:
            os.chmod(KEY_PATH, 0o600)
        except Exception:
            pass  # Windows ne supporte pas chmod
        print(f"[PKI] Nouvelle identite generee -> {KEY_PATH}")

    else:
        # Chargement robuste — gère les fichiers corrompus
        try:
            with open(KEY_PATH, "rb") as f:
                seed_bytes = f.read()  # ← lu une seule fois, réutilisé plus bas
            if HAVE_PYNACL:
                signing_key = nacl.signing.SigningKey(seed_bytes)
                print(f"[PKI] Identite chargee depuis {KEY_PATH}")
            else:
                signing_key = None
                print(f"[PKI] Identite (fallback) chargee depuis {KEY_PATH}")
        except Exception:
            print(f"[PKI] Cle corrompue - regeneration...")
            os.remove(KEY_PATH)
            return get_my_identity()  # Relance récursivement

    # Calcul de l'identifiant public — réutilise seed_bytes, pas de double lecture
    if HAVE_PYNACL and signing_key is not None:
        public_key_hex = signing_key.verify_key.encode().hex()
    else:
        public_key_hex = hashlib.sha256(seed_bytes).hexdigest()

    return signing_key, public_key_hex


if __name__ == "__main__":
    signing_key, my_id = get_my_identity()
    print(f"Mon ID Archipel : {my_id}")
    print(f"Fingerprint     : {my_id[:16]}...")