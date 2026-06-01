import cv2
from ultralytics import YOLO

# Carrega o modelo YOLOv8 treinado para detectar pessoas
model = YOLO("yolov8n.pt")

# Abre a câmera (Mude para 0 para testar na webcam ou insira o link RTSP da sua câmera)
cap = cv2.VideoCapture(0)

# ==============================================================================
# CONFIGURAÇÃO DAS ÁREAS DE ESPERA (Ajuste os retângulos na sua imagem)
# ==============================================================================
elevador_A_x1, elevador_A_y1 = 50, 150
elevador_A_x2, elevador_A_y2 = 300, 450

elevador_B_x1, elevador_B_y1 = 340, 150
elevador_B_x2, elevador_B_y2 = 590, 450

# Tempo médio estimado que o elevador gasta por pessoa na fila (em segundos)
TEMPO_POR_PESSOA = 15 

while cap.isOpened():
    sucesso, frame = cap.read()
    if not sucesso:
        break

    # IA detecta apenas pessoas (classe 0)
    resultados = model(frame, classes=[0], verbose=False)
    
    fila_A = 0
    fila_B = 0

    # Contagem de pessoas dentro de cada região correspondente
    for caixa in resultados[0].boxes:
        x1, y1, x2, y2 = map(int, caixa.xyxy[0])
        centro_x = int((x1 + x2) / 2)
        centro_y = int(y2)

        if elevador_A_x1 < centro_x < elevador_A_x2 and elevador_A_y1 < centro_y < elevador_A_y2:
            fila_A += 1
        elif elevador_B_x1 < centro_x < elevador_B_x2 and elevador_B_y1 < centro_y < elevador_B_y2:
            fila_B += 1

    # Cálculo matemático do tempo estimado de espera (convertido para minutos/segundos)
    tempo_segundos_A = fila_A * TEMPO_POR_PESSOA
    tempo_segundos_B = fila_B * TEMPO_POR_PESSOA

    texto_tempo_A = f"{tempo_segundos_A}s" if tempo_segundos_A < 60 else f"{tempo_segundos_A // 60} min"
    texto_tempo_B = f"{tempo_segundos_B}s" if tempo_segundos_B < 60 else f"{tempo_segundos_B // 60} min"

    # ==============================================================================
    # DESENHO DA INTERFACE GRÁFICA PARA A TV
    # ==============================================================================
    # Criando um painel digital do zero com fundo escuro (Resolução 1280x720)
    painel = cv2.resize(frame, (1280, 720))
    painel[:] = (15, 15, 15) # Cor de fundo cinza escuro/preto

    # Linha divisória vertical fina no meio da tela
    cv2.line(painel, (640, 0), (640, 720), (40, 40, 40), 2)

    # --------------------------------------------------------------------------
    # LADO ESQUERDO: ELEVADOR A
    # --------------------------------------------------------------------------
    cv2.putText(painel, "ELEVADOR A", (160, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3)
    cv2.putText(painel, f"Fila atual: {fila_A} pessoas", (140, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (160, 160, 160), 2)
    
    cv2.putText(painel, "Tempo de espera:", (140, 380), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (120, 120, 120), 2)
    cv2.putText(painel, texto_tempo_A, (140, 480), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 6)

    # --------------------------------------------------------------------------
    # LADO DIREITO: ELEVADOR B
    # --------------------------------------------------------------------------
    cv2.putText(painel, "ELEVADOR B", (800, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3)
    cv2.putText(painel, f"Fila atual: {fila_B} pessoas", (780, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (160, 160, 160), 2)
    
    cv2.putText(painel, "Tempo de espera:", (780, 380), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (120, 120, 120), 2)
    cv2.putText(painel, texto_tempo_B, (780, 480), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 6)

    # --------------------------------------------------------------------------
    # BARRA INFERIOR: INDICAÇÃO DE MENOR FILA
    # --------------------------------------------------------------------------
    # Retângulo cinza de rodapé
    cv2.rectangle(painel, (0, 600), (1280, 720), (25), 25, 25)
    
    # Define qual elevador está mais vazio para destacar no rodapé
    if fila_A < fila_B:
        indicacao = "RECOMENDADO: USE O ELEVADOR A (MENOS CHEIO)"
        cor_status = (255, 120, 0) # Ciano/Azul destacado
    elif fila_B < fila_A:
        indicacao = "RECOMENDADO: USE O ELEVADOR B (MENOS CHEIO)"
        cor_status = (0, 220, 100) # Verde destacado
    else:
        indicacao = "ELEVADORES COM FILAS IGUAIS - EMBARQUE LIVRE"
        cor_status = (200, 200, 200) # Branco/Cinza

    cv2.putText(painel, indicacao, (180, 670), cv2.FONT_HERSHEY_SIMPLEX, 1.2, cor_status, 3)

    # Opções de renderização em tela cheia na TV
    cv2.namedWindow("Painel Informativo de Fluxo", cv2.WINDOW_NORMAL)
    cv2.imshow("Painel Informativo de Fluxo", painel)

    # Pressione 'q' na janela para encerrar o programa
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()