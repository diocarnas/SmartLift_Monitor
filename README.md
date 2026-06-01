# API de Monitoramento de Filas de Elevadores

Sistema de visão computacional que detecta pessoas em filas de elevadores via câmera e expõe os dados em tempo real através de uma API REST.

---

## Tecnologias

- **Python 3.10+**
- **YOLOv8** — detecção de pessoas em tempo real
- **OpenCV** — captura de vídeo da câmera
- **Flask** — servidor da API REST
- **HTML/CSS/JS** — painel web de visualização

---

## Instalação

```bash
pip install -r requirements.txt
```

---

## Como usar

```bash
python contador.py
```

Abra o navegador em `http://localhost:5000` para ver o painel web.

### Variáveis de ambiente (opcionais)

| Variável | Padrão | Descrição |
|---|---|---|
| `API_KEY` | `minha-chave-secreta` | Chave de autenticação da API |
| `PORT` | `5000` | Porta do servidor |
| `TEMPO_PESSOA` | `15` | Segundos estimados por pessoa na fila |
| `RATE_LIMIT_MAX` | `60` | Máximo de requisições por minuto por IP |

Exemplo:
```bash
API_KEY=abc123 PORT=8080 python contador.py
```

---

## Endpoints

Todos os endpoints (exceto `/` e `/health`) exigem o header:
```
X-API-Key: <sua chave>
```

| Método | Endpoint | Descrição | Auth |
|---|---|---|---|
| GET | `/` | Painel web | Não |
| GET | `/health` | Health check | Não |
| GET | `/v1/status` | Status completo das duas filas | Sim |
| GET | `/v1/elevador/a` | Dados do Elevador A | Sim |
| GET | `/v1/elevador/b` | Dados do Elevador B | Sim |
| GET | `/v1/recomendado` | Elevador recomendado | Sim |

---

## Exemplo de resposta — `/v1/status`

```json
{
  "elevador_A": {
    "fila": 3,
    "tempo_espera_segundos": 45,
    "tempo_espera_texto": "45s"
  },
  "elevador_B": {
    "fila": 7,
    "tempo_espera_segundos": 105,
    "tempo_espera_texto": "1 min"
  },
  "recomendado": "A",
  "ultima_atualizacao": "2026-05-28T14:32:01.123456"
}
```

---

## Exemplo de requisição

```bash
curl -H "X-API-Key: minha-chave-secreta" http://localhost:5000/v1/status
```

---

## Segurança

- Autenticação via `X-API-Key` em todos os endpoints protegidos
- Rate limiting: máximo de 60 requisições por minuto por IP
- CORS restrito à origem local
- Logs de acesso e tentativas negadas em `elevadores.log`

---

## Integração multidisciplinar

| Área | Tecnologia |
|---|---|
| Visão Computacional | YOLOv8 + OpenCV |
| Desenvolvimento de API | Flask REST |
| Interface Web | HTML + CSS + JS |

---

## Estrutura do projeto

```
.
├── contador.py       # API + visão computacional
├── painel_web.html   # Painel web
├── requirements.txt  # Dependências
├── README.md         # Documentação
└── elevadores.log    # Gerado automaticamente ao rodar
```
