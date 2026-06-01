"""
API de Monitoramento de Filas de Elevadores
Versão: 1.0.0
Descrição: Detecta pessoas via câmera (YOLOv8) e expõe os dados em tempo real via REST API.
"""

import cv2
import threading
import logging
import os
import time
from datetime import datetime

from ultralytics import YOLO
from flask import Flask, jsonify, send_file, request, abort
from flask_cors import CORS
from functools import wraps

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

API_KEY        = os.getenv("API_KEY", "minha-chave-secreta")
PORT           = int(os.getenv("PORT", 5000))
TEMPO_PESSOA   = int(os.getenv("TEMPO_PESSOA", 15))   # segundos por pessoa
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", 60)) # requisições por minuto

EL_A = {"x1": 50,  "y1": 150, "x2": 300, "y2": 450}
EL_B = {"x1": 340, "y1": 150, "x2": 590, "y2": 450}

# ==============================================================================
# LOGS
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("elevadores.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ==============================================================================
# ESTADO COMPARTILHADO
# ==============================================================================

dados_filas = {
    "elevador_A": {"fila": 0, "tempo_espera_segundos": 0, "tempo_espera_texto": "0s"},
    "elevador_B": {"fila": 0, "tempo_espera_segundos": 0, "tempo_espera_texto": "0s"},
    "recomendado": "igual",
    "ultima_atualizacao": None
}
lock = threading.Lock()

# Rate limiting simples (por IP)
requisicoes = {}
requisicoes_lock = threading.Lock()

# ==============================================================================
# FLASK
# ==============================================================================

app = Flask(__name__)
CORS(app,
     origins="*",
     allow_headers=["X-API-Key", "Content-Type"],
     methods=["GET", "OPTIONS"])


def requer_api_key(f):
    """Decorator: exige header X-API-Key válido (ignora preflight OPTIONS)."""
    @wraps(f)
    def decorado(*args, **kwargs):
        if request.method == "OPTIONS":
            return "", 200
        chave = request.headers.get("X-API-Key")
        if chave != API_KEY:
            log.warning(f"Acesso negado: chave inválida de {request.remote_addr}")
            abort(401, description="API Key inválida ou ausente.")
        return f(*args, **kwargs)
    return decorado


def rate_limit(f):
    """Decorator: limita requisições por IP (máx por minuto)."""
    @wraps(f)
    def decorado(*args, **kwargs):
        ip = request.remote_addr
        agora = time.time()
        with requisicoes_lock:
            historico = [t for t in requisicoes.get(ip, []) if agora - t < 60]
            if len(historico) >= RATE_LIMIT_MAX:
                log.warning(f"Rate limit atingido: {ip}")
                abort(429, description="Muitas requisições. Tente novamente em 1 minuto.")
            historico.append(agora)
            requisicoes[ip] = historico
        return f(*args, **kwargs)
    return decorado


def resposta_erro(mensagem, codigo):
    return jsonify({
        "erro": mensagem,
        "codigo": codigo,
        "timestamp": datetime.now().isoformat()
    }), codigo


@app.errorhandler(401)
def nao_autorizado(e):
    return resposta_erro(str(e.description), 401)

@app.errorhandler(429)
def muitas_requisicoes(e):
    return resposta_erro(str(e.description), 429)

@app.errorhandler(404)
def nao_encontrado(e):
    return resposta_erro("Endpoint não encontrado.", 404)


# ------------------------------------------------------------------------------
# ROTAS
# ------------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Serve o painel web."""
    html_path = os.path.join(os.path.dirname(__file__), "painel_web.html")
    return send_file(html_path)


@app.route("/v1/status", methods=["GET", "OPTIONS"])
@rate_limit
@requer_api_key
def status():
    """
    Retorna o status completo das filas.
    ---
    Headers obrigatórios:
      X-API-Key: <sua chave>
    Resposta:
      {
        "elevador_A": { "fila": int, "tempo_espera_segundos": int, "tempo_espera_texto": str },
        "elevador_B": { "fila": int, "tempo_espera_segundos": int, "tempo_espera_texto": str },
        "recomendado": "A" | "B" | "igual",
        "ultima_atualizacao": str (ISO 8601)
      }
    """
    with lock:
        log.info(f"GET /v1/status — {request.remote_addr}")
        return jsonify(dados_filas)


@app.route("/v1/elevador/a", methods=["GET", "OPTIONS"])
@rate_limit
@requer_api_key
def elevador_a():
    """Retorna dados do Elevador A."""
    with lock:
        return jsonify(dados_filas["elevador_A"])


@app.route("/v1/elevador/b", methods=["GET", "OPTIONS"])
@rate_limit
@requer_api_key
def elevador_b():
    """Retorna dados do Elevador B."""
    with lock:
        return jsonify(dados_filas["elevador_B"])


@app.route("/v1/recomendado", methods=["GET", "OPTIONS"])
@rate_limit
@requer_api_key
def recomendado():
    """Retorna qual elevador usar."""
    with lock:
        return jsonify({"recomendado": dados_filas["recomendado"]})


@app.route("/health", methods=["GET"])
def health():
    """Health check público — sem autenticação."""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


def iniciar_api():
    log.info(f"API iniciada em http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, use_reloader=False, threaded=True)


# ==============================================================================
# VISÃO COMPUTACIONAL
# ==============================================================================

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    log.error("Câmera não encontrada. Verifique a conexão.")
    exit(1)

thread_api = threading.Thread(target=iniciar_api, daemon=True)
thread_api.start()

log.info("Sistema iniciado. Pressione Ctrl+C para encerrar.")

try:
    while cap.isOpened():
        sucesso, frame = cap.read()
        if not sucesso:
            log.warning("Frame não capturado. Tentando novamente...")
            time.sleep(0.1)
            continue

        resultados = model(frame, classes=[0], verbose=False)

        fila_A, fila_B = 0, 0

        for caixa in resultados[0].boxes:
            x1, y1, x2, y2 = map(int, caixa.xyxy[0])
            cx = int((x1 + x2) / 2)
            cy = int(y2)
            if EL_A["x1"] < cx < EL_A["x2"] and EL_A["y1"] < cy < EL_A["y2"]:
                fila_A += 1
            elif EL_B["x1"] < cx < EL_B["x2"] and EL_B["y1"] < cy < EL_B["y2"]:
                fila_B += 1

        tempo_A = fila_A * TEMPO_PESSOA
        tempo_B = fila_B * TEMPO_PESSOA
        txt_A = f"{tempo_A}s" if tempo_A < 60 else f"{tempo_A // 60} min"
        txt_B = f"{tempo_B}s" if tempo_B < 60 else f"{tempo_B // 60} min"
        rec   = "A" if fila_A < fila_B else ("B" if fila_B < fila_A else "igual")

        with lock:
            dados_filas["elevador_A"] = {"fila": fila_A, "tempo_espera_segundos": tempo_A, "tempo_espera_texto": txt_A}
            dados_filas["elevador_B"] = {"fila": fila_B, "tempo_espera_segundos": tempo_B, "tempo_espera_texto": txt_B}
            dados_filas["recomendado"] = rec
            dados_filas["ultima_atualizacao"] = datetime.now().isoformat()

except KeyboardInterrupt:
    log.info("Encerrando sistema...")
finally:
    cap.release()
    log.info("Câmera liberada.")