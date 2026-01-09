import time
import os
import sqlite3
import sys
import random
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth

sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURAÇÃO DO BANCO ---
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
        is_demo BOOLEAN DEFAULT 0,
        UNIQUE(product, source)
    )
    """)
    # Coluna is_demo ajuda a saber se o dado é real ou fake
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN is_demo BOOLEAN DEFAULT 0")
    except:
        pass # Coluna já existe
        
    conn.commit()
    return conn

# --- FUNÇÃO GERADORA DE DADOS MOCK (FAKE) ---
def generate_mock_data():
    """Gera dados falsos para o portfólio não ficar vazio quando houver bloqueio"""
    print("⚠️ ATIVANDO MODO DEMO: Gerando dados simulados para portfólio...")
    
    mock_products = [
        ("Monitor Gamer LG UltraGear 24'", "Loja Oficial LG", 1600.00, 1299.00, "https://mercadolivre.com.br", "https://http2.mlstatic.com/D_NQ_NP_895340-MLA46610859669_072021-O.webp"),
        ("Monitor Samsung Odyssey G3", "Kabum", 1800.00, 1450.00, "https://mercadolivre.com.br", "https://http2.mlstatic.com/D_NQ_NP_965682-MLA48643836371_122021-O.webp"),
        ("Monitor Gamer AOC Hero 144hz", "Mercado Livre", 1100.00, 989.90, "https://mercadolivre.com.br", "https://http2.mlstatic.com/D_NQ_NP_662095-MLA44336048564_122020-O.webp"),
        ("Monitor Dell Alienware 25'", "Dell Oficial", 3500.00, 3199.00, "https://mercadolivre.com.br", "https://http2.mlstatic.com/D_NQ_NP_934446-MLA43722744822_102020-O.webp"),
        ("Monitor Pichau Centauri", "Pichau", 900.00, 799.00, "https://mercadolivre.com.br", "https://http2.mlstatic.com/D_NQ_NP_798544-MLA47864350993_102021-O.webp"),
    ]
    
    conn = setup_db()
    cursor = conn.cursor()
    
    # Limpa dados antigos para mostrar o Demo limpo
    cursor.execute("DELETE FROM products")
    
    for p in mock_products:
        # Adiciona variação aleatória no preço para parecer dinâmico a cada clique
        variation = random.uniform(0.95, 1.05)
        price = p[3] * variation
        
        cursor.execute("""
        INSERT INTO products (product, seller, old_price, current_price, source, img_link, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (p[0], p[1], p[2], price, p[4], p[5]))
        
    conn.commit()
    conn.close()
    print("✅ Dados de demonstração inseridos com sucesso!")

# --- SCRAPER REAL ---
def run_scraper():
    print("--- INICIANDO TENTATIVA DE SCRAPING ---")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)

    stealth(driver,
        languages=["pt-BR", "pt"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    url = os.environ.get("URL", "https://lista.mercadolivre.com.br/monitor-gamer")
    
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        
        # Check básico de bloqueio de título
        print(f"Título da página: {driver.title}")
        
        soup = BeautifulSoup(driver.page_source, "lxml")
        
        # Tenta coletores
        items = soup.select("div.poly-card")
        if not items: items = soup.select("li.ui-search-layout__item")
        if not items: items = soup.select("div.andes-card") # Última tentativa

        print(f"Itens encontrados: {len(items)}")

        # LÓGICA DE FAIL-SAFE
        # Se achou menos de 3 itens, consideramos bloqueio ou erro
        if len(items) < 3:
            print("❌ Bloqueio detectado ou HTML desconhecido.")
            generate_mock_data() # <--- CHAMA O PLANO B
            return

        # Se passou daqui, o scraping funcionou!
        produtos_processados = []
        for item in items:
            try:
                # Lógica de extração simplificada para brevidade
                title_tag = item.select_one("a.poly-component__title, h2.ui-search-item__title")
                if not title_tag: continue
                title = title_tag.text.strip()
                link = title_tag.get("href")
                
                price_tag = item.select_one(".andes-money-amount__fraction")
                current_price = float(price_tag.text.replace(".", "").replace(",", ".")) if price_tag else 0
                
                img_tag = item.select_one("img")
                img_link = img_tag.get("data-src") or img_tag.get("src") or ""
                
                if current_price > 0:
                    produtos_processados.append((title, "Mercado Livre", 0, current_price, link, img_link, 0)) # 0 = Real Data
            except:
                continue

        if produtos_processados:
            conn = setup_db()
            cursor = conn.cursor()
            # Limpa Demo anterior se houver
            cursor.execute("DELETE FROM products WHERE is_demo = 1")
            
            cursor.executemany("""
            INSERT INTO products (product, seller, old_price, current_price, source, img_link, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product, source) DO UPDATE SET current_price=excluded.current_price
            """, produtos_processados)
            conn.commit()
            conn.close()
            print(f"✅ Sucesso Real! {len(produtos_processados)} produtos salvos.")
        else:
             generate_mock_data() # Fallback se falhar no loop

    except Exception as e:
        print(f"Erro: {e}")
        generate_mock_data() # Fallback em caso de crash
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
