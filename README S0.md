
## Livrable Sprint 0 — Bootstrap & Architecture

## Stack Technique

Le cœur d'Archipel repose sur **Python 3.9+** comme langage principal. Dans le contexte d'un hackathon de 24 heures, la productivité prime sur la performance brute, et Python offre l'écosystème cryptographique le plus mature et le plus accessible qui soit : PyNaCl expose directement libsodium (la bibliothèque cryptographique la plus auditée au monde), et la bibliothèque standard couvre déjà les sockets TCP/UDP sans dépendance externe.

Pour le transport local, Archipel combine deux technologies complémentaires tirées directement du sujet. La découverte des pairs repose sur **UDP Multicast** à l'adresse `239.255.42.99:6000` : chaque nœud émet un paquet HELLO toutes les 30 secondes à l'ensemble du réseau local, sans établir de connexion préalable. C'est léger, instantané, et ne nécessite aucune configuration. Une fois les pairs identifiés, le transfert des données bascule sur **TCP Sockets (port 7777)** : la connexion point-à-point garantit la fiabilité des échanges, le contrôle de flux, et la livraison ordonnée des chunks — indispensable pour des transferts de fichiers volumineux.

Cette combinaison UDP + TCP est exactement celle préconisée par le document technique : chaque protocole intervient là où il excelle.

La couche cryptographique s'appuie sur **PyNaCl** (bindings libsodium) pour les clés Ed25519 et X25519, et sur la bibliothèque `cryptography` (PyCA) pour AES-256-GCM et HMAC-SHA256.

L'interface utilisateur combine un **CLI interactif** (`src/cli.py`) pour les démonstrations rapides en terminal, et une **UI Web légère** (`src/web_ui.py` + `src/archipel_ui.html`) servie localement sur le port 8080 pour une présentation visuelle devant le jury.

Le stockage local des métadonnées repose sur **JSON** dans le dossier `.archipel/`. Ce choix délibéré élimine toute dépendance d'infrastructure : aucun serveur de base de données, un simple fichier sur le disque.


## Schéma d'Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     RÉSEAU LOCAL (LAN/WiFi)                     │
│                                                                 │
│   ┌──────────┐   UDP Multicast (découverte)  ┌──────────┐      │
│   │  Nœud A  │──────────────────────────────►│  Nœud B  │      │
│   │          │   239.255.42.99:6000  HELLO   │          │      │
│   │ Ed25519  │◄──────────────────────────────│ Ed25519  │      │
│   │  KeyPair │                               │  KeyPair │      │
│   │          │   TCP :7777 (transfert E2E)   │          │      │
│   │          │◄══════════════════════════════│          │      │
│   └────┬─────┘                               └────┬─────┘      │
│        │                                          │            │
│        │         TCP :7777 (transfert E2E)        │            │
│        └══════════════════════════════════════════┘            │
│                          │                                      │
│                     ┌────▼─────┐                               │
│                     │  Nœud C  │   Chaque nœud :               │
│                     │          │   • UDP Multicast → HELLO     │
│                     │ Ed25519  │   • TCP → transfert chiffré   │
│                     │  KeyPair │   • Chunks BitTorrent-style   │
│                     └──────────┘   • Web of Trust (TOFU)      │
└─────────────────────────────────────────────────────────────────┘
```


## Format de Paquet Archipel v1 — Spécification

Conformément au cahier des charges, les échanges utilisent un protocole binaire strict (pas de simples chaînes JSON).

```
┌──────────┬──────────┬───────────┬────────────────────────┐
│  MAGIC   │  TYPE    │  NODE_ID  │  PAYLOAD_LEN           │
│  "ARCH"  │  1 byte  │  32 bytes │  4 bytes (uint32_BE)   │
│  4 bytes │          │ (Ed25519  │                        │
│          │          │  pub key) │                        │
├──────────┴──────────┴───────────┴────────────────────────┤
│  PAYLOAD (chiffré AES-256-GCM, longueur variable)        │
├──────────────────────────────────────────────────────────┤
│  HMAC-SHA256 SIGNATURE  (32 bytes)                       │
└──────────────────────────────────────────────────────────┘

En-tête fixe : 41 bytes  (4 + 1 + 32 + 4)
Signature     : 32 bytes (HMAC-SHA256)
Taille min    : 73 bytes
```

### Types de paquets

| Code   | Nom          | Usage                                         |
|--------|--------------|-----------------------------------------------|
| `0x01` | `HELLO`      | Annonce de présence UDP toutes les 30s        |
| `0x02` | `PEER_LIST`  | Liste des pairs connus (TCP unicast)          |
| `0x03` | `MSG`        | Message texte chiffré E2E                     |
| `0x04` | `CHUNK_REQ`  | Requête d'un bloc de fichier                  |
| `0x05` | `CHUNK_DATA` | Transfert d'un bloc de fichier                |
| `0x06` | `MANIFEST`   | Métadonnées d'un fichier (hash, nb chunks)   |
| `0x07` | `ACK`        | Acquittement                                  |
| `0x10` | `HANDSHAKE_INIT` | Initiation du handshake chiffré           |
| `0x11` | `HANDSHAKE_ACK`  | Confirmation handshake                    |
| `0x12` | `HANDSHAKE_AUTH` | Authentification Ed25519                  |
| `0xF0` | `PING`       | Keep-alive                                    |
| `0xF1` | `PONG`       | Réponse keep-alive                            |


## Guide de démo

```bash
# Génération des identités (une fois par machine)
python src/clé.py --name Alice
# Sur la machine B :
python src/clé.py --name Bob

# Terminal 1 — Lancer le nœud Alice (port 7777 + discovery UDP)
python src/cli.py start --port 7777

# Terminal 2 — Nœud Bob (même LAN ou localhost)
python src/cli.py start --port 7778

# Commandes CLI disponibles :
python src/cli.py peers                          # Liste les pairs découverts
python src/cli.py msg <NODE_ID> "Hello!"         # Envoie un message chiffré
python src/cli.py send <NODE_ID> fichier.zip     # Partage un fichier (chunking)
python src/cli.py download <FILE_ID>             # Télécharge un fichier par ID
python src/cli.py msg <ID> "@archipel-ai Résume" # Interroge l'assistant Gemini

# Interface Web Dashboard :
python src/web_ui.py   # Ouvrir http://localhost:8080
```

