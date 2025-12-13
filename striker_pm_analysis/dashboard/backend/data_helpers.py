import math
import pandas as pd
import streamlit as st
from datetime import datetime
from helpers import safe_divide
from dashboard.ui import formatting
from dashboard.data.analysis import DataAnalyst


def filter_and_format_closed(
        df: pd.DataFrame
    ) -> pd.DataFrame.style:
    
    if df.empty:
        return df

    if 'tags' not in df.columns:
        df['tags'] = "[]" 

    
    new_df = df[[
        'endDate', 'title', 'outcome',
        'totalBought', 'avgPrice', 'curPrice',
        'realizedPnl', 'slug', 'tags'
    ]].copy()


    new_df = new_df.rename(columns={
        'endDate': 'End Date',
        'avgPrice': 'Average Price',
        'totalBought': 'Shares Bought',
        'realizedPnl': 'Realized Profit',
        'curPrice': 'Current Price',
        'title': 'Event',
        'outcome': 'Bet',
        'slug': 'Slug',
        'tags': 'Tags'
    })

    # 3. Criar versões formatadas
    df_fmt = pd.DataFrame()

    # Data
    df_fmt["End Date"] = pd.to_datetime(new_df["End Date"])

    df_fmt["Event"] = new_df["Event"]
    df_fmt["Bet"] = new_df["Bet"]
    df_fmt["Slug"] = new_df["Slug"]

    # Números
    df_fmt["Shares Bought"] = new_df["Shares Bought"]
    df_fmt["Average Price"] = new_df["Average Price"]
    df_fmt["Staked ($)"] = new_df["Shares Bought"] * new_df['Average Price']
    df_fmt["Current Price"] = new_df["Current Price"]

    df_fmt["Realized Profit"] = new_df["Realized Profit"]
    df_fmt["ROI (%)"] = safe_divide(df_fmt["Realized Profit"], df_fmt["Staked ($)"])

    # Tags (Agora seguro)
    df_fmt["Tags"] = new_df["Tags"].apply(formatting.format_tags)

    # 4. APLICAR FORMATAÇÃO E CORES
    styler = (
        df_fmt.style
        .format({
            "End Date": lambda d: d.strftime("%d/%m/%Y"), 
            "Shares Bought": "{:.2f}",
            "Average Price": "{:.2f}",
            "Current Price": "{:.2f}",
            "Staked ($)": formatting.float_to_dol,
            "Realized Profit": formatting.float_to_dol,
            "ROI (%)": formatting.float_to_pct
        })
        .map(
            formatting.color_positive_negative,
            subset=["Realized Profit", "ROI (%)"]
        )
    )

    return styler


def filter_and_format_active(
        df: pd.DataFrame
    ) -> pd.DataFrame.style:
    """
    Formata o DataFrame de posições ativas para exibição no Streamlit.
    """
    

    if df.empty:
        return df
        
    if 'tags' not in df.columns:
        df['tags'] = "[]"

    
    # 1. PREPARAR O DF
    df = df.copy()
    df['total_profit'] = df['cashPnl'] + df['realizedPnl']

    # 2. FILTRAR
    cols_to_keep = [
        'endDate', 'title', 'outcome', 
        'size', 'totalBought', 'avgPrice', 'curPrice', 
        'cashPnl', 'realizedPnl', 'total_profit', 
        'slug', 'tags'
    ]
    
    # Filtra apenas o que existe (segurança extra), mas garantimos tags acima
    existing_cols = [col for col in cols_to_keep if col in df.columns]
    new_df = df[existing_cols].copy()

    # 3. RENOMEAR
    new_df = new_df.rename(columns={
        'endDate': 'End Date',
        'avgPrice': 'Average Price',
        'size': 'Current Shares',
        'totalBought': 'Total Shares Bought',
        'realizedPnl': 'Realized Profit',
        'cashPnl': 'Unrealized Profit',
        'curPrice': 'Current Price',
        'title': 'Event',
        'outcome': 'Bet',
        'slug': 'Slug',
        'tags': 'Tags',
        'total_profit': 'Total Profit',
    })

    # 4. CRIAR VERSÕES FORMATADAS
    df_fmt = pd.DataFrame()

    df_fmt["End Date"] = pd.to_datetime(new_df["End Date"])
    df_fmt["Event"] = new_df["Event"]
    df_fmt["Bet"] = new_df["Bet"]
    df_fmt["Slug"] = new_df["Slug"]

    df_fmt["Current Shares"] = new_df["Current Shares"]
    df_fmt["Average Price"] = new_df["Average Price"]
    df_fmt["Staked ($)"] = new_df["Current Shares"] * new_df['Average Price']
    df_fmt["Current Price"] = new_df["Current Price"]

    df_fmt["Unrealized Profit"] = new_df["Unrealized Profit"]
    df_fmt["Realized Profit"] = new_df["Realized Profit"]
    df_fmt["Total Profit"] = new_df["Total Profit"]
    df_fmt["ROI (%)"] = safe_divide(df_fmt["Total Profit"], df_fmt["Staked ($)"])

    df_fmt["Tags"] = new_df["Tags"].apply(formatting.format_tags)

    # 5. APLICAR FORMATAÇÃO E CORES
    styler = (
        df_fmt.style
        .format({
            "End Date": lambda d: d.strftime("%d/%m/%Y"), 
            "Current Shares": "{:,.2f}",
            "Average Price": "{:,.2f}",
            "Current Price": "{:,.2f}",
            "Staked ($)": formatting.float_to_dol,
            "Unrealized Profit": formatting.float_to_dol,
            "Realized Profit": formatting.float_to_dol,
            "Total Profit": formatting.float_to_dol,
            "ROI (%)": formatting.float_to_pct
        })
        .map(
            formatting.color_positive_negative,
            subset=["Unrealized Profit", "Realized Profit", "Total Profit", "ROI (%)"] 
        )
    )

    return styler


def cum_pnl(
    df: pd.DataFrame,
    pnl_column: str = 'realizedPnl',
    date_column: str = 'endDate'
) -> pd.DataFrame: 
    """
    Recebe um dataframe e retorna um DataFrame com o
    lucro diário e o lucro cumulativo.
    Colunas: ['Date', 'Daily Profit', 'Cumulative Profit']
    """
    df = df.copy()
    
    df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
    df = df.sort_values(by=date_column)
    
   
    daily_profit = df.groupby(df[date_column].dt.normalize())[pnl_column].sum()
    out_df = daily_profit.reset_index()
    out_df.columns = ['Date', 'Profit']
    
    # 4. Calcular o lucro CUMULATIVO
    out_df['Cumulative Profit'] = out_df['Profit'].cumsum()
        
    return out_df


def create_daily_summary(
    df: pd.DataFrame,
    pnl_column: str = 'realizedPnl',
    date_column: str = 'endDate'
) -> pd.DataFrame:
    
    df = df.copy()

    df[date_column] = pd.to_datetime(
        df[date_column],
        format='ISO8601',
        utc=True)
    df = df.sort_values(by=date_column)
    
    df['staked'] = df['totalBought'] * df['avgPrice']
    df['roi'] = safe_divide(df[pnl_column], df['staked'])

    rows = []

    for date, sub_df in df.groupby(df[date_column].dt.normalize()):
        profit = sub_df[pnl_column].sum()
        bets = len(sub_df)
        roi = safe_divide(profit, sub_df['staked'].sum())
        units = sub_df['roi'].sum()

        rows.append({
            "Date": date,
            "Bets": bets,
            "Profit": profit,
            "ROI": roi,
            "Units": units,
        })

    out = pd.DataFrame(rows).sort_values(by='Date', ascending=False)

    # Formatar coluna de data para YYYY-MM-DD
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")

    # Aplicar formatações
    styler = (
        out.style
            .format({
                "Profit": formatting.float_to_dol,
                "ROI": formatting.float_to_pct,
                "Units": formatting.float_to_units,
            })
            .map(formatting.color_positive_negative, subset=["Profit", "ROI", "Units"])
    )

    return styler


def get_tag_list(
    df:pd.DataFrame
    ) -> list:
    # Retorna a lista de Tags do User
    return DataAnalyst.tag_analysis(df=df)['tag'].unique()


def create_tag_df(
    df: pd.DataFrame,
    stake: float,
    start_date,
    end_date,
    ) -> pd.DataFrame:
    

    if df.empty:
        return df # Retorna vazio se a entrada for vazia
        
    df = df.copy()
    
    if 'tags' not in df.columns:
        df['tags'] = "[]"

    
    # Filtrar o dataframe
    df["endDate"] = pd.to_datetime(df['endDate'], format='ISO8601', utc=True).dt.tz_localize(None)
    df["endDate"] = pd.to_datetime(df["endDate"], utc=False, errors="coerce")
    
    if isinstance(start_date, (datetime, pd.Timestamp)) and \
       isinstance(end_date, (datetime, pd.Timestamp)):
        
        df = df[(df["endDate"] >= start_date) &
                (df["endDate"] <= end_date)]

    if stake is not None:
        df["calculated_stake"] = df["totalBought"] * df["avgPrice"]
        df = df[df["calculated_stake"] > stake]
    
    tag_df = DataAnalyst.tag_analysis(df=df)
    
    tag_df = tag_df.rename(columns={
        'tag': 'Tag',
        'profit': 'Profit',
        'volume': 'Staked',
        'roi': 'ROI',
        'units': 'Units',
        'bets': 'Total Bets',
    })
    
    styler = (
        tag_df.style
            .format({
                'Profit': formatting.float_to_dol,
                'Staked': formatting.float_to_dol,
                'ROI': formatting.float_to_pct,
                'Units': formatting.float_to_units,
            })
            .map(
                formatting.color_positive_negative,
                subset=['Profit', 'ROI', 'Units'] 
            )
    )
        
    return styler


def render_paginated_table(
    df: pd.DataFrame,
    unique_key: str,
    page_size: int = 20,
    format_func: callable = None,
    csv_df: pd.DataFrame = None,
    csv_file_name: str = "data.csv",
    **st_dataframe_kwargs
    ) -> None:
    """
    Renderiza um DataFrame paginado com controles de navegação e download.
    
    Args:
        df: O DataFrame completo (fonte de dados).
        unique_key: Uma string única para controlar o session_state desta tabela específica.
        page_size: Itens por página.
        format_func: (Opcional) Função para formatar APENAS a fatia visível (ex: adicionar R$, %).
        csv_df: (Opcional) DataFrame específico para o CSV. Se None, usa o 'df' original.
        csv_file_name: Nome do arquivo para download.
        **st_dataframe_kwargs: Argumentos extras passados direto para st.dataframe (ex: column_config).
    """
    
    # 1. Gerenciamento de Estado (Página Atual)
    session_key = f"{unique_key}_current_page"
    
    if session_key not in st.session_state:
        st.session_state[session_key] = 1
        
    total_rows = len(df)
    total_pages = math.ceil(total_rows / page_size)
    
    # Resetar para pág 1 se filtros mudarem e a pág atual ficar fora do range
    if st.session_state[session_key] > total_pages and total_pages > 0:
        st.session_state[session_key] = 1
    elif total_pages == 0:
        st.session_state[session_key] = 1

    # Callbacks de Navegação
    def prev_page():
        st.session_state[session_key] = max(1, st.session_state[session_key] - 1)
        
    def next_page():
        st.session_state[session_key] = min(total_pages, st.session_state[session_key] + 1)

    # 2. Informação de Status
    st.caption(f"Page **{st.session_state[session_key]}** of **{max(1, total_pages)}** (Total: {total_rows} items)")

    # 3. Fatiamento (Slicing)
    if total_rows > 0:
        start_idx = (st.session_state[session_key] - 1) * page_size
        end_idx = start_idx + page_size
        
        # Pega a fatia bruta
        df_slice = df.iloc[start_idx:end_idx].copy()
        
        # Aplica formatação visual (se fornecida)
        if format_func:
            display_data = format_func(df_slice)
        else:
            display_data = df_slice
            
        # 4. Renderiza Tabela
        st.dataframe(
            display_data,
            width='stretch',
            **st_dataframe_kwargs # Repassa configs como hide_index, column_order, etc.
        )
    else:
        st.info("No data available.")

    # 5. Controles (Botões)
    cols = st.columns([1, 1, 3, 2])
    
    with cols[0]:
        st.button(
            "Previous", 
            on_click=prev_page, 
            disabled=(st.session_state[session_key] <= 1),
            key=f"{unique_key}_btn_prev",
            width='stretch'
        )
        
    with cols[1]:
        st.button(
            "Next", 
            on_click=next_page, 
            disabled=(st.session_state[session_key] >= total_pages),
            key=f"{unique_key}_btn_next",
            width='stretch'
        )
        
    with cols[3]:
        # Prepara dados para CSV (Usa csv_df se fornecido, senão usa o df original)
        data_to_download = csv_df if csv_df is not None else df
        csv_bytes = data_to_download.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="Download CSV",
            data=csv_bytes,
            file_name=csv_file_name,
            mime='text/csv',
            key=f"{unique_key}_btn_download",
            width='stretch'
        )