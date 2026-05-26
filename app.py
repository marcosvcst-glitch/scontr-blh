import streamlit as st
import cv2
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Configuração da página do site
st.set_page_config(page_title="SCONTR - Banco de Leite", page_icon="🍼", layout="wide")

# Inicializa o banco de dados na memória do servidor se não existir
if 'banco_dados_blh' not in st.session_state:
    st.session_state.banco_dados_blh = []

st.title("🍼 SCONTR - Central Inteligente de Triagem e Logística")
st.caption("Gerenciamento prioritário de filas da ANVISA e análise colorimétrica calibrada")

# Divisão da tela em duas colunas (Inputs e Painel)
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📥 Entrada de Dados")
    nome_frasco = st.text_input("Identificação do Leite", placeholder="Ex: Frasco #03")
    volume_ml = st.number_input("Volume de NaOH Consumido (mL)", min_value=0.000, max_value=0.150, value=0.045, step=0.005, format="%.3f")
    
    # Campo de Câmera nativo
    foto_arquivo = st.camera_input("Captura da Viragem (Foto da Bancada)")
    
    acao = st.radio("Comando do Operador", ["Adicionar / Atualizar", "Remover Frasco", "Limpar Banco Total (Reset)"])
    btn_processar = st.button("🚀 Registrar e Processar Lote", type="primary")

# Lógica de processamento ao clicar no botão
if btn_processar:
    if acao == "Limpar Banco Total (Reset)":
        st.session_state.banco_dados_blh = []
        st.toast("🧹 Sistema reiniciado. O painel está limpo!", icon="🗑️")
        
    elif acao == "Remover Frasco":
        if nome_frasco:
            antes = len(st.session_state.banco_dados_blh)
            st.session_state.banco_dados_blh = [f for f in st.session_state.banco_dados_blh if f['Frasco'].strip().lower() != nome_frasco.strip().lower()]
            if len(st.session_state.banco_dados_blh) < antes:
                st.toast(f"🗑️ O '{nome_frasco}' foi removido.", icon="✅")
            else:
                st.error(f"Frasco '{nome_frasco}' não encontrado.")
        else:
            st.warning("Insira o nome do frasco para remover.")
            
    else: # Adicionar / Atualizar
        if not nome_frasco:
            st.error("❌ Identifique o frasco antes de salvar.")
        elif volume_ml <= 0:
            st.error("❌ O volume de NaOH deve ser maior que zero.")
        else:
            status_viragem = "⏳ Não Detectada / Incompleta"
            
            # Processamento inteligente e tolerante da imagem
            if foto_arquivo is not None:
                try:
                    # Converte a foto do Streamlit para o formato do OpenCV
                    file_bytes = np.asarray(bytearray(foto_arquivo.read()), dtype=np.uint8)
                    opencv_image = cv2.imdecode(file_bytes, 1)
                    
                    # Converte para HSV (Matiz, Saturação, Brilho)
                    img_hsv = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2HSV)
                    
                    # OPÇÃO 2: Filtros alargados para máxima tolerância a sombras e tons claros
                    # Saturação mínima reduzida para 20 (pega rosa bem suave) e Brilho aceita de 30 a 255
                    lower_rosa1 = np.array([0, 20, 30])
                    upper_rosa1 = np.array([15, 255, 255])
                    
                    lower_rosa2 = np.array([150, 20, 30])
                    upper_rosa2 = np.array([180, 255, 255])
                    
                    # Cria as máscaras que isolam a gama estendida de rosa
                    mask1 = cv2.inRange(img_hsv, lower_rosa1, upper_rosa1)
                    mask2 = cv2.inRange(img_hsv, lower_rosa2, upper_rosa2)
                    mask_total = mask1 + mask2
                    
                    # Conta quantos pixels dentro da faixa existem na imagem
                    pixels_rosa = np.sum(mask_total > 0)
                    total_pixels = img_hsv.shape[0] * img_hsv.shape[1]
                    porcentagem_rosa = (pixels_rosa / total_pixels) * 100
                    
                    # Limite de área reduzido para 0.4% (alta sensibilidade para o frasco na bancada)
                    if porcentagem_rosa > 0.4:
                        status_viragem = "🟢 Viragem Confirmada"
                    else:
                        status_viragem = "⏳ Escorvamento / Incompleta"
                except Exception as e:
                    status_viragem = "⚠️ Erro na análise visual"

            # Remove duplicados para atualização
            st.session_state.banco_dados_blh = [f for f in st.session_state.banco_dados_blh if f['Frasco'].strip().lower() != nome_frasco.strip().lower()]
            
            graus_dornic = volume_ml * 100
            hora_do_teste = datetime.now(pytz.timezone('America/Sao_Paulo'))
            
            if graus_dornic <= 5.0:
                prioridade_num, status_anvisa, cor = 1, "Excelente (Até 6h)", "#e2efda"
            elif 5.0 < graus_dornic <= 7.0:
                prioridade_num, status_anvisa, cor = 2, "ZONA DE ATENÇÃO (Até 3h)", "#fff2cc"
            elif 7.0 < graus_dornic <= 8.0:
                prioridade_num, status_anvisa, cor = 3, "🚨 URGÊNCIA MÁXIMA (Até 1h)", "#fce4d6"
            else:
                prioridade_num, status_anvisa, cor = 0, "❌ REPROVADO (Descartar)", "#f2f2f2"
                
            prazo_txt = (hora_do_teste + timedelta(hours=(6 if prioridade_num == 1 else (3 if prioridade_num == 2 else 1)))).strftime("%H:%M:%S") if prioridade_num > 0 else "-"
            
            st.session_state.banco_dados_blh.append({
                'Frasco': nome_frasco,
                'Volume NaOH': f"{volume_ml:.3f}".replace(".", ",") + " mL",
                'Acidez_Num': graus_dornic,
                'Acidez Real': f"{graus_dornic:.1f} °D",
                'Validação por Imagem': status_viragem,
                'Horário do Teste': hora_do_teste.strftime("%H:%M:%S"),
                'Prazo Limite': prazo_txt,
                'Status e Ação Logística': status_anvisa,
                'prioridade': prioridade_num,
                'cor_linha': cor
            })
            st.toast(f"✅ {nome_frasco} processado!", icon="🍼")

with col2:
    st.subheader("📋 Monitoramento Estratégico da Fila de Espera")
    
    if len(st.session_state.banco_dados_blh) > 0:
        historico_ordenado = sorted(st.session_state.banco_dados_blh, key=lambda k: (k['prioridade'], k['Acidez_Num']), reverse=True)
        
        fila_posicao = 1
        for item in historico_ordenado:
            if item['prioridade'] > 0:
                item['Fila de Espera'] = f"{fila_posicao}º lugar"
                fila_posicao += 1
            else:
                item['Fila de Espera'] = "BLOQUEADO"
                
        df_painel = pd.DataFrame(historico_ordenado)[['Fila de Espera', 'Frasco', 'Volume NaOH', 'Acidez Real', 'Validação por Imagem', 'Horário do Teste', 'Prazo Limite', 'Status e Ação Logística']]
        
        def aplicar_cor_linha(row):
            match = [item['cor_linha'] for item in historico_ordenado if item['Frasco'] == row['Frasco']]
            cor = match[0] if match else "#ffffff"
            return [f'background-color: {cor}; color: #000000; text-align: center; font-size: 14px;'] * len(row)
            
        df_estilizado = df_painel.style.apply(aplicar_cor_linha, axis=1)
        st.dataframe(df_estilizado, use_container_width=True, hide_index=True)
    else:
        st.info("O painel logístico está aguardando dados da bancada.")
