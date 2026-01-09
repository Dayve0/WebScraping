import time
import os
import sqlite3
import sys
from selenium import webdriver
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Encoding para logs
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

def clean_price(price_str):
    if not price_str: return 0.0
    try:
        clean = price_str.replace("R$", "").replace(" ", "").strip()
        clean = clean.replace(".", "").replace(",", ".")
        return float(clean)
    except:
        return 0.0

def run_scraper():
    print("--- INICIANDO SCRAPER V3 (CAMUFLADO) ---")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Define tamanho de janela para parecer monitor real
    chrome_options.add_argument("--window-size=1920,1080")
    
    # --- TRUQUES ANTI-DETECÇÃO ---
    # Desabilita flags que denunciam automação
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # User-Agent de um PC comum (Windows 10 / Chrome 120)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Truque extra: remove propriedade 'webdriver' do navegador via JS
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    url = os.environ.get("URL", "https://lista.mercadolivre.com.br/monitor-gamer")
    
    try:
        print(f"Acessando URL: {url}")
        driver.get(url)
        time.sleep(5) # Aumentei o tempo de espera
        
        page_title = driver.title
        print(f"Título obtido: {page_title}")
        
        # Scroll para tentar ativar carregamento dinâmico
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(2)
        
        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")
        
        # Tentativa de captura genérica (busca qualquer item de lista)
        # O ML as vezes usa 'ol li' ou 'div.ui-search-result'
        items = soup.select("li.ui-search-layout__item, div.poly-card, div.ui-search-result__wrapper")
        
        print(f"Itens brutos encontrados via CSS: {len(items)}")

        # --- DEBUG: Se for zero, vamos ler o que tem na tela ---
        if len(items) == 0:
            print("!!! BLOQUEIO DETECTADO OU HTML MUDOU !!!")
            # Pega o texto principal da página para saber se é Captcha
            body_text = soup.body.get_text(strip=True)[:300]
            print(f"Texto no topo da página: {body_text}")
            
            # Se tiver cookies ou aviso, tentamos pegar
            h1 = soup.select_one("h1")
            if h1: print(f"H1 da página: {h1.text}")

        produtos_processados = []

        for item in items:
            try:
                # Busca título (link)
                link_tag = item.select_one("a")
                if not link_tag: continue
                
                title = link_tag.get('title') or link_tag.text.strip()
                link = link_tag.get('href')
                
                # Pula se não for link de produto
                if not link or "mercadolivre.com" not in link: continue

                # Preço
                price_tag = item.select_one(".andes-money-amount__fraction")
                price_val = clean_price(price_tag.text) if price_tag else 0.0
                
                # Imagem
                img_tag = item.select_one("img")
                img_link = img_tag.get('data-src') or img_tag.get('src') or ""
                
                # Vendedor
                seller_tag = item.select_one(".poly-component__seller, .ui-search-official-store-label")
                seller = seller_tag.text.strip() if seller_tag else "Vendedor não informado"

                if title and price_val > 0:
                    produtos_processados.append((title, seller, 0.0, price_val, link, img_link))
                
            except Exception as e:
                continue

        if produtos_processados:
            print(f"Conseguimos extrair {len(produtos_processados)} produtos válidos.")
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
            print("Salvo no SQLite com sucesso!")
        else:
            print("Nenhum produto estruturado pôde ser montado.")

    except Exception as e:
        print(f"Erro geral: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
