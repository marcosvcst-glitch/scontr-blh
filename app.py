import streamlit as st
import cv2
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytz
import io

# Tenta importar o ReportLab para gerar o PDF. Se não estiver instalado no Streamlit, instala automaticamente em segundo plano.
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
except ImportError:
    import os
    os.system('pip install reportlab')
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

# Configuração da página do site
st.set_page_config(page_title="SCONTR - Banco de Leite", page_icon="🍼", layout="wide")

# Inicializa o banco de dados na memória do servidor se não existir
if 'banco_dados_blh' not in st.session_state:
    st.session_state.banco_dados_blh = []

st.title("🍼 SCONTR - Central Inteligente de Triagem e Logística")
st.caption("Gerenciamento prioritário de filas da ANVISA e análise colorimétrica calibrada")

# Função robusta para criar o relatório em PDF estruturado
def gerar_pdf(dados_fila):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Estilos customizados para o PDF
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1A365D'),
        spaceAfter=6,
        alignment=1 # Centralizado
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=20,
        alignment=1
    )
    
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=1
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.white,
        fontWeight='Bold',
        alignment=1
    )

    # Cabeçalho do Documento
    story.append(Paragraph("<b>SCONTR - SISTEMA DE CONTROLE E LOGÍSTICA DE BANCO DE LEITE</b>", title_style))
    data_atual = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime("%d/%m/%Y às %H:%M:%S")
    story.append(Paragraph(f"Relatório Técnico de Triagem e Fila de Prioridade ANVISA - Gerado em {data_atual}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Montagem da tabela do PDF
    table_data = [[
        Paragraph("<b>Posição</b>", header_style),
        Paragraph("<b>Frasco</b>", header_style),
        Paragraph("<b>Vol. NaOH</b>", header_style),
        Paragraph("<b>Acidez Real</b>", header_style),
        Paragraph("<b>Validação Visual</b>", header_style),
        Paragraph("<b>Horário</b>", header_style),
        Paragraph("<b>Prazo Limite</b>", header_style),
        Paragraph("<b>Status / Ação ANVISA</b>", header_style)
    ]]
    
    for row in dados_fila:
        table_data.append([
            Paragraph(str(row['Fila de Espera']), cell_style),
            Paragraph(str(row['Frasco']), cell_style),
            Paragraph(str(row['Volume NaOH']), cell_style),
            Paragraph(str(row['Acidez Real']), cell_style),
            Paragraph(str(row['Validação por Imagem']), cell_style),
            Paragraph(str(row['Horário do Teste']), cell_style),
            Paragraph(str(row['Prazo Limite']), cell_style),
            Paragraph(str(row['Status e Ação Logística']), cell_style)
        ])
        
    t = Table(table_data, colWidths=[55, 60, 60, 60, 85, 55, 65, 120])
    
    # Estilização da tabela padrão ANVISA (Linhas alternadas e cabeçalho azul escuro)
    t_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A365D')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])
    
    # Aplica cores suaves no PDF simulando a estilização do site
    for i in range(1, len(table_data)):
        status_txt = dados_fila[i-1]['Status e Ação Logística']
        if "Excelente" in status_txt:
            bg_color = colors.HexColor('#E2EFDA')
        elif "ATENÇÃO" in status_txt:
            bg_color = colors.HexColor('#FFF2CC')
        elif "URGÊNCIA" in status_txt:
            bg_color = colors.HexColor('#FCE4D6')
        else:
            bg_color = colors.HexColor('#F2f2f2')
            
        t_style.add('BACKGROUND', (0, i), (-1, i), bg_color)
        
    t.setStyle(t_style)
    story.append(t)
    
    # Assinatura técnica no rodapé do documento
    story.append(Spacer(1, 40))
    assinatura_style = ParagraphStyle('Assinatura', parent=styles['Normal'], fontSize=9, alignment=1, textColor=colors.HexColor('#718096'))
    story.append(Paragraph("_________________________________________________________", assinatura_style))
    story.append(Paragraph("Responsável Técnico pelo Controle de Qualidade - BLH", assinatura_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# Divisão da tela em duas colunas (Inputs e Painel)
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📥 Entrada de Dados")
    nome_frasco = st.text_input("Identificação do Leite", placeholder="Ex: Frasco #03")
    volume_ml = st.number_input("Volume de NaOH Consumido (mL)", min_value=0.000, max_value=0.150, value=0.045, step=0.005, format="%.3f")
    
    foto_arquivo = st.camera_input("Captura da Viragem (Foto da Bancada)")
    acao = st.radio("Comando do Operador", ["Adicionar / Atualizar", "Remover Frasco", "Limpar Banco Total (Reset)"])
    btn_processar = st.button("🚀 Registrar e Processar Lote", type="primary")

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
            
            if foto_arquivo is not None:
                try:
                    file_bytes = np.asarray(bytearray(foto_arquivo.read()), dtype=np.uint8)
                    opencv_image = cv2.imdecode(file_bytes, 1)
                    img_hsv = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2HSV)
                    
                    # CORREÇÃO ANTIBRANCO: Saturação mínima ajustada para 50 (ignora branco/luz pura)
                    # O rosa real tem matiz bem específica no OpenCV (pontas do espectro: 0-10 e 160-180)
                    lower_rosa1 = np.array([0, 50, 40])
                    upper_rosa1 = np.array([12, 255, 255])
                    
                    lower_rosa2 = np.array([155, 50, 40])
                    upper_rosa2 = np.array([180, 255, 255])
                    
                    mask1 = cv2.inRange(img_hsv, lower_rosa1, upper_rosa1)
                    mask2 = cv2.inRange(img_hsv, lower_rosa2, upper_rosa2)
                    mask_total = mask1 + mask2
                    
                    pixels_rosa = np.sum(mask_total > 0)
                    total_pixels = img_hsv.shape[0] * img_hsv.shape[1]
                    porcentagem_rosa = (pixels_rosa / total_pixels) * 100
                    
                    # Limite de segurança para confirmar que é o frasco de teste
                    if porcentagem_rosa > 0.3:
                        status_viragem = "🟢 Viragem Confirmada"
                    else:
                        status_viragem = "⏳ Escorvamento / Incompleta"
                except Exception as e:
                    status_viragem = "⚠️ Erro na análise visual"

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
        
        # BOTÃO EXTRAVAGANTE PARA BAIXAR EM PDF 📄✨
        st.write("---")
        pdf_data = gerar_pdf(historico_ordenado)
        st.download_button(
            label="📄 Baixar Relatório de Triagem Oficial (PDF)",
            data=pdf_data,
            file_name=f"Relatorio_SCONTR_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    else:
        st.info("O painel logístico está aguardando dados da bancada.")
