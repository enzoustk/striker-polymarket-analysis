import json
import pandas as pd
import streamlit as st
from src.ui import elements, formatting
from striker_polymarket_api.rest import number_of_trades
from striker_polymarket_api.rest import fetch_all_positions

def _select_user(
    ) -> str:
    """Interface para seleção de usuário via chat input."""
    user_address = st.chat_input("Type user wallet to start")
    
    if user_address:
        wallet_trades = number_of_trades(user_address)
        if wallet_trades == -1:
            st.error("Invalid Wallet.")
        else:
            st.success(
                f"Carteira **{user_address}** válida.\n"
                f"Total de Traded Markets: **{wallet_trades}**"
            )
            st.session_state["copytrade_wallet"] = user_address
            return user_address
    return st.session_state.get("copytrade_wallet")

def get_api_data(
    user_address: str
    ) -> pd.DataFrame:
    """Busca dados brutos da API do Polymarket."""
    try:
        df_api = fetch_all_positions(user_address)
        if df_api is None or df_api.empty:
            st.error("No position found for the given address.")
            return None
        return df_api
    except Exception as e:
        st.error(f"Error searching data: {e}")
        return None

def recieve_json():
    """Componente de upload de arquivo JSON de configuração."""
    uploaded_file = st.file_uploader("Drag and drop the JSON file", type=["json"])
    if uploaded_file is not None:
        try:    
            json_data = json.load(uploaded_file)
            st.success("Json Loaded.")
            return json_data
        except json.JSONDecodeError:
            st.error("Invalid Json.")
    return None

def get_traders(
    asset_id: int,
    asset_to_traders: dict
    ) -> str:
    """Retorna os nomes dos traders seguidos para um determinado asset."""
    traders = asset_to_traders.get(str(asset_id), ["Unknown/Direct"])
    return " | ".join(sorted(traders))

def enrich_api_data(
    df_api: pd.DataFrame,
    df_json: list
    ) -> tuple[pd.DataFrame, list]:
    """Prepara o DataFrame com mapeamento de traders e cálculos iniciais."""
    df = df_api.copy()
    
    # 1. Mapeamento de Traders do JSON
    asset_to_traders = {}
    unique_traders = set()
    for t in df_json:
        asset = str(t.get('asset_id', ''))
        trader = t.get('copy_from', 'Unknown')
        if asset:
            if asset not in asset_to_traders: 
                asset_to_traders[asset] = set()
            asset_to_traders[asset].add(trader)
            unique_traders.add(trader)

    # Permitir filtrar trades manuais ou não mapeados via UI
    unique_traders.add("Unknown/Direct")

    # 2. Adição de colunas e tratamento de tipos
    if 'asset' not in df.columns: df['asset'] = 'Unknown'
    if 'title' not in df.columns: df['title'] = 'N/A'
    
    df['trader_followed'] = df['asset'].apply(lambda x: get_traders(x, asset_to_traders))

    numeric_cols = ['curPrice', 'avgPrice', 'size', 'realizedPnl', 'initialValue']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0.0

    df['unrealized_pnl_usd'] = (df['curPrice'] - df['avgPrice']) * df['size']
    df['total_value_usd'] = df['curPrice'] * df['size']
    
    if 'active' in df.columns:
        df['is_active'] = df['active'].apply(lambda x: str(x).upper() in ['TRUE', '1', 'VERDADEIRO'])
    else:
        df['is_active'] = False

    return df, sorted(list(unique_traders))

def apply_filters(
    df: pd.DataFrame,
    selected_traders: list,
    start_date,
    end_date,
    min_stake
    ):
    """Aplica os filtros de usuário ao DataFrame enriquecido."""
    filtered = df.copy()

    # 1. Filtro de Tempo (Normalização para evitar conflito datetime vs date)
    if 'endDate' in filtered.columns:
        filtered["endDate"] = pd.to_datetime(filtered['endDate'], errors="coerce")
        if start_date and end_date:
            sd = pd.to_datetime(start_date).date()
            ed = pd.to_datetime(end_date).date()
            filtered = filtered[
                (filtered["endDate"].dt.date >= sd) & 
                (filtered["endDate"].dt.date <= ed)
            ]

    # 2. Filtro de Stake
    if min_stake > 0:
        if 'totalBought' in filtered.columns and 'avgPrice' in filtered.columns:
            filtered["calculated_stake"] = filtered["totalBought"] * filtered["avgPrice"]
            filtered = filtered[filtered["calculated_stake"] >= min_stake]
        elif 'initialValue' in filtered.columns:
            filtered = filtered[filtered['initialValue'] >= min_stake]

    # 3. Filtro por Trader
    if selected_traders:
        mask = filtered['trader_followed'].apply(
            lambda x: any(trader in x for trader in selected_traders)
        )
        filtered = filtered[mask]

    return filtered

def run():
    """Função principal para renderizar a página do Reporter."""
    formatting.center_text("Copy Trade Strategy Reporter", size=50, bold=True)
    
    wallet = _select_user()
    if not wallet:
        return

    json_data = recieve_json()
    if not json_data:
        return

    # Gerenciamento de Dados (Cache)
    if (st.session_state.get("df_api_full") is None or 
        st.session_state.get("last_wallet") != wallet):
        
        with st.spinner("Loading data..."):
            raw_data = get_api_data(wallet)
            if raw_data is not None:
                enriched_df, traders_list = enrich_api_data(raw_data, json_data)
                st.session_state['df_api_full'] = enriched_df
                st.session_state['traders_available'] = traders_list
                st.session_state['last_wallet'] = wallet
            else:
                return

    df_full = st.session_state['df_api_full']
    traders_list = st.session_state['traders_available']

    # Seção de Filtros
    st.header('Filtros de Análise')
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    
    with f_col1:
        selected_traders = st.pills("Filter by Trader", options=traders_list, selection_mode="multi")
    
    with f_col2:
        _, start_date, end_date = elements.time_filter_buttons(df_full)
    
    with f_col3:
        min_stake = elements.stake()

    # Aplicação de Filtros
    df_filtered = apply_filters(df_full, selected_traders, start_date, end_date, min_stake)
    
    # Segmentação baseada no estado e tamanho da posição
    df_open = df_filtered[df_filtered['is_active'] & (df_filtered['size'] > 0)].copy()
    df_closed = df_filtered[~df_filtered['is_active'] | (df_filtered['size'] <= 0)].copy()

    # Sumário por Trader
    summary = df_filtered.groupby('trader_followed').agg({
        'total_value_usd': 'sum',
        'unrealized_pnl_usd': 'sum',
        'realizedPnl': 'sum'
    }).rename(columns={
        'total_value_usd': 'Live Positions (USD)',
        'unrealized_pnl_usd': 'Unrealized PnL',
        'realizedPnl': 'Realized PnL'
    }).fillna(0)

    # Exibição do Dashboard
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Realized PnL", f"${df_closed['realizedPnl'].sum():,.2f}")
    m2.metric("Unrealized PnL", f"${df_open['unrealized_pnl_usd'].sum():,.2f}")
    m3.metric("Live Positions", f"${df_open['total_value_usd'].sum():,.2f}")
    m4.metric("Total Trades", len(df_filtered))

    tab1, tab2, tab3, tab4 = st.tabs([
        "Trader Overview", 
        "Open Positions", 
        "Closed Positions",
        "All Trades"
    ])

    with tab1:
        st.dataframe(summary.style.format("${:,.2f}"), width='stretch')

    with tab2:
        if not df_open.empty:
            cols = ['title', 'outcome', 'trader_followed', 'size', 'avgPrice', 'curPrice', 'unrealized_pnl_usd']
            st.dataframe(df_open[cols], width='stretch', hide_index=True)
        else:
            st.info("No position found for the given filters.")

    with tab3:
        if not df_closed.empty:
            cols = ['title', 'outcome', 'trader_followed', 'size', 'avgPrice', 'realizedPnl']
            st.dataframe(df_closed[cols], width='stretch', hide_index=True)
        else:
            st.info("No position found for the given filters")

    with tab4:
        if not df_filtered.empty:
            # Visão completa de todo e qualquer trade filtrado
            all_cols = ['title', 'outcome', 'trader_followed', 'size', 'avgPrice', 'curPrice', 'realizedPnl', 'unrealized_pnl_usd', 'is_active']
            st.dataframe(df_filtered[all_cols], width='stretch', hide_index=True)
        else:
            st.info("No trade Found.")