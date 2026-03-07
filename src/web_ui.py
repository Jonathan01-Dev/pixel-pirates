import sys
import os
import io

# Fix encodage Windows (évite 'charmap' codec errors avec accents/emojis)
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, OSError):
            pass

import json
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Définir GEMINI_API_KEY pour activer l'IA (https://aistudio.google.com/apikey)
os.environ.setdefault("GEMINI_API_KEY", "AIzaSyDuli0YtYel0jeW5Zcmk95L-X_qGoEtNts")

from crypto.identity import get_my_identity
from network.peer_table import PeerTable
from transfer.chunking import LocalStorage

# Module 4.2 : Gestion du contexte de conversation
CONVERSATION_HISTORY = []
MAX_HISTORY = 10
AI_DISABLED = False

def safe_ascii(s):
    """Convertit en ASCII pour eviter charmap sur Windows."""
    if s is None:
        return ""
    try:
        return str(s).encode('ascii', 'replace').decode('ascii')
    except Exception:
        return ""

def get_html():
    try:
        with open(r"c:\wamp64\www\pixel-pirates\src\archipel_ui.html", "r", encoding="utf-8") as html_f:
            return html_f.read()
    except Exception as e:
        return f"<h1>Error loading UI: {e}</h1>"




class ArchipelHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silence HTTP logs

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=True).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/' or parsed.path == '/index.html':
            body = get_html().encode("utf-8")
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == '/api/status':
            _, my_id = get_my_identity()
            pt = PeerTable()
            st = LocalStorage()
            self.send_json({
                'node_id': my_id,
                'peers': len(pt.get_alive()),
                'files': len(st.files)
            })

        elif parsed.path == '/api/peers':
            pt = PeerTable()
            pt.clean_old_peers()
            self.send_json({'peers': pt.peers})

        elif parsed.path == '/api/files':
            st = LocalStorage()
            files = {}
            for fid, finfo in st.files.items():
                m = finfo['manifest']
                nb = m.get('nb_chunks', 1)
                have = len(finfo.get('chunks_have', []))
                files[fid] = {
                    'name': m.get('filename', '?'),
                    'nb_chunks': nb,
                    'chunks_have': have,
                    'pct': int(have / nb * 100) if nb > 0 else 0
                }
            self.send_json({'files': files})

        else:
            self.send_json({'error': 'not found'}, 404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        parsed = urlparse(self.path)

        if parsed.path == '/api/msg':
            try:
                node_id = body.get('node_id', '')
                text = body.get('text', '')
                signing_key, my_id = get_my_identity()
                pt = PeerTable()
                target = pt.peers.get(node_id)
                if not target:
                    matches = [uid for uid in pt.peers if uid.startswith(node_id)]
                    if matches:
                        target = pt.peers[matches[0]]
                        node_id = matches[0]

                # Déclenchement via @archipel-ai ou /ask (Module 4.2)
                is_ai_trigger = '@archipel-ai' in text or '/ask' in text
                send_error = None

                if target:
                    try:
                        import socket as sock_mod
                        from crypto.handshake import perform_handshake_initiator
                        from crypto.messaging import send_encrypted_message
                        s = sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_STREAM)
                        s.settimeout(5)
                        s.connect((target['ip'], target['tcp_port']))
                        session = perform_handshake_initiator(s, my_id)
                        send_encrypted_message(s, session, my_id, text)
                        s.close()
                    except Exception as e:
                        send_error = str(e)
                else:
                    send_error = "Peer not found (Solo Mode)"
                
                # Module 4.2 : Toujours enregistrer dans l'historique pour le contexte IA
                if not AI_DISABLED:
                    CONVERSATION_HISTORY.append(("User", text))
                    if len(CONVERSATION_HISTORY) > MAX_HISTORY * 2:
                        CONVERSATION_HISTORY[:] = CONVERSATION_HISTORY[-MAX_HISTORY * 2:]

                ai_reply = None
                if is_ai_trigger and not AI_DISABLED:
                    from messaging.gemini_ai import query_gemini
                    try:
                        ai_reply = query_gemini(CONVERSATION_HISTORY[:-1], text)
                        ai_reply = safe_ascii(ai_reply)
                        CONVERSATION_HISTORY.append(("Gemini", ai_reply))
                        if len(CONVERSATION_HISTORY) > MAX_HISTORY * 2:
                            CONVERSATION_HISTORY[:] = CONVERSATION_HISTORY[-MAX_HISTORY * 2:]
                    except Exception as e:
                        ai_reply = safe_ascii(f"[IA] Erreur: {e}")

                self.send_json({
                    'ok': True,
                    'ai_reply': ai_reply,
                    'send_status': 'ok' if not send_error and target else 'local_only',
                    'send_error': send_error if not target else None
                })
            except Exception as e:
                self.send_json({'ok': False, 'error': safe_ascii(str(e))})

        elif parsed.path == '/api/send':
            try:
                node_id = body.get('node_id', '')
                filename = body.get('filename', '')
                signing_key, my_id = get_my_identity()
                pt = PeerTable()
                target = pt.peers.get(node_id)
                if not target:
                    matches = [uid for uid in pt.peers if uid.startswith(node_id)]
                    if matches:
                        target = pt.peers[matches[0]]

                if not target:
                    self.send_json({'ok': False, 'error': 'Peer not found'})
                    return

                from transfer.chunking import build_manifest, LocalStorage as LS
                from crypto.handshake import perform_handshake_initiator
                from crypto.messaging import send_encrypted_payload
                from network.packet import TYPE_MANIFEST
                import socket as sock_mod

                st = LS()
                manifest = build_manifest(filename, my_id, signing_key)
                st.add_local_file(filename, manifest)

                s = sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_STREAM)
                s.settimeout(10)
                s.connect((target['ip'], target['tcp_port']))
                session = perform_handshake_initiator(s, my_id)
                send_encrypted_payload(s, session, TYPE_MANIFEST, my_id, manifest)
                s.close()
                self.send_json({'ok': True})
            except Exception as e:
                self.send_json({'ok': False, 'error': str(e)})

        elif parsed.path == '/api/trust':
            try:
                from crypto.trust_store import TrustStore
                _, my_id = get_my_identity()
                store = TrustStore()
                store.sign_peer(body.get('node_id', ''), my_id)
                self.send_json({'ok': True})
            except Exception as e:
                self.send_json({'ok': False, 'error': str(e)})

        elif parsed.path == '/api/download':
            try:
                file_id = body.get('file_id', '')
                st = LocalStorage()
                file_info = st.files.get(file_id)
                if not file_info:
                    self.send_json({'ok': False, 'error': 'File not found'})
                    return
                signing_key, my_id = get_my_identity()
                pt = PeerTable()
                manifest = file_info['manifest']
                sender_id = manifest['sender_id']
                target = pt.peers.get(sender_id)
                if not target:
                    self.send_json({'ok': False, 'error': 'Sender not reachable'})
                    return
                from transfer.transfer_manager import TransferManager
                mgr = TransferManager(st)
                mgr.fetch_file(manifest, target['ip'], target['tcp_port'])
                self.send_json({'ok': True})
            except Exception as e:
                self.send_json({'ok': False, 'error': str(e)})

        else:
            self.send_json({'error': 'not found'}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def run(port=8080, no_ai=False):
    global AI_DISABLED
    AI_DISABLED = no_ai
    server = HTTPServer(('0.0.0.0', port), ArchipelHandler)
    print(f"[UI] Interface web -> http://localhost:{port}")
    if no_ai:
        print("[UI] Mode IA desactive (--no-ai)")
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"[UI] Depuis le reseau local -> http://{local_ip}:{port}")
    except:
        pass
    server.serve_forever()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--no-ai', action='store_true', help="Désactiver l'assistant IA")
    args = parser.parse_args()
    run(args.port, args.no_ai)
