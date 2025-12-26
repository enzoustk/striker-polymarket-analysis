import json
import asyncio
import pandas as pd
import streamlit as st
from src.ui.formatting import center_text
from striker_polymarket_api.rest import number_of_trades
from striker_polymarket_api.rest import fetch_all_positions

def _select_user(
    ) -> str:
    # Retora um user válido    
    center_text("Select User", bold=True, size=30)

    # campo de input do chat
    user_address = st.chat_input("Wallet:")
    
    # se o usuário enviou algo
    if user_address:
        wallet_trades = number_of_trades(user_address)

        if wallet_trades == -1:
            st.error("Invalid Wallet.")
        else:
            st.success(
                f"Carteira **{user_address}** válida.\n"
                f"Total de Traded Markets: **{wallet_trades}**"
            )
            # guardar no session_state se quiser
            st.session_state["copytrade_wallet"] = user_address
            return user_address

def get_api_data(
        user_address: str
    ) -> pd.DataFrame:
    df_api = fetch_all_positions(user_address)
    
    if df_api is None or df_api.empty:
        st.error("⚠️ Nenhuma posição encontrada na API.")
        return
    return df_api

def recieve_json():
    uploaded_file = st.file_uploader(
        "Arraste seu arquivo JSON aqui",
        type=["json"]
    )

    if uploaded_file is not None:
        try:    
            json_data = json.load(uploaded_file)
            if json_data is None:
                st.error('Arquivo em branco. Tente novamente')

            st.success("JSON carregado com sucesso!")
            return json_data

        except json.JSONDecodeError:
            st.error("Arquivo inválido. Envie um JSON válido.")

def get_traders(
        asset_id: int,
        asset_to_traders: dict
    ) -> str:
    traders = asset_to_traders.get(str(asset_id), ["Unknown/Direct"])
    return " | ".join(sorted(traders))

def generate_dataframe(
        df_json: list, # Note que json_data costuma vir como lista de dicts
        df_api: pd.DataFrame
    ):
    # 1. Verificação inicial: Se o DataFrame da API é inválido ou vazio
    if df_api is None or df_api.empty:
        return pd.DataFrame(columns=['Valor Atual em Aberto', 'Lucro Flutuante (Unrealized)', 'Lucro Realizado (Closed)'])

    # 2. Mapeamento de Traders do JSON
    asset_to_traders = {}
    for t in df_json:
        asset = str(t.get('asset_id', ''))
        trader = t.get('copy_from', 'Unknown')
        if asset:
            if asset not in asset_to_traders:
                asset_to_traders[asset] = set()
            asset_to_traders[asset].add(trader)

    # 3. Verificação de Colunas Críticas antes de processar
    # Se 'asset' não existir, criamos como 'Desconhecido' para não quebrar o apply
    if 'asset' not in df_api.columns:
        df_api['asset'] = 'Unknown'
    
    df_api['trader_followed'] = df_api['asset'].apply(lambda x: get_traders(x, asset_to_traders))

    # 4. Garantir colunas numéricas com segurança
    numeric_cols = ['curPrice', 'avgPrice', 'size', 'realizedPnl', 'initialValue']
    for col in numeric_cols:
        if col in df_api.columns:
            df_api[col] = pd.to_numeric(df_api[col], errors='coerce').fillna(0)
        else:
            df_api[col] = 0.0 # Cria a coluna com zero se ela não existir

    # 5. Cálculos (Agora seguros pois garantimos que as colunas existem)
    df_api['unrealized_pnl_usd'] = (df_api['curPrice'] - df_api['avgPrice']) * df_api['size']
    df_api['total_value_usd'] = df_api['curPrice'] * df_api['size']

    # 6. Tratamento da coluna 'active'
    if 'active' in df_api.columns:
        df_api['active_bool'] = df_api['active'].apply(lambda x: str(x).upper() in ['TRUE', 'VERDADEIRO', '1'])
    else:
        df_api['active_bool'] = False

    # 7. Agrupamento (Summary)
    # Usamos fillna(0) no final para garantir que o Streamlit não mostre NaN
    summary = df_api.groupby('trader_followed').agg({
        'total_value_usd': 'sum',
        'unrealized_pnl_usd': 'sum',
        'realizedPnl': 'sum'
    }).rename(columns={
        'total_value_usd': 'Valor Atual em Aberto',
        'unrealized_pnl_usd': 'Lucro Flutuante (Unrealized)',
        'realizedPnl': 'Lucro Realizado (Closed)'
    }).fillna(0)

    return summary

def generate_reports(df_json: list, df_api: pd.DataFrame):
    if df_api is None or df_api.empty:
        empty_df = pd.DataFrame()
        return empty_df, empty_df, empty_df

    # --- 1. Mapeamento de Traders (Mesma lógica) ---
    asset_to_traders = {}
    for t in df_json:
        asset = str(t.get('asset_id', ''))
        trader = t.get('copy_from', 'Unknown')
        if asset:
            if asset not in asset_to_traders:
                asset_to_traders[asset] = set()
            asset_to_traders[asset].add(trader)

    # --- 2. Limpeza e Proteção de Colunas ---
    # Garantir que colunas textuais existam
    if 'asset' not in df_api.columns: df_api['asset'] = 'Unknown'
    if 'title' not in df_api.columns: df_api['title'] = 'N/A' # Garantia da coluna title
    
    df_api['trader_followed'] = df_api['asset'].apply(lambda x: get_traders(x, asset_to_traders))

    # Garantir colunas numéricas
    numeric_cols = ['curPrice', 'avgPrice', 'size', 'realizedPnl', 'initialValue']
    for col in numeric_cols:
        if col in df_api.columns:
            df_api[col] = pd.to_numeric(df_api[col], errors='coerce').fillna(0)
        else:
            df_api[col] = 0.0

    # Cálculos
    df_api['unrealized_pnl_usd'] = (df_api['curPrice'] - df_api['avgPrice']) * df_api['size']
    df_api['total_value_usd'] = df_api['curPrice'] * df_api['size']

    # --- 3. Separação: Abertas vs Fechadas ---
    if 'active' in df_api.columns:
        df_api['is_active'] = df_api['active'].apply(lambda x: str(x).upper() in ['TRUE', '1'])
    else:
        df_api['is_active'] = False

    df_open = df_api[df_api['is_active'] & (df_api['size'] > 0)].copy()
    df_closed = df_api[~df_api['is_active'] | (df_api['size'] <= 0)].copy()

    # --- 4. Sumário por Trader ---
    summary = df_api.groupby('trader_followed').agg({
        'total_value_usd': 'sum',
        'unrealized_pnl_usd': 'sum',
        'realizedPnl': 'sum'
    }).rename(columns={
        'total_value_usd': 'Valor Aberto (USD)',
        'unrealized_pnl_usd': 'P&L Não Realizado',
        'realizedPnl': 'P&L Realizado'
    }).fillna(0)

    return df_open, df_closed, summary

def run():
    user = _select_user()
    
    # Mantendo sua lógica de bloqueio se não houver wallet
    wallet = st.session_state.get('copytrade_wallet')
    if wallet is None: 
        st.info("Aguardando carteira...")
        return

    json_data = recieve_json()
    if json_data is None: 
        return

    # Busca os dados da API (com cache simples no session_state)
    if st.session_state.get("df_api") is None or st.session_state.get("last_wallet") != wallet:
        with st.spinner("Carregando dados do Polymarket..."):
            data = get_api_data(wallet)
            if data is not None:
                st.session_state['df_api'] = data
                st.session_state['last_wallet'] = wallet

    # Se temos os dados, geramos os três reports
    if st.session_state.get('df_api') is not None:
        df_open, df_closed, summary = generate_reports(json_data, st.session_state['df_api'])

        # --- UI Dashboard ---
        st.divider()
        
        # Métricas Rápidas no Topo
        m1, m2, m3 = st.columns(3)
        m1.metric("Lucro Realizado Total", f"${df_closed['realizedPnl'].sum():,.2f}")
        m2.metric("Lucro Flutuante", f"${df_open['unrealized_pnl_usd'].sum():,.2f}", 
                  delta=f"{df_open['unrealized_pnl_usd'].sum():,.2f}")
        m3.metric("Capital em Aberto", f"${df_open['total_value_usd'].sum():,.2f}")

        # Abas para os DataFrames
        tab1, tab2, tab3 = st.tabs(["📊 Sumário por Trader", "🟢 Posições Abertas", "🔴 Histórico/Fechadas"])

        with tab1:
            st.dataframe(summary.style.format("${:,.2f}"), use_container_width=True)

        with tab2:
            if not df_open.empty:
                cols_to_show = ['title', 'outcome', 'trader_followed', 'size', 'avgPrice', 'curPrice', 'unrealized_pnl_usd']
                st.dataframe(df_open[cols_to_show], use_container_width=True)
            else:
                st.write("Nenhuma posição aberta no momento.")

        with tab3:
            if not df_closed.empty:
                cols_to_show_closed = ['title', 'outcome', 'trader_followed', 'size', 'avgPrice', 'realizedPnl']
                st.dataframe(df_closed[cols_to_show_closed], use_container_width=True)
            else:
                st.write("Nenhum histórico de posições fechadas.")