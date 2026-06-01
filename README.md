# 🛗 API de Monitoramento de Filas de Elevadores

Sistema de visão computacional que detecta pessoas em tempo real via câmera e expõe os dados de fila através de uma REST API, permitindo que painéis e outros sistemas consultem qual elevador está menos cheio.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Integração Multidisciplinar](#integração-multidisciplinar)
- [Requisitos](#requisitos)
- [Instalação e Execução](#instalação-e-execução)
- [Endpoints da API](#endpoints-da-api)
- [Autenticação](#autenticação)
- [Rate Limiting](#rate-limiting)
- [Segurança](#segurança)
- [Painel Web](#painel-web)
- [Configuração via Variáveis de Ambiente](#configuração-via-variáveis-de-ambiente)
- [Decisões de Design](#decisões-de-design)
- [Ciclo de Vida e Operação](#ciclo-de-vida-e-operação)

---

## Visão Geral

```
Câmera → YOLOv8 (detecção) → contador.py → REST API → painel_web.html
                                                      → qualquer cliente HTTP
```

O sistema roda localmente e atualiza os dados de fila a cada frame capturado. A API é o **contrato** entre a visão computacional e qualquer sistema que precise saber o estado das filas.

---

## Arquitetura

### Estilo arquitetural: REST

A API segue o estilo REST com os seguintes princípios:

| Princípio | Implementação |
|-----------|--------------|
| Interface uniforme | Todos os endpoints retornam JSON com estrutura documentada |
| Sem estado (stateless) | Cada requisição contém tudo que o servidor precisa (API Key no header) |
| Sistema em camadas | Cliente → API Flask → Estado compartilhado (thread-safe) ← Thread de visão |
| Recurso identificável por URL | `/v1/elevador/a`, `/v1/elevador/b`, `/v1/recomendado` |

### Versionamento

Todos os endpoints funcionais estão sob `/v1/`. Isso garante que, ao evoluir a API para `/v2/`, clientes existentes **não quebram**.

### Concorrência

Duas threads rodam simultaneamente:
- **Thread principal**: captura frames e atualiza o estado.
- **Thread da API**: serve requisições HTTP.

O acesso ao estado compartilhado é protegido por `threading.Lock()`, evitando condições de corrida.

```python
# Escrita (thread de visão computacional)
with lock:
    dados_filas["elevador_A"] = { ... }

# Leitura (thread da API)
with lock:
    return jsonify(dados_filas)
```

---

## Integração Multidisciplinar

Este projeto integra **quatro áreas**:

### 1. Visão Computacional (IA)
- Modelo **YOLOv8n** (Ultralytics) para detecção de pessoas (classe 0 do COCO dataset).
- Regiões de interesse (ROIs) definidas por coordenadas para cada elevador.
- Inferência em tempo real, frame a frame.

### 2. Engenharia de Software / APIs
- REST API com Flask, versionamento de rota, tratamento de erros padronizado.
- Decorators reutilizáveis para autenticação e rate limiting.
- Documentação OpenAPI 3.0 (`openapi.yaml`).

### 3. Redes e Segurança
- CORS configurado explicitamente.
- Autenticação via API Key (header `X-API-Key`).
- Rate limiting por IP para proteção contra abuso.
- Variáveis de ambiente para segredos (sem hardcode em produção).

### 4. Interface e Experiência do Usuário
- Painel web responsivo com atualização automática a cada 1,5 segundo.
- Indicação visual do elevador recomendado e diferença de filas.
- Status de conexão com a API em tempo real.

---

## Requisitos

- Python 3.9+
- Webcam ou câmera USB
- Dependências:

```bash
pip install flask flask-cors ultralytics opencv-python
```

---

## Instalação e Execução

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/elevadores-api
cd elevadores-api

# 2. Instale as dependências
pip install flask flask-cors ultralytics opencv-python

# 3. (Opcional) Configure variáveis de ambiente
export API_KEY="sua-chave-segura-aqui"
export PORT=5000
export TEMPO_PESSOA=15

# 4. Execute
python contador.py
```

O YOLOv8 fará o download automático do modelo `yolov8n.pt` na primeira execução (~6 MB).

Acesse o painel em: **http://localhost:5000**

---

## Endpoints da API

A documentação completa está no arquivo `openapi.yaml` (compatível com Swagger UI / Redoc).

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-----------|
| GET | `/health` | ❌ | Health check público |
| GET | `/` | ❌ | Painel web |
| GET | `/v1/status` | ✅ | Status completo de ambas as filas |
| GET | `/v1/elevador/a` | ✅ | Dados do Elevador A |
| GET | `/v1/elevador/b` | ✅ | Dados do Elevador B |
| GET | `/v1/recomendado` | ✅ | Qual elevador usar agora |

### Exemplo de requisição

```bash
curl -H "X-API-Key: minha-chave-secreta" http://localhost:5000/v1/status
```

### Exemplo de resposta (`/v1/status`)

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
  "ultima_atualizacao": "2025-06-01T14:32:10.123456"
}
```

---

## Autenticação

Todos os endpoints `/v1/*` exigem o header `X-API-Key`.

```
X-API-Key: minha-chave-secreta
```

Sem a chave ou com chave inválida, a API retorna `401`:

```json
{
  "erro": "API Key inválida ou ausente.",
  "codigo": 401,
  "timestamp": "2025-06-01T14:00:00.000000"
}
```

> **Em produção**: defina `API_KEY` via variável de ambiente. Nunca coloque a chave real no código-fonte.

---

## Rate Limiting

Máximo de **60 requisições por minuto por IP**. Ao exceder, retorna `429`:

```json
{
  "erro": "Muitas requisições. Tente novamente em 1 minuto.",
  "codigo": 429,
  "timestamp": "2025-06-01T14:00:00.000000"
}
```

A janela de controle é deslizante de 60 segundos, implementada em memória com `threading.Lock`.

---

## Segurança

| Mecanismo | Implementação |
|-----------|--------------|
| Autenticação | API Key via header HTTP |
| Rate limiting | 60 req/min por IP (proteção a DoS simples) |
| CORS | `flask-cors` com `origins="*"` (restringir em produção) |
| Preflight OPTIONS | Respondido automaticamente sem exigir API Key |
| Segredos | Carregados via `os.getenv()`, com fallback para desenvolvimento |
| Logs de segurança | Tentativas inválidas registradas com IP do solicitante |

### ⚠️ Ponto de atenção para produção

O painel `painel_web.html` contém a API Key exposta no JavaScript do cliente. Isso é aceitável em ambiente local/interno. Para deploy público:
1. Crie um endpoint proxy no backend que injete a chave.
2. Ou use um sistema de autenticação baseado em sessão para o painel.

---

## Painel Web

Acessível em `http://localhost:5000` sem autenticação. O HTML já é servido pelo Flask via `send_file()`.

Funcionalidades:
- Atualização automática a cada **1,5 segundo**
- Indicador de conexão com a API
- Destaque visual do elevador recomendado
- Pontinhos visuais proporcionais à fila (até 10)
- Timestamp da última atualização

---

## Configuração via Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `API_KEY` | `minha-chave-secreta` | Chave de autenticação da API |
| `PORT` | `5000` | Porta HTTP do servidor |
| `TEMPO_PESSOA` | `15` | Segundos estimados por pessoa na fila |
| `RATE_LIMIT_MAX` | `60` | Requisições máximas por minuto por IP |

---

## Decisões de Design

### Por que REST e não WebSocket?
REST é mais simples de integrar, documentar e testar. O painel faz polling a cada 1,5s, o que é suficiente dado que a câmera atualiza continuamente no backend. WebSocket seria mais eficiente se houvesse muitos clientes simultâneos — é uma evolução natural para v2.

### Por que API Key e não JWT?
Este sistema é local/interno. API Key é direta e suficiente para controle de acesso em contexto de uso único. JWT faria sentido em sistemas multi-usuário com autenticação de identidade.

### Por que `/v1/` nas rotas?
Versionamento de URL é a abordagem mais transparente e compatível. Clientes existentes continuam funcionando quando uma nova versão é lançada em `/v2/`.

### Por que o health check é público?
`/health` sem autenticação permite que ferramentas de monitoramento (UptimeRobot, Kubernetes probes, etc.) verifiquem disponibilidade sem gerenciar credenciais.

---

## Ciclo de Vida e Operação

### Logs
Todos os eventos são registrados em `elevadores.log` e no stdout:
```
2025-06-01 14:32:10 [INFO] API iniciada em http://localhost:5000
2025-06-01 14:32:11 [INFO] GET /v1/status — 127.0.0.1
2025-06-01 14:32:15 [WARNING] Acesso negado: chave inválida de 192.168.1.5
```

### Encerramento gracioso
O sistema captura `KeyboardInterrupt` para liberar a câmera corretamente:
```python
except KeyboardInterrupt:
    log.info("Encerrando sistema...")
finally:
    cap.release()
```

### Evolução futura (v2)
- Histórico de filas com banco de dados (SQLite/Postgres)
- Autenticação OAuth2
- Suporte a N elevadores via configuração
- WebSocket para push em tempo real
- Restrição de CORS por domínio específico
