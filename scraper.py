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

# Configuração de encoding para evitar erros de emoji/acentos no log
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
        # Remove R$, pontos de milhar e troca vírgula por ponto
        clean = price_str.replace("R$", "").replace(" ", "").strip()
        clean = clean.replace(".", "").replace(",", ".")
        return float(clean)
    except:
        return 0.0

def run_scraper():
    print("--- INICIANDO SCRAPER ML (MODO STEALTH) ---")
    
    # 1. Configuração do Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Desativa extensões e automação
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # 2. APLICANDO A CAMUFLAGEM (Selenium Stealth)
    # Isso sobrescreve as variáveis do navegador que dizem "sou um robô"
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
        print(f"Acessando: {url}")
        driver.get(url)
        
        # Espera aleatória para parecer humano
        time.sleep(random.uniform(3, 6))
        
        # Verifica se caiu no Login (Bloqueio)
        if "login" in driver.current_url or "suspend" in driver.current_url:
            print("❌ BLOQUEIO: O Mercado Livre redirecionou para login.")
            return

        # Scroll humano (desce e sobe um pouco)
        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)
        
        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")
        
        # 3. ESTRATÉGIA MULTI-LAYOUT
        # O ML usa 3 layouts. Tentamos todos.
        
        # Layout 1: Grid Novo (Poly)
        items = soup.select("div.poly-card")
        layout_name = "Poly Grid"
        
        # Layout 2: Lista Antiga (Search Layout)
        if not items:
            items = soup.select("li.ui-search-layout__item")
            layout_name = "Search List"
            
        # Layout 3: Cards Genéricos
        if not items:
            items = soup.select("div.andes-card")
            layout_name = "Andes Card"

        print(f"Layout detectado: {layout_name} | Itens: {len(items)}")

        produtos_processados = []

        for item in items:
            try:
                # TÍTULO E LINK
                # Tenta seletores do novo layout (Poly) e do antigo (ui-search)
                title_tag = item.select_one("a.poly-component__title, h2.ui-search-item__title, a.ui-search-item__group__element")
                if not title_tag: 
                    # Tenta pegar o link direto se não achou título
                    title_tag = item.select_one("a")
                
                if not title_tag: continue

                title = title_tag.get_text(strip=True) or title_tag.get("title")
                link = title_tag.get("href")
                
                # PREÇO
                # O seletor de preço costuma ser igual em todos
                price_tag = item.select_one(".andes-money-amount__fraction")
                price_val = clean_price(price_tag.text) if price_tag else 0.0
                
                # IMAGEM (Tenta Lazy Load e SRC normal)
                img_tag = item.select_one("img.poly-component__picture, img.ui-search-result-image__element")
                img_link = ""
                if img_tag:
                    img_link = img_tag.get("data-src") or img_tag.get("src")

                # VENDEDOR
                seller_tag = item.select_one(".poly-component__seller, .ui-search-official-store-label")
                seller = seller_tag.text.strip() if seller_tag else "Mercado Livre"

                # Filtro básico: só salva se tiver preço e nome
                if link and price_val > 0:
                    produtos_processados.append((title, seller, 0.0, price_val, link, img_link))

            except Exception as e:
                continue

        # 4. SALVAMENTO
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
            print(f"✅ SUCESSO! {len(produtos_processados)} produtos salvos.")
        else:
            print("⚠️ Nenhum produto extraído. Possível mudança de HTML ou Captcha.")

    except Exception as e:
        print(f"❌ Erro Crítico: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
