"""
Archipel — Serveur Web UI (Sprint 4)
Lance un serveur HTTP local qui expose une interface de démo.
Usage: python src/web_ui.py --port 8080
"""

import sys
import os
import json
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault("GEMINI_API_KEY", "AIzaSyDuli0YtYel0jeW5Zcmk95L-X_qGoEtNts")

from crypto.identity import get_my_identity
from network.peer_table import PeerTable
from transfer.chunking import LocalStorage

HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Archipel — Interface de Démonstration</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0a0a0f;
  --surface: #111118;
  --surface2: #16161f;
  --border: #2a2a3a;
  --accent: #6c63ff;
  --accent2: #00d4aa;
  --accent3: #ff6b6b;
  --text: #e8e8f0;
  --text-dim: #6b6b80;
  --text-muted: #3a3a50;
  --success: #00d4aa;
  --warning: #ffbb00;
  --error: #ff6b6b;
  --mono: 'JetBrains Mono', monospace;
  --sans: 'Syne', sans-serif;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--mono);
  font-size: 13px;
  min-height: 100vh;
  line-height: 1.6;
}

/* Background texture */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 20% 20%, rgba(108,99,255,0.06) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 80%, rgba(0,212,170,0.04) 0%, transparent 60%);
  pointer-events: none;
  z-index: 0;
}

.wrapper { position: relative; z-index: 1; max-width: 960px; margin: 0 auto; padding: 40px 24px 80px; }

/* ── HEADER ── */
.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 48px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border);
}

.brand { display: flex; flex-direction: column; gap: 4px; }

.brand-name {
  font-family: var(--sans);
  font-size: 36px;
  font-weight: 800;
  letter-spacing: -1px;
  background: linear-gradient(135deg, #fff 0%, var(--accent) 50%, var(--accent2) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-sub {
  font-size: 11px;
  color: var(--text-dim);
  letter-spacing: 3px;
  text-transform: uppercase;
}

.node-info {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-end;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(0,212,170,0.08);
  border: 1px solid rgba(0,212,170,0.25);
  padding: 4px 12px;
  border-radius: 100px;
  font-size: 11px;
  color: var(--accent2);
  letter-spacing: 1px;
}

.status-pill::before {
  content: '';
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent2);
  box-shadow: 0 0 8px var(--accent2);
  animation: pulse 2s infinite;
}

@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

.node-id-display {
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 1px;
}

/* ── SECTION ── */
.section {
  margin-bottom: 32px;
  animation: fadeUp 0.4s ease both;
}

.section:nth-child(1) { animation-delay: 0.05s; }
.section:nth-child(2) { animation-delay: 0.10s; }
.section:nth-child(3) { animation-delay: 0.15s; }
.section:nth-child(4) { animation-delay: 0.20s; }
.section:nth-child(5) { animation-delay: 0.25s; }
.section:nth-child(6) { animation-delay: 0.30s; }
.section:nth-child(7) { animation-delay: 0.35s; }

@keyframes fadeUp {
  from { opacity:0; transform:translateY(16px); }
  to { opacity:1; transform:translateY(0); }
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.section-num {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  background: rgba(108,99,255,0.1);
  border: 1px solid rgba(108,99,255,0.25);
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  flex-shrink: 0;
}

.section-title {
  font-family: var(--sans);
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.5px;
}

.section-desc {
  font-size: 11px;
  color: var(--text-dim);
  margin-left: auto;
}

/* ── CARD ── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px 24px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s;
}

.card:hover { border-color: rgba(108,99,255,0.3); }

.card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(108,99,255,0.4), transparent);
  opacity: 0;
  transition: opacity 0.3s;
}

.card:hover::before { opacity: 1; }

/* ── FORM ELEMENTS ── */
.field { margin-bottom: 14px; }
.field:last-child { margin-bottom: 0; }

.field-row { display: flex; gap: 12px; }
.field-row .field { flex: 1; }

label {
  display: block;
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 6px;
}

input[type="text"],
input[type="number"],
input[type="file"],
select,
textarea {
  width: 100%;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-family: var(--mono);
  font-size: 12px;
  padding: 9px 12px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  -webkit-appearance: none;
}

input:focus, select:focus, textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(108,99,255,0.1);
}

input::placeholder, textarea::placeholder { color: var(--text-muted); }

select { cursor: pointer; }
select option { background: var(--surface2); }

textarea { resize: vertical; min-height: 70px; }

input[type="file"] {
  padding: 8px 12px;
  cursor: pointer;
  color: var(--text-dim);
}

input[type="file"]::-webkit-file-upload-button {
  background: rgba(108,99,255,0.15);
  border: 1px solid rgba(108,99,255,0.3);
  border-radius: 4px;
  color: var(--accent);
  font-family: var(--mono);
  font-size: 11px;
  padding: 4px 10px;
  cursor: pointer;
  margin-right: 10px;
}

/* ── BUTTONS ── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 500;
  padding: 9px 20px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.btn-primary {
  background: var(--accent);
  color: #fff;
  box-shadow: 0 0 20px rgba(108,99,255,0.3);
}
.btn-primary:hover { background: #7c74ff; transform: translateY(-1px); box-shadow: 0 4px 24px rgba(108,99,255,0.5); }

.btn-success {
  background: rgba(0,212,170,0.12);
  color: var(--accent2);
  border: 1px solid rgba(0,212,170,0.3);
}
.btn-success:hover { background: rgba(0,212,170,0.2); transform: translateY(-1px); }

.btn-danger {
  background: rgba(255,107,107,0.1);
  color: var(--error);
  border: 1px solid rgba(255,107,107,0.25);
}
.btn-danger:hover { background: rgba(255,107,107,0.18); }

.btn-ghost {
  background: transparent;
  color: var(--text-dim);
  border: 1px solid var(--border);
}
.btn-ghost:hover { border-color: var(--text-dim); color: var(--text); }

.btn-row { display: flex; gap: 10px; align-items: center; margin-top: 16px; flex-wrap: wrap; }

/* ── OUTPUT / RESPONSE ── */
.output {
  margin-top: 12px;
  padding: 12px 14px;
  background: #0d0d14;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-dim);
  min-height: 40px;
  white-space: pre-wrap;
  word-break: break-all;
  display: none;
  transition: all 0.3s;
}

.output.visible { display: block; }
.output.ok { border-color: rgba(0,212,170,0.3); color: var(--success); }
.output.err { border-color: rgba(255,107,107,0.3); color: var(--error); }
.output.info { border-color: rgba(108,99,255,0.3); color: #a09cf7; }

/* ── PEERS TABLE ── */
.peers-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 4px;
}

.peer-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: border-color 0.2s;
}

.peer-card:hover { border-color: rgba(0,212,170,0.3); }

.peer-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--accent2);
  box-shadow: 0 0 8px var(--accent2);
  flex-shrink: 0;
}

.peer-data { flex: 1; overflow: hidden; }
.peer-node-id { font-size: 11px; color: var(--accent2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.peer-meta { font-size: 10px; color: var(--text-dim); margin-top: 2px; }

.empty-state {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 12px;
}

/* ── FILES LIST ── */
.file-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.file-row:last-child { border-bottom: none; }

.file-info { flex: 1; overflow: hidden; }
.file-name-text { font-size: 12px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-id-text { font-size: 10px; color: var(--text-muted); margin-top: 2px; }

.progress-bar { height: 3px; background: var(--border); border-radius: 2px; margin: 4px 0; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 2px; transition: width 0.5s; }

.badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 100px;
  white-space: nowrap;
}
.badge-ok { background: rgba(0,212,170,0.1); color: var(--success); border: 1px solid rgba(0,212,170,0.2); }
.badge-pending { background: rgba(255,187,0,0.1); color: var(--warning); border: 1px solid rgba(255,187,0,0.2); }

/* ── LOG ── */
.log-panel {
  background: #070710;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  height: 140px;
  overflow-y: auto;
  font-size: 11px;
}

.log-panel::-webkit-scrollbar { width: 4px; }
.log-panel::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

.log-line { padding: 2px 0; color: var(--text-dim); display: flex; gap: 10px; }
.log-line .ts { color: var(--text-muted); flex-shrink: 0; }
.log-line .msg-ok { color: var(--success); }
.log-line .msg-err { color: var(--error); }
.log-line .msg-info { color: #a09cf7; }
.log-line .msg-warn { color: var(--warning); }

/* ── DIVIDER ── */
.divider { border: none; border-top: 1px solid var(--border); margin: 8px 0; }

/* ── SPRINT BADGE ── */
.sprint-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(108,99,255,0.1);
  border: 1px solid rgba(108,99,255,0.2);
  color: #a09cf7;
  margin-left: 8px;
  letter-spacing: 1px;
}

/* ── HINT ── */
.hint {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 6px;
  padding-left: 2px;
}

/* ── LOADING ── */
.loading { display: inline-block; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>
<div class="wrapper">

  <!-- HEADER -->
  <header class="header">
    <div class="brand">
      <div class="brand-name">ARCHIPEL</div>
      <div class="brand-sub">Protocole P2P Chiffré · Décentralisé · Zéro Connexion</div>
    </div>
    <div class="node-info">
      <div class="status-pill">NODE ONLINE</div>
      <div class="node-id-display" id="hdr-node-id">Node ID: chargement...</div>
      <div class="node-id-display">Port TCP: <span style="color:var(--accent2)">7777</span> · UDP: <span style="color:var(--accent2)">6000</span></div>
    </div>
  </header>

  <!-- 1. DÉMARRER LE NŒUD -->
  <div class="section">
    <div class="section-header">
      <div class="section-num">1</div>
      <div class="section-title">Démarrer le nœud <span class="sprint-tag">SPRINT 1</span></div>
      <div class="section-desc">archipel start</div>
    </div>
    <div class="card">
      <div class="field-row">
        <div class="field">
          <label>Port TCP d'écoute</label>
          <input type="number" id="start-port" value="7777" min="1024" max="65535">
        </div>
        <div class="field">
          <label>Mode IA</label>
          <select id="start-ai">
            <option value="on">Gemini activé</option>
            <option value="off">--no-ai (offline strict)</option>
          </select>
        </div>
      </div>
      <div class="btn-row">
        <button class="btn btn-primary" onclick="startNode()">▶ Démarrer le nœud</button>
        <button class="btn btn-danger" onclick="stopNode()">■ Arrêter</button>
      </div>
      <div id="out-start" class="output"></div>
      <p class="hint">Lance le serveur TCP sur 0.0.0.0:{port} + découverte UDP Multicast sur 239.255.42.99:6000</p>
    </div>
  </div>

  <!-- 2. STATUT -->
  <div class="section">
    <div class="section-header">
      <div class="section-num">2</div>
      <div class="section-title">Statut du nœud <span class="sprint-tag">SPRINT 0</span></div>
      <div class="section-desc">archipel status</div>
    </div>
    <div class="card">
      <div class="btn-row" style="margin-top:0">
        <button class="btn btn-success" onclick="getStatus()">◈ Afficher le statut</button>
      </div>
      <div id="out-status" class="output"></div>
    </div>
  </div>

  <!-- 3. PAIRS DÉCOUVERTS -->
  <div class="section">
    <div class="section-header">
      <div class="section-num">3</div>
      <div class="section-title">Pairs découverts <span class="sprint-tag">SPRINT 1</span></div>
      <div class="section-desc">archipel peers</div>
    </div>
    <div class="card">
      <div class="btn-row" style="margin-top:0">
        <button class="btn btn-success" onclick="listPeers()">⟳ Rafraîchir la peer table</button>
      </div>
      <div id="peers-container" style="margin-top:14px">
        <div class="empty-state">Cliquer sur "Rafraîchir" pour scanner le réseau</div>
      </div>
      <p class="hint">Découverte via HELLO UDP Multicast toutes les 30s · Timeout pair: 90s sans HELLO</p>
    </div>
  </div>

  <!-- 4. ENVOYER UN MESSAGE -->
  <div class="section">
    <div class="section-header">
      <div class="section-num">4</div>
      <div class="section-title">Envoyer un message chiffré <span class="sprint-tag">SPRINT 2</span></div>
      <div class="section-desc">archipel msg</div>
    </div>
    <div class="card">
      <div class="field">
        <label>Destinataire (Node ID)</label>
        <input type="text" id="msg-node-id" placeholder="b349e711c30902cf... (ou préfixe court)">
      </div>
      <div class="field">
        <label>Message <span style="color:var(--accent);font-size:10px">· préfixe @archipel-ai pour l'assistant Gemini</span></label>
        <textarea id="msg-text" placeholder="Salut depuis Archipel !&#10;@archipel-ai Résume le protocole Archipel en 2 phrases"></textarea>
      </div>
      <div class="btn-row">
        <button class="btn btn-primary" onclick="sendMsg()">🔒 Envoyer (chiffré E2E)</button>
        <button class="btn btn-ghost" onclick="document.getElementById('msg-text').value='@archipel-ai Explique le protocole Archipel en 2 phrases'">🤖 Test Gemini</button>
      </div>
      <div id="out-msg" class="output"></div>
      <p class="hint">Chiffrement X25519 + AES-256-GCM · Handshake à 3 temps · Forward Secrecy</p>
    </div>
  </div>

  <!-- 5. ENVOYER UN FICHIER -->
  <div class="section">
    <div class="section-header">
      <div class="section-num">5</div>
      <div class="section-title">Envoyer un fichier <span class="sprint-tag">SPRINT 3</span></div>
      <div class="section-desc">archipel send</div>
    </div>
    <div class="card">
      <div class="field">
        <label>Destinataire (Node ID)</label>
        <input type="text" id="send-node-id" placeholder="b349e711c30902cf...">
      </div>
      <div class="field">
        <label>Chemin du fichier</label>
        <input type="text" id="send-filepath" placeholder="test50mb.bin · gros_fichier.zip · rapport.pdf">
      </div>
      <div class="btn-row">
        <button class="btn btn-primary" onclick="sendFile()">📦 Envoyer le manifest</button>
        <button class="btn btn-ghost" onclick="document.getElementById('send-filepath').value='test50mb.bin'">Fichier test 50 Mo</button>
      </div>
      <div id="out-send" class="output"></div>
      <p class="hint">Découpe le fichier en chunks de 512 KB · Génère un manifest SHA-256 · Le pair lance le téléchargement</p>
    </div>
  </div>

  <!-- 6. FICHIERS DISPONIBLES -->
  <div class="section">
    <div class="section-header">
      <div class="section-num">6</div>
      <div class="section-title">Fichiers disponibles <span class="sprint-tag">SPRINT 3</span></div>
      <div class="section-desc">archipel receive</div>
    </div>
    <div class="card">
      <div class="btn-row" style="margin-top:0">
        <button class="btn btn-success" onclick="listFiles()">⟳ Afficher l'index local</button>
      </div>
      <div id="files-container" style="margin-top:14px">
        <div class="empty-state">Cliquer pour afficher les fichiers indexés</div>
      </div>
    </div>
  </div>

  <!-- 7. TÉLÉCHARGER UN FICHIER -->
  <div class="section">
    <div class="section-header">
      <div class="section-num">7</div>
      <div class="section-title">Télécharger un fichier <span class="sprint-tag">SPRINT 3</span></div>
      <div class="section-desc">archipel download</div>
    </div>
    <div class="card">
      <div class="field">
        <label>File ID (SHA-256 du fichier)</label>
        <input type="text" id="dl-file-id" placeholder="3ee008a438903184494e4568fe575136b096075c862b699a187a63293b0b2901">
      </div>
      <div class="btn-row">
        <button class="btn btn-primary" onclick="downloadFile()">⬇ Lancer le téléchargement</button>
      </div>
      <div id="out-dl" class="output"></div>
      <p class="hint">Pipeline parallèle · Vérification SHA-256 de chaque chunk · Fallback automatique si pair injoignable</p>
    </div>
  </div>

  <!-- 8. WEB OF TRUST -->
  <div class="section">
    <div class="section-header">
      <div class="section-num">8</div>
      <div class="section-title">Web of Trust <span class="sprint-tag">SPRINT 2</span></div>
      <div class="section-desc">archipel trust</div>
    </div>
    <div class="card">
      <div class="field">
        <label>Node ID à approuver</label>
        <input type="text" id="trust-node-id" placeholder="b349e711c30902cf...">
      </div>
      <div class="btn-row">
        <button class="btn btn-success" onclick="trustPeer()">✓ Approuver ce pair</button>
      </div>
      <div id="out-trust" class="output"></div>
      <p class="hint">TOFU (Trust On First Use) · Détection MITM · Signature Ed25519 permanente · Pas de CA centrale</p>
    </div>
  </div>

  <!-- LOG SYSTÈME -->
  <div class="section">
    <div class="section-header">
      <div class="section-num">9</div>
      <div class="section-title">Journal système</div>
    </div>
    <div class="card" style="padding:16px">
      <div class="log-panel" id="sys-log">
        <div class="log-line"><span class="ts">--:--:--</span><span class="msg-info">Archipel UI initialisée. Serveur: http://localhost:8080</span></div>
      </div>
    </div>
  </div>

</div>

<script>
  const API = 'http://localhost:8080';

  function ts() {
    return new Date().toTimeString().slice(0,8);
  }

  function sysLog(msg, type='info') {
    const log = document.getElementById('sys-log');
    const d = document.createElement('div');
    d.className = 'log-line';
    d.innerHTML = `<span class="ts">${ts()}</span><span class="msg-${type}">${msg}</span>`;
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
  }

  function showOut(id, msg, type='ok') {
    const el = document.getElementById(id);
    el.textContent = msg;
    el.className = `output visible ${type}`;
  }

  async function api(path, opts={}) {
    try {
      const r = await fetch(API + path, opts);
      return await r.json();
    } catch(e) {
      return { ok: false, error: 'Serveur injoignable — lancez python src/web_ui.py --port 8080' };
    }
  }

  async function startNode() {
    const port = document.getElementById('start-port').value;
    const ai = document.getElementById('start-ai').value;
    sysLog(`Démarrage du nœud sur port ${port}...`);
    showOut('out-start', `⏳ Démarrage en cours...\nCommande: python src/cli.py start --port ${port}${ai==='off'?' --no-ai':''}`, 'info');
    const r = await api('/api/status');
    if (r && r.node_id) {
      document.getElementById('hdr-node-id').textContent = 'Node ID: ' + r.node_id.slice(0,20) + '...';
      showOut('out-start', `✅ Nœud actif\nNode ID : ${r.node_id}\nPairs   : ${r.peers}\nFichiers: ${r.files}`, 'ok');
      sysLog(`Nœud démarré · ID: ${r.node_id.slice(0,16)}...`, 'ok');
    } else {
      showOut('out-start', '❌ ' + (r?.error || 'Erreur inconnue') + '\n\nLancez d\'abord:\npython src/cli.py start --port ' + port, 'err');
    }
  }

  async function stopNode() {
    showOut('out-start', 'Pour arrêter le nœud: Ctrl+C dans le terminal où tourne cli.py start', 'info');
  }

  async function getStatus() {
    sysLog('Requête statut nœud...');
    const r = await api('/api/status');
    if (r && r.node_id) {
      document.getElementById('hdr-node-id').textContent = 'Node ID: ' + r.node_id.slice(0,20) + '...';
      const txt = [
        '--- ARCHIPEL STATUS ---',
        `Node ID  : ${r.node_id}`,
        `Port TCP : 7777`,
        `Crypto   : Ed25519 + X25519 + AES-256-GCM`,
        `Trust    : TOFU / Web of Trust`,
        `Pairs    : ${r.peers} actif(s)`,
        `Fichiers : ${r.files} indexé(s)`,
        '-----------------------'
      ].join('\n');
      showOut('out-status', txt, 'ok');
      sysLog(`Statut récupéré · ${r.peers} pairs · ${r.files} fichiers`, 'ok');
    } else {
      showOut('out-status', '❌ ' + (r?.error || 'Nœud non démarré'), 'err');
    }
  }

  async function listPeers() {
    sysLog('Scan peer table...');
    const r = await api('/api/peers');
    const container = document.getElementById('peers-container');

    if (!r || r.error) {
      container.innerHTML = `<div class="empty-state" style="color:var(--error)">${r?.error || 'Erreur'}</div>`;
      return;
    }

    const peers = r.peers || {};
    const count = Object.keys(peers).length;

    if (count === 0) {
      container.innerHTML = '<div class="empty-state">Aucun pair découvert · Attendez les paquets HELLO UDP (30s)</div>';
      sysLog('Aucun pair trouvé', 'warn');
      return;
    }

    sysLog(`${count} pair(s) découvert(s)`, 'ok');

    // Populate peer selectors in other forms
    ['msg-node-id', 'send-node-id', 'trust-node-id'].forEach(id => {
      const el = document.getElementById(id);
      if (!el.value) el.placeholder = Object.keys(peers)[0] + ' (auto-détecté)';
    });
    document.getElementById('dl-file-id').placeholder = '3ee008a438903184...';

    let html = `<div class="peers-grid">`;
    Object.entries(peers).forEach(([id, p]) => {
      html += `
        <div class="peer-card">
          <div class="peer-dot"></div>
          <div class="peer-data">
            <div class="peer-node-id">${id.slice(0,24)}...</div>
            <div class="peer-meta">${p.ip}:${p.tcp_port} · vu: ${new Date(p.last_seen*1000).toLocaleTimeString()}</div>
          </div>
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
  }

  async function sendMsg() {
    const nodeId = document.getElementById('msg-node-id').value.trim();
    const text = document.getElementById('msg-text').value.trim();
    if (!nodeId) { showOut('out-msg', '❌ Entrez un Node ID destinataire', 'err'); return; }
    if (!text) { showOut('out-msg', '❌ Entrez un message', 'err'); return; }

    showOut('out-msg', '⏳ Chiffrement et envoi en cours...', 'info');
    sysLog(`Envoi message → ${nodeId.slice(0,16)}...`);

    const r = await api('/api/msg', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ node_id: nodeId, text })
    });

    if (r && r.ok) {
      let out = `✅ Message chiffré envoyé\n\nDestinataire : ${nodeId.slice(0,20)}...\nMessage      : ${text}`;
      if (r.ai_reply) out += `\n\n🤖 Gemini AI :\n${r.ai_reply}`;
      showOut('out-msg', out, 'ok');
      sysLog('Message envoyé avec succès', 'ok');
    } else {
      showOut('out-msg', '❌ ' + (r?.error || 'Échec'), 'err');
      sysLog('Échec envoi message: ' + (r?.error || ''), 'err');
    }
  }

  async function sendFile() {
    const nodeId = document.getElementById('send-node-id').value.trim();
    const filepath = document.getElementById('send-filepath').value.trim();
    if (!nodeId) { showOut('out-send', '❌ Entrez un Node ID destinataire', 'err'); return; }
    if (!filepath) { showOut('out-send', '❌ Entrez le chemin du fichier', 'err'); return; }

    showOut('out-send', '⏳ Découpe en chunks et envoi du manifest...', 'info');
    sysLog(`Envoi fichier: ${filepath} → ${nodeId.slice(0,16)}...`);

    const r = await api('/api/send', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ node_id: nodeId, filename: filepath })
    });

    if (r && r.ok) {
      showOut('out-send', `✅ Manifest envoyé avec succès !\n\nFichier      : ${filepath}\nDestinataire : ${nodeId.slice(0,20)}...\n\nLe pair va initier le téléchargement en arrière-plan.\nUtilisez "archipel receive" pour suivre la progression.`, 'ok');
      sysLog(`Manifest envoyé: ${filepath}`, 'ok');
    } else {
      showOut('out-send', '❌ ' + (r?.error || 'Échec'), 'err');
      sysLog('Échec envoi fichier: ' + (r?.error || ''), 'err');
    }
  }

  async function listFiles() {
    sysLog('Chargement index fichiers...');
    const r = await api('/api/files');
    const container = document.getElementById('files-container');

    if (!r || r.error) {
      container.innerHTML = `<div class="empty-state" style="color:var(--error)">${r?.error || 'Erreur'}</div>`;
      return;
    }

    const files = r.files || {};
    if (Object.keys(files).length === 0) {
      container.innerHTML = '<div class="empty-state">Aucun fichier indexé</div>';
      sysLog('Index vide', 'warn');
      return;
    }

    sysLog(`${Object.keys(files).length} fichier(s) indexé(s)`, 'ok');
    let html = '';
    Object.entries(files).forEach(([id, f]) => {
      const badge = f.pct === 100
        ? '<span class="badge badge-ok">✅ Complet</span>'
        : `<span class="badge badge-pending">⏳ ${f.pct}%</span>`;
      html += `
        <div class="file-row">
          <div class="file-info">
            <div class="file-name-text">${f.name}</div>
            <div class="file-id-text">${id.slice(0,32)}...</div>
            <div class="progress-bar"><div class="progress-fill" style="width:${f.pct}%"></div></div>
            <div class="file-id-text">${f.chunks_have}/${f.nb_chunks} chunks</div>
          </div>
          ${badge}
          ${f.pct < 100 ? `<button class="btn btn-ghost" onclick="document.getElementById('dl-file-id').value='${id}';document.getElementById('dl-file-id').scrollIntoView({behavior:'smooth'})" style="font-size:10px;padding:5px 10px">↓ DL</button>` : ''}
        </div>`;
    });
    container.innerHTML = html;
  }

  async function downloadFile() {
    const fileId = document.getElementById('dl-file-id').value.trim();
    if (!fileId) { showOut('out-dl', '❌ Entrez un File ID', 'err'); return; }

    showOut('out-dl', '⏳ Lancement du téléchargement...', 'info');
    sysLog(`Download: ${fileId.slice(0,16)}...`);

    const r = await api('/api/download', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ file_id: fileId })
    });

    if (r && r.ok) {
      showOut('out-dl', `✅ Téléchargement lancé en arrière-plan\n\nFile ID : ${fileId}\n\nVérification SHA-256 de chaque chunk activée.\nUtilisez "Fichiers disponibles" pour suivre la progression.`, 'ok');
      sysLog('Téléchargement démarré', 'ok');
    } else {
      showOut('out-dl', '❌ ' + (r?.error || 'Pair origine injoignable'), 'err');
      sysLog('Échec download: ' + (r?.error || ''), 'err');
    }
  }

  async function trustPeer() {
    const nodeId = document.getElementById('trust-node-id').value.trim();
    if (!nodeId) { showOut('out-trust', '❌ Entrez un Node ID', 'err'); return; }

    sysLog(`Trust: ${nodeId.slice(0,16)}...`);
    const r = await api('/api/trust', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ node_id: nodeId })
    });

    if (r && r.ok) {
      showOut('out-trust', `✅ Pair approuvé dans le Web of Trust\n\nNode ID   : ${nodeId}\nMéthode   : TOFU (Trust On First Use)\nSignature : Ed25519 permanente enregistrée\nStatut    : Connexions futures vérifiées (anti-MITM)`, 'ok');
      sysLog('Pair approuvé dans Web of Trust', 'ok');
    } else {
      showOut('out-trust', '❌ ' + (r?.error || 'Échec'), 'err');
    }
  }

  // Init
  (async () => {
    const r = await api('/api/status');
    if (r && r.node_id) {
      document.getElementById('hdr-node-id').textContent = 'Node ID: ' + r.node_id.slice(0,20) + '...';
      sysLog(`Nœud connecté · ${r.peers} pairs · ${r.files} fichiers`, 'ok');
    } else {
      sysLog('Serveur non démarré · Lancez: python src/web_ui.py --port 8080', 'warn');
    }
  })();
</script>
</body>
</html>"""


class ArchipelHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silence HTTP logs

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/' or parsed.path == '/index.html':
            body = HTML.encode()
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

                if not target:
                    self.send_json({'ok': False, 'error': 'Peer not found'})
                    return

                import socket as sock_mod
                from crypto.handshake import perform_handshake_initiator
                from crypto.messaging import send_encrypted_message
                s = sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_STREAM)
                s.settimeout(10)
                s.connect((target['ip'], target['tcp_port']))
                session = perform_handshake_initiator(s, my_id)
                send_encrypted_message(s, session, my_id, text)
                s.close()

                ai_reply = None
                if '@archipel-ai' in text:
                    from messaging.gemini_ai import query_gemini
                    ai_reply = query_gemini('', text)

                self.send_json({'ok': True, 'ai_reply': ai_reply})
            except Exception as e:
                self.send_json({'ok': False, 'error': str(e)})

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


def run(port=8080):
    server = HTTPServer(('0.0.0.0', port), ArchipelHandler)
    print(f"[UI] 🌐 Interface web disponible → http://localhost:{port}")
    print(f"[UI] 🌐 Depuis Machine B      → http://172.20.10.3:{port}")
    server.serve_forever()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    run(args.port)