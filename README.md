# WebScraping

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange)
![Selenium](https://img.shields.io/badge/Selenium-4.x-green)

## Sobre o Projeto

Este projeto é uma solução completa para monitoramento de preços de produtos no **Mercado Livre**. Ele automatiza a coleta de dados, armazena o histórico em um banco de dados relacional e apresenta as informações em uma interface web amigável.

Diferente de scrapers simples, este projeto possui um **Front-end integrado** que permite visualizar os produtos coletados, comparar preços antigos vs. atuais e acessar os links diretamente.

## Funcionalidades

* **Web Scraping Automatizado:** Utiliza `Selenium` para navegar e extrair dados dinâmicos.
* **Gestão de Dados (Upsert):** Salva produtos no MySQL e atualiza automaticamente o preço caso o produto já exista (`ON DUPLICATE KEY UPDATE`).
* **Interface Web:** Dashboard desenvolvido com **Flask** e **TailwindCSS** (via CDN).
* **Filtros Inteligentes:** Formatação automática de moeda (BRL) e datas no frontend via filtros Jinja2 personalizados.
* **Trigger via Interface:** Rota `/run-scraper` para disparar a atualização dos dados sob demanda via subprocesso.

## Tecnologias

* **Backend:** Python 3, Flask
* **Coleta:** Selenium WebDriver, BeautifulSoup4
* **Dados:** MySQL (Connector), Pandas (Processamento)
* **Frontend:** HTML5, Jinja2, TailwindCSS

## Pré-requisitos

* Python 3.x instalado
* Google Chrome instalado
* Servidor MySQL rodando localmente

## Instalação e Configuração

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/seu-usuario/flask-price-monitor.git](https://github.com/seu-usuario/flask-price-monitor.git)
    cd flask-price-monitor
    ```

2.  **Crie um ambiente virtual:**
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # Linux/Mac:
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuração do Banco de Dados:**
    * Certifique-se que o MySQL está rodando na porta `3306`.
    * O script cria automaticamente o banco `banco_dayve` e a tabela `products` na primeira execução.
    * *Nota: Verifique as credenciais de conexão no arquivo `scraper.py` e `app.py`.*

5.  **Variáveis de Ambiente:**
    Crie um arquivo `.env` na raiz para definir a URL alvo (opcional):
    ```env
    URL="[https://lista.mercadolivre.com.br/monitor-gamer](https://lista.mercadolivre.com.br/monitor-gamer)"
    ```

## Como Executar

1.  Inicie o servidor Flask:
    ```bash
    python app.py
    ```
2.  Acesse no navegador: `http://localhost:5000`
3.  Para rodar o scraper, acesse a rota ou configure um botão para: `http://localhost:5000/run-scraper`

## Screenshots

<img width="1477" height="967" alt="image" src="https://github.com/user-attachments/assets/e24f812f-ee9b-4246-927e-45bab476245b" />
