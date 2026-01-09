import time
import os
from selenium import webdriver
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pandas as pd
import mysql.connector
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Declarando funções que vão ser usadas no scraping

def organize(item):
    try:
        # Tentando extrair informaçoes de cada item
        title = item.select_one(".poly-component__title").text
        source = item.select_one(".poly-component__title")["href"]
        seller = item.select_one(".poly-component__seller").text if item.select_one(".poly-component__seller") else 'Não informado'
        
        # oldPrice
        old_integer = item.select_one(".andes-money-amount__fraction").text.strip()
        old_cents = item.select_one(".andes-money-amount__cents").text.strip() if item.select_one(".andes-money-amount__cents") else '00'
        old_price_str = str(old_integer + "," + old_cents)
        
        new_element = item.select_one(".poly-price__current")
        
        # currentPrice
        new_integer = new_element.select_one(".andes-money-amount__fraction").text.strip()
        new_cents = new_element.select_one(".andes-money-amount__cents").text.strip() if new_element.select_one(".andes-money-amount__cents") else '00'
        new_price_str = str(new_integer + "," + new_cents)
        
        image = item.select_one(".poly-component__picture")["src"]
    except Exception as e: 
            # comment: Tratando possivel erro
            print("Erro")
            raise e
    else:
        # Retornando o item em dictionary
         return {
            "product": title,
            "seller": "Vendido por: " + seller,
            "old_price": old_price_str,
            "current_price": new_price_str,
            "source": source,
            "img_link": image
        }
   
def connectDb():
    try:
        # Tentando conectar ao banco
        conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Tomato@mysql08",
        port=3306
        )
        
        # Conectando ao mysql e criando banco/tabela caso não existir
        cursor = conn.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS banco_dayve")
        cursor.execute("USE banco_dayve")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product VARCHAR(1000),
            old_price DECIMAL(10,2),
            current_price DECIMAL(10,2),
            seller VARCHAR(500),
            source TEXT,
            img_link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_product_source (product(255), source(255))
        )
        """)
        
    except Exception as e: 
        # Tratando possivel erro
        raise e
    else:
        # Retornando a conexão
        print("Conectado ao banco com sucesso")
        return  conn, cursor
        
    # end try
    
# Acessa uma variável de ambiente específica, retorna None se não existir
# Use o segundo argumento para um valor padrão caso a variável não exista

#1 - Pegar página html

load_dotenv() # Lendo as variáveis ambientes
url = os.environ.get("URL","https://www.google.com/") 

# Inicializando serviço e configurações
service = Service() 
chrome_options = Options()

# Inicializando o driver
driver = webdriver.Chrome(service=service, options=chrome_options)

# Pegando conteúdo da página
driver.get(url)
time.sleep(3)  # Pausando para a página carregar completamente

# Rola para a parte inferior da página suavemente
driver.execute_script("window.scrollTo({ top: document.body.scrollHeight / 2, behavior: 'smooth' });")

time.sleep(2)  # Pausando para a página carregar completamente


driver.execute_script("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });")


# driver.find_element(By.TAG_NAME, "body").send_keys(Keys.CONTROL, Keys.END)

time.sleep(2)  # Pausando para a página carregar completamente

# Separando Item principal
element = driver.find_element(By.CLASS_NAME, 'items-with-smart-groups')
html_base = element.get_attribute('outerHTML')

# Encerrando o processo e fechando a página
driver.quit() 

# 2 Formatando a página
soup = BeautifulSoup(html_base,"lxml")

# Separando items e organizando itens
items = soup.select(".andes-card.poly-card.poly-card--grid-card.poly-card--xlarge.andes-card--flat.andes-card--padding-0.andes-card--animated")
produtos = [organize(item) for item in items]

# Salvando itens num DF
dataFrame_full = pd.DataFrame(produtos, columns=["product", "old_price", "current_price", "seller", "source", "img_link"])

dataFrame_full["old_price"] = (
    dataFrame_full["old_price"]
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
    .astype(float)
)

dataFrame_full["current_price"] = (
    dataFrame_full["current_price"]
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
    .astype(float)
)

rows = list(
    dataFrame_full[["product", "old_price", "current_price", "seller", "source", "img_link"]]
    .itertuples(index=False, name=None)
)

sql = """
INSERT INTO products (product, old_price, current_price, seller, source, img_link)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    current_price = VALUES(current_price)
"""

conn, cursor  = connectDb()

try:
    cursor.executemany(sql, rows)
    conn.commit()
    
except Exception as e: 
    # Tratando possivel erro
    raise e
finally:
    cursor.close()
    conn.close()


print("Fim do scraping.")