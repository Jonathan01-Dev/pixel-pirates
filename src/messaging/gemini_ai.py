"""
Archipel — Module 4.2 : Intégration Gemini API
Assistant IA fonctionnant de manière isolée pour le réseau P2P.
"""

import os
import json
import urllib.request
import urllib.error

<<<<<<< HEAD
def query_gemini(conversation_context: list, user_query: str) -> str:
    """
    Interroge l'API Gemini avec un contexte de conversation.
    conversation_context: Liste des derniers messages [(sender, text), ...]
    """
    # Clé API depuis la variable d'environnement (ex: GEMINI_API_KEY)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
=======
def query_gemini(conversation_context: str, user_query: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY") or "AIzaSyDuli0YtYel0jeW5Zcmk95L-X_qGoEtNts"
    print(f"DEBUG clé: '{api_key}'")
>>>>>>> origin/main
    if not api_key:
        return "[IA] Erreur: Clé API Gemini non configurée."

    # v1beta + gemini-2.5-flash (modèle actuel)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # Construction du prompt avec historique
    history_str = "\n".join([f"- {s}: {t}" for s, t in conversation_context])
    prompt = f"Tu es l'assistant du protocole P2P Archipel. Voici le contexte de la conversation récente:\n{history_str}\n\nQuestion de l'utilisateur:\n{user_query}"
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["candidates"][0]["content"]["parts"][0]["text"]
            
    except urllib.error.HTTPError as e:
        # Masquer la clé pour les logs publics
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if api_key else "NONE"
        error_body = ""
        try:
            error_body = e.read().decode()
        except:
            pass
        return f"[IA] Erreur API {e.code}: {e.reason} (Key: {masked_key})\n{error_body}"
    except Exception as e:
        return f"[IA] Erreur système: {e}"

if __name__ == "__main__":
    test_context = [("Alice", "Bonjour"), ("Bob", "Salut Archipel")]
    print(query_gemini(test_context, "Qui est Alice ?"))
