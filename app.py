import streamlit as st
import sqlite3
import subprocess
import sys
import os

st.set_page_config(page_title="Monitor ML", layout="wide")

def get_connection():
    if not os.path.exists('dados.db'):
        return None
    return sqlite3.connect('dados.db')

st.title("🕵️ Monitor de Preços - Debug Mode")

# Botão de Ação
if st.button("🔄 Executar Scraper (Ver Logs)"):
    with st.spinner("O robô está trabalhando..."):
        # Roda o script e captura TUDO o que ele imprimir
        process = subprocess.run(
            [sys.executable, "scraper.py"], 
            capture_output=True, 
            text=True,
            encoding='utf-8' # Força UTF-8 para não dar erro de caractere
        )
        
        # Mostra o resultado na tela (Debug)
        with st.expander("Ver Detalhes da Execução (Logs)", expanded=True):
            st.write("Saída do Script:")
            st.code(process.stdout) # Aqui vai aparecer os prints do scraper.py
            
            if process.stderr:
                st.write("Erros encontrados:")
                st.error(process.stderr)
        
        if "Dados salvos no SQLite!" in process.stdout:
            st.success("Sucesso! O banco foi atualizado.")
            st.rerun()
        else:
            st.warning("O script rodou, mas não confirmou o salvamento. Verifique os logs acima.")

# Exibição (Grid)
conn = get_connection()
if conn:
    try:
        df = conn.execute("SELECT * FROM products ORDER BY created_at DESC").fetchall()
        # Converte para dict para facilitar
        cols_names = [description[0] for description in conn.execute("SELECT * FROM products LIMIT 1").description]
        produtos = [dict(zip(cols_names, row)) for row in df]
        conn.close()

        if produtos:
            st.metric("Produtos Rastreados", len(produtos))
            cols = st.columns(4)
            for i, p in enumerate(produtos):
                with cols[i % 4]:
                    with st.container(border=True):
                        if p['img_link']: st.image(p['img_link'])
                        st.markdown(f"**{p['product'][:40]}**")
                        st.markdown(f"### R$ {p['current_price']:,.2f}")
                        st.caption(f"Vendedor: {p['seller']}")
                        st.link_button("Ver Oferta", p['source'])
        else:
            st.info("Banco de dados existe, mas está vazio.")
    except Exception as e:
        st.error(f"Erro ao ler banco: {e}")
else:
    st.info("Banco de dados ainda não criado. Clique no botão acima.")
