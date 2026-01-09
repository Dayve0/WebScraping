import streamlit as st
import sqlite3
import subprocess
import sys
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente (caso use .env localmente)
load_dotenv()

# Configuração da página (Deve ser sempre o primeiro comando)
st.set_page_config(
    page_title="Book Scraper Dashboard",
    page_icon="📚",
    layout="wide"
)

# --- FUNÇÕES DE FORMATAÇÃO ---
def format_currency(value):
    """Formata para Libras (£) pois é o padrão do Books to Scrape"""
    if value is None:
        return "£ 0.00"
    return f"£ {value:,.2f}"

def format_date(value):
    """Formata a data de coleta"""
    if not value:
        return ""
    return str(value)

# --- CONEXÃO COM BANCO DE DADOS ---
def get_db_connection():
    """Conecta ao SQLite. Se não existir, retorna None para tratar na interface."""
    if not os.path.exists('dados.db'):
        return None
    return sqlite3.connect('dados.db')

# --- INTERFACE PRINCIPAL ---
st.title("📚 Monitor de Preços - Livros (Demo)")
st.markdown("""
Este projeto coleta dados automaticamente do **Books to Scrape**, armazena em um banco de dados **SQLite** e exibe as oportunidades encontradas.
""")

# --- BARRA LATERAL (Sidebar) ---
with st.sidebar:
    st.header("🎮 Painel de Controle")
    if st.button("🔄 Rodar Scraper Agora", type="primary"):
        with st.spinner("O robô está coletando dados... aguarde."):
            try:
                # Executa o scraper.py usando o mesmo Python do ambiente atual
                result = subprocess.run(
                    [sys.executable, "scraper.py"], 
                    capture_output=True, 
                    text=True,
                    encoding='utf-8'
                )
                
                # Verifica se deu certo
                if result.returncode == 0:
                    st.success("✅ Coleta finalizada com sucesso!")
                    st.rerun() # Atualiza a tela
                else:
                    st.error("❌ Erro ao rodar o script.")
                    with st.expander("Ver Logs de Erro"):
                        st.code(result.stderr)
                        st.code(result.stdout)
            except Exception as e:
                st.error(f"Erro crítico: {e}")
    
    st.info("O banco de dados é atualizado a cada execução.")

# --- EXIBIÇÃO DOS DADOS ---
conn = get_db_connection()

if conn:
    try:
        # Configura para acessar colunas pelo nome
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Busca os dados ordenados pelos mais recentes
        cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
        produtos = cursor.fetchall()
        conn.close()

        if not produtos:
            st.warning("O banco de dados existe, mas está vazio. Clique em 'Rodar Scraper Agora'.")
        else:
            # Métricas no topo
            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Livros", len(produtos))
            col2.metric("Menor Preço", format_currency(min(p['current_price'] for p in produtos)))
            col3.metric("Média de Preço", format_currency(sum(p['current_price'] for p in produtos) / len(produtos)))
            
            st.divider()
            
            # Grid de Cards (4 colunas)
            cols = st.columns(4)
            for index, p in enumerate(produtos):
                with cols[index % 4]:
                    with st.container(border=True):
                        # Imagem
                        if p['img_link']:
                            st.image(p['img_link'], use_container_width=True)
                        
                        # Título (com tooltip se for muito longo)
                        st.markdown(f"**{p['product']}**", help=p['product'])
                        
                        # Status (Estoque)
                        st.caption(f"Status: {p['seller']}")
                        
                        # Preços
                        # Simulamos um "De/Por" visual baseada na lógica do scraper
                        st.markdown(f"<span style='color:red; text-decoration:line-through'>{format_currency(p['old_price'])}</span>", unsafe_allow_html=True)
                        st.markdown(f"### {format_currency(p['current_price'])}")
                        
                        # Botão de Link
                        st.link_button("Ver no Site", p['source'], use_container_width=True)
                        
                        # Data
                        st.caption(f"Atualizado: {p['created_at']}")
            
    except Exception as e:
        st.error(f"Erro ao ler o banco de dados: {e}")
else:
    st.info("👋 Bem-vindo! Clique no botão **'Rodar Scraper Agora'** na barra lateral para iniciar a primeira coleta e criar o banco de dados.")
