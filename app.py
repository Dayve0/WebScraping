import streamlit as st
import sqlite3
import subprocess
import sys
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Monitor ML", page_icon="📦", layout="wide")

# Formatação BR
def format_currency(value):
    if value is None: return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_db_connection():
    if not os.path.exists('dados.db'):
        return None
    return sqlite3.connect('dados.db')

st.title("📦 Monitor de Preços - Mercado Livre")
st.markdown("Monitoramento de preços utilizando **Selenium Stealth** para contornar proteções.")

# --- SIDEBAR COM BOTÃO ---
with st.sidebar:
    st.header("Controles")
    if st.button("🔄 Atualizar Dados", type="primary"):
        with st.spinner("Acessando Mercado Livre (Modo Stealth)..."):
            try:
                # Executa scraper.py
                result = subprocess.run(
                    [sys.executable, "scraper.py"], 
                    capture_output=True, 
                    text=True,
                    encoding='utf-8'
                )
                
                # Exibe logs no sidebar para você saber se foi bloqueado
                with st.expander("Logs da Execução"):
                    st.code(result.stdout)
                    if result.stderr:
                        st.error(result.stderr)

                if "SUCESSO" in result.stdout:
                    st.success("Dados atualizados!")
                    st.rerun()
                elif "BLOQUEIO" in result.stdout:
                    st.error("O ML bloqueou o IP temporariamente (Login Wall).")
                else:
                    st.warning("O script rodou mas não salvou dados. Verifique os logs.")
                    
            except Exception as e:
                st.error(f"Erro: {e}")

# --- DISPLAY ---
conn = get_db_connection()
if conn:
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
        produtos = cursor.fetchall()
        conn.close()

        if not produtos:
            st.info("Banco vazio. Clique em atualizar.")
        else:
            # Métricas
            col1, col2 = st.columns(2)
            col1.metric("Produtos Rastreados", len(produtos))
            media = sum(p['current_price'] for p in produtos) / len(produtos)
            col2.metric("Preço Médio", format_currency(media))

            st.divider()

            # Grid
            cols = st.columns(4)
            for i, p in enumerate(produtos):
                with cols[i % 4]:
                    with st.container(border=True):
                        # Imagem com tratamento de erro
                        if p['img_link']:
                            st.image(p['img_link'], use_container_width=True)
                        else:
                            st.text("Sem imagem")
                        
                        # Título e Preço
                        st.markdown(f"**{p['product'][:50]}...**")
                        st.markdown(f"### {format_currency(p['current_price'])}")
                        st.caption(p['seller'])
                        
                        st.link_button("Ver Oferta", p['source'], use_container_width=True)
                        st.caption(f"Atualizado: {p['created_at']}")
    except Exception as e:
        st.error(f"Erro de leitura: {e}")
else:
    st.warning("Banco de dados ainda não existe. Execute o scraper pela primeira vez.")
