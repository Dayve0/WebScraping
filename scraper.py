import time
import os
import sqlite3
import sys
from selenium import webdriver
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Garante que os acentos apareçam nos logs do Streamlit
sys.stdout.reconfigure(encoding='utf-8')

def setup_db():
    conn = sqlite3.connect('dados.db')
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT,
        old_price REAL,
        current_price REAL,
        seller TEXT,
        source TEXT,
        img_link TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(product, source)
    )
    """)
    conn.commit()
    return conn

# Função para limpar preços
def clean_price(price_str):
    if not price_str: return 0.0
    try:
        # Remove R$, espaços, e converte formato BR (1.000,00) para US (1000.00)
        clean = price_str.replace("R$", "").replace(" ", "").strip()
        clean = clean.replace(".", "").replace(",", ".")
        return float(clean)
    except:
        return 0.0

def run_scraper():
    print("--- INICIANDO SCRAPER ---")
    
    # 1. Configuração do Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # User-Agent rotativo ou comum para parecer PC real
    chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    url = os.environ.get("URL", "https://lista.mercadolivre.com.br/monitor-gamer")
    print(f"Acessando URL: {url}")

    try:
        driver.get(url)
        time.sleep(3) # Espera carregar
        
        # Tenta pegar o título da página para ver se carregou
        print(f"Título da página encontrada: {driver.title}")
        
        # Scroll para carregar imagens
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        
        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")
        
        # 2. Estratégia Multi-Seletor (O segredo para não falhar)
        # O ML usa classes diferentes dependendo do servidor. Tentamos todas.
        
        # Opção A: Layout Novo (Poly)
        items = soup.select(".poly-card")
        tipo_layout = "Poly (Novo)"
        
        # Opção B: Layout Clássico (Search Layout)
        if not items:
            items = soup.select(".ui-search-layout__item")
            tipo_layout = "Search Layout (Antigo)"
            
        print(f"Layout detectado: {tipo_layout} - Itens encontrados: {len(items)}")

        produtos_processados = []

        for item in items:
            try:
                # Tenta achar o link e título (são essenciais)
                link_tag = item.select_one("a.poly-component__title, a.ui-search-link")
                if not link_tag: continue
                
                title = link_tag.text.strip()
                link = link_tag['href']
                
                # Preço (Tenta vários seletores)
                price_tag = item.select_one(".poly-price__current .andes-money-amount__fraction, .ui-search-price__second-line .andes-money-amount__fraction")
                price_val = clean_price(price_tag.text) if price_tag else 0.0
                
                # Imagem
                img_tag = item.select_one("img.poly-component__picture, img.ui-search-result-image__element")
                img_link = img_tag.get('src') if img_tag else ""
                
                # Vendedor (Opcional)
                seller_tag = item.select_one(".poly-component__seller")
                seller = seller_tag.text.strip() if seller_tag else "Vendedor Desconhecido"

                produtos_processados.append((title, seller, 0.0, price_val, link, img_link))
                
            except Exception as e:
                continue # Pula item com erro sem quebrar o resto

        print(f"Produtos extraídos com sucesso: {len(produtos_processados)}")

        # 3. Salvar no Banco
        if produtos_processados:
            conn = setup_db()
            cursor = conn.cursor()
            
            sql = """
            INSERT INTO products (product, seller, old_price, current_price, source, img_link)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(product, source) DO UPDATE SET
                current_price = excluded.current_price,
                created_at = CURRENT_TIMESTAMP
            """
            cursor.executemany(sql, produtos_processados)
            conn.commit()
            conn.close()
            print("Dados salvos no SQLite!")
        else:
            print("ALERTA: Nenhum produto extraído. O HTML pode ter mudado ou fomos bloqueados.")

    except Exception as e:
        print(f"ERRO CRÍTICO NO SCRAPER: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
