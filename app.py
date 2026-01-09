import streamlit as st
import sqlite3
import subprocess
import sys
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente (se houver)
load_dotenv()

# 1. Configuração da Página (Título da aba do navegador e layout)
st.set_page_config(page_title="Monitor de Preços Mercado Livre", page_icon="🏷️", layout="wide")

# --- FUNÇÕES DE FORMATAÇÃO (Substituindo os filtros do Jinja2) ---
def format_currency(value):
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_date(value):
    if not value:
        return ""
    return str(value)

# --- CONEXÃO COM BANCO DE DADOS (SQLite) ---
def get_db_connection():
    # Verifica se o arquivo existe antes de tentar conectar
    if not os.path.exists('dados.db'):
        return None
    
    conn = sqlite3.connect('dados.db')
    # Isso permite acessar as colunas pelo nome (ex: row['product']) igual no MySQL dictionary=True
    conn.row_factory = sqlite3.Row 
    return conn

# --- INTERFACE VISUAL ---
st.title("🏷️ Produtos Coletados")
st.markdown("Monitoramento de preços via Web Scraping com **Selenium** e **SQLite**.")

# --- BARRA LATERAL (Botão de ação) ---
with st.sidebar:
    st.header("Controles")
    
    # Botão para rodar o Scraper (Substitui a rota /run-scraper)
    if st.button("🔄 Atualizar Dados", type="primary"):
        with st.spinner("Rodando o robô de captura... Isso pode levar alguns segundos."):
            try:
                # sys.executable garante que o Python usado seja o mesmo do ambiente virtual
                result = subprocess.run(
                    [sys.executable, "scraper.py"], 
                    capture_output=True, 
                    text=True,
                    encoding='utf-8' # Garante leitura correta de acentos
                )
                
                # Verifica se o script rodou sem erros (código 0)
                if result.returncode == 0:
                    st.success("✅ Dados atualizados com sucesso!")
                    st.rerun() # Recarrega a página para mostrar os dados novos
                else:
                    st.error("❌ Ocorreu um erro ao rodar o scraper.")
                    # Mostra o erro técnico dentro de uma caixa expansível
                    with st.expander("Ver detalhes do erro"):
                        st.code(result.stderr)
                        st.text("Logs de saída:")
                        st.code(result.stdout)
                        
            except Exception as e:
                st.error(f"Erro crítico ao tentar executar o script: {e}")

# --- EXIBIÇÃO DOS PRODUTOS (Substitui o produtos.html) ---
conn = get_db_connection()

if conn:
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT product, old_price, current_price, seller, source, img_link, created_at
            FROM products
            ORDER BY created_at DESC
        """)
        produtos = cursor.fetchall()
        conn.close()

        if not produtos:
            st.warning("⚠️ O banco de dados existe, mas está vazio. Clique em 'Atualizar Dados'.")
        else:
            # Mostra métricas no topo
            col1, col2 = st.columns(2)
            col1.metric("Total de Produtos", len(produtos))
            
            # Cálculo seguro da média
            if len(produtos) > 0:
                media = sum(p['current_price'] for p in produtos) / len(produtos)
                col2.metric("Preço Médio", format_currency(media))
            
            st.divider()

            # Criação do Grid (igual ao grid-cols-4 do Tailwind)
            cols = st.columns(4)
            
            for index, p in enumerate(produtos):
                # Distribui os cards entre as 4 colunas
                with cols[index % 4]:
                    # st.container com borda cria o efeito de "Card"
                    with st.container(border=True):
                        
                        # Imagem (com tratamento caso venha vazia)
                        if p['img_link']:
                            st.image(p['img_link'], use_container_width=True)
                        else:
                            st.text("Sem Imagem")
                        
                        # Título e Vendedor
                        st.markdown(f"**{p['product']}**")
                        st.caption(f"{p['seller']}")
                        
                        # Preços
                        if p['old_price'] and p['old_price'] > 0:
                            st.markdown(f"<span style='color:red; text-decoration:line-through'>{format_currency(p['old_price'])}</span>", unsafe_allow_html=True)
                        
                        st.markdown(f"### {format_currency(p['current_price'])}")
                        
                        # Botão de Link
                        st.link_button("Ver Oferta", p['source'], use_container_width=True)
                        
                        # Data
                        st.caption(f"Atualizado em: {format_date(p['created_at'])}")

    except sqlite3.Error as e:
        st.error(f"Erro ao ler o banco de dados: {e}")
else:
    # Caso o arquivo dados.db ainda não exista
    st.info("👋 Bem-vindo! Clique no botão **'Atualizar Dados'** na barra lateral para iniciar a primeira coleta.")

