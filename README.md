# ARCHIPEL — Protocole P2P Chiffré et Décentralisé

## 1. Description

Archipel est un protocole de communication Peer-to-Peer (P2P) conçu pour fonctionner sur un réseau local pur (zéro connexion Internet externe), sans serveur central ni tracker DNS.

Chaque nœud agit à la fois comme client et serveur décentralisé. Le système garantit la sécurité et l'identité des pairs grâce à une cryptographie forte : **Ed25519** (signatures), **X25519** (échange de clés éphémères), **AES-256-GCM** (chiffrement symétrique), et une politique de confiance distribuée (*Web of Trust* TOFU).

## 2. Langage et Justification

**Langage principal : Python 3.9+**

Choix justifié par :
- **Productivité maximale** sur un hackathon de 24h
- **Ecosystème cryptographique mature** : PyNaCl (libsodium), bibliothèque `cryptography` (PyCA)
- **Sockets TCP/UDP natifs** dans la bibliothèque standard
- **Prototypage rapide** sans sacrifier la robustesse

## 3. Architecture et Choix Techniques

### Transport Local

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Découverte | UDP Multicast `239.255.42.99:6000` | Annonces HELLO toutes les 30s |
| Transfert | TCP Sockets port `7777` | Échanges chiffrés E2E fiables |

### Cryptographie & Handshake (3 temps)

Séquence inspirée du *Noise Protocol* :
1. `INIT` : Alice envoie sa clé publique éphémère X25519
2. `ACK`  : Bob répond avec sa clé éphémère + salt → dérivation `session_key = HKDF(shared_secret, salt)`
3. `AUTH` : Alice s'authentifie via sa clé long-terme **Ed25519** (protection MITM)

### Web of Trust (TOFU)

Le réseau utilise *Trust On First Use* à la place d'une CA centrale. L'empreinte Ed25519 d'un pair est enregistrée dès le premier contact. Toute reconnexion avec une clé différente est rejetée.

### Format de Paquet Binaire

```
MAGIC(4) | TYPE(1) | NODE_ID(32) | PAYLOAD_LEN(4) | PAYLOAD(var) | HMAC-SHA256(32)
```
Header fixe = **41 bytes** · Signature = **32 bytes** HMAC-SHA256

### Transfert de Fichiers (Sprint 3)

Fichiers découpés en chunks de **512 KB**. L'expéditeur génère un `MANIFEST` signé (hash SHA-256, nombre de chunks), permettant les téléchargements asynchrones et la reprise après interruption.

### Intégration IA (Sprint 4)

Gemini est intégré via le tag `@archipel-ai` ou `/ask` dans le CLI et la Web UI.

## 4. Instructions d'Utilisation

### Prérequis

```bash
python -m pip install -r requirements.txt
# Optionnel (IA) :
$env:GEMINI_API_KEY = "votre_clé_api"
```

### Générer son identité

```bash
python src/clé.py --name Alice
```

### Lancer le nœud

```bash
# Terminal 1 — Nœud Alice
python src/cli.py start --port 7777

# Terminal 2 — Nœud Bob (même LAN)
python src/cli.py start --port 7778
```

### Commandes CLI

```bash
python src/cli.py peers                             # Voir les pairs
python src/cli.py msg <NODE_ID> "Salut Bob!"        # Message chiffré E2E
python src/cli.py msg <NODE_ID> "@archipel-ai ..."  # Interroger l'IA
python src/cli.py send <NODE_ID> fichier.zip        # Envoyer un fichier
python src/cli.py download <FILE_ID>                # Télécharger un fichier
python src/cli.py status                            # Voir l'état du nœud
```

### Interface Web

```bash
python src/web_ui.py
# Ouvrir : http://localhost:8080
```

## 5. Structure du Projet

```
src/
├── cli.py               # Interface CLI principale
├── web_ui.py            # Serveur HTTP (dashboard)
├── archipel_ui.html     # Interface Web
├── crypto/
│   ├── identity.py      # Génération/chargement clés Ed25519
│   ├── handshake.py     # Handshake 3-temps (INIT/ACK/AUTH)
│   ├── messaging.py     # Chiffrement/déchiffrement messages
│   └── crypto.py        # Primitives AES-256-GCM + HMAC
├── network/
│   ├── packet.py        # Format binaire Archipel v1
│   ├── discovery.py     # Émetteur UDP Multicast
│   ├── listener.py      # Récepteur UDP Multicast
│   └── tcp_server.py    # Serveur TCP (connexions pairs)
├── transfer/
│   ├── chunking.py      # Découpage fichiers + manifests
│   └── transfer_manager.py  # Orchestration téléchargements
└── messaging/
    └── gemini_ai.py     # Intégration Gemini API
```

## 6. Membres de l'équipe

- **OURO-M'BON Diyanatou** — Planification stratégique et validation des exigences
- *[Ajouter les autres membres de l'équipe ici]*

🎉 **Bonne chance. Construisez quelque chose qui mérite de survivre.**
