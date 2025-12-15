# Striker Polymarket Analysis

**Striker Polymarket Analysis** é uma plataforma completa de *analytics* desenvolvida em Python e Streamlit para analisar a performance de traders na Polymarket.

A ferramenta permite dissecar o histórico de negociação de qualquer carteira, calcular métricas avançadas (como CLV) e simular estratégias de *Copy Trading* com base em dados históricos.

## 🚀 Funcionalidades Principais

### 📊 Análise de Utilizador (User Analysis)
Introduz um endereço de carteira da Polymarket e obtém uma visão detalhada:
* **Métricas de PnL:** Lucro Realizado, Não Realizado, ROI, Volume Apostado e Lucro "Flat" (baseado em unidades).
* **Filtragem Avançada:** Filtra trades por **Tags** (ex: Politics, Sports), **Intervalo de Tempo** e **Stake Mínima**.
* **Gráficos Interativos:** Curva de lucro acumulado e distribuição de lucros mensais/diários.
* **Tabelas Paginadas:** Visualiza posições abertas e fechadas com exportação para CSV.

### 🧠 Closing Line Value (CLV)
Avalia a habilidade real do trader comparando o preço de entrada com o preço de fecho do mercado:
* Cálculo da probabilidade implícita vs. probabilidade final.
* Estatísticas de "Beat Market" (percentagem de vezes que o trader bateu o mercado).

### 🤖 Simulador de Copy Trade
Uma ferramenta poderosa para testar a viabilidade de copiar um trader específico:
* **Estratégias de Entrada:**
    * *Flat Staking:* Aposta fixa independentemente do tamanho da aposta original.
    * *Capped:* Segue o valor original até um limite máximo definido.
    * *2x Flat:* Entra apenas se a aposta for o dobro da tua stake base.
* **Estratégias de Saída (Sell):**
    * *Proportional:* Vende a mesma percentagem que o trader original.
    * *One Sell Dumps All:* Vende tudo ao primeiro sinal de venda do trader (Panic Mode).
    * *Never Sell:* Ignora vendas e segura até à resolução (Diamond Hands).
* **Visualização:** Gráfico de *Equity Curve* comparando o Trader Original vs. Estratégia de Cópia.

## 🛠️ Instalação e Configuração

### Pré-requisitos
* Python 3.10 ou superior
* Git

### Passo a Passo

1.  **Clonar o repositório:**
    ```bash
    git clone [https://github.com/enzoustk/striker-polymarket-analysis.git](https://github.com/enzoustk/striker-polymarket-analysis.git)
    cd striker-polymarket-analysis
    ```

2.  **Criar um ambiente virtual (Recomendado):**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Instalar dependências:**
    > **Nota:** Este projeto depende de uma biblioteca API personalizada hospedada no GitHub. Certifica-te de que tens git instalado.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Executar a aplicação:**
    ```bash
    streamlit run striker_pm_analysis/app.py
    ```

## 📂 Estrutura do Projeto

```text
striker-polymarket-analysis/
├── striker_pm_analysis/
│   ├── app.py                 # Ponto de entrada da aplicação (Main)
│   ├── helpers.py             # Funções auxiliares genéricas
│   ├── src/
│   │   ├── backend/           # Lógica de negócio e processamento de dados
│   │   │   ├── clv.py                   # Cálculos de Closing Line Value
│   │   │   ├── copy_trade_simulator.py  # Motor de simulação de CopyTrade
│   │   │   ├── data_helpers.py          # Manipulação e formatação de DataFrames
│   │   │   └── user_data.py             # Gestão de dados do utilizador
│   │   ├── data/              # Lógica analítica matemática (ROI, Stats)
│   │   ├── pages/             # Páginas do Streamlit (Dashboard, User Analysis)
│   │   └── ui/                # Elementos visuais (Gráficos, Tabelas, Cards)
├── requirements.txt           # Lista de dependências
└── README.md                  # Documentação