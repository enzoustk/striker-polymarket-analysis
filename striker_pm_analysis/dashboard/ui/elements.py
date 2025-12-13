import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from helpers import get_exploded_df
from dashboard.ui.formatting import *
from dashboard.data.analysis import DataAnalyst
from dashboard.backend import data_helpers as dh


def top_bar():
        # TODO: Add image
        # img_cols = st.columns([2.8,3.5])
        # with img_cols[1]:
        #     st.image('images/striker_logo/logo-reduzido_branco.png', width=150)
        center_text('Powered by Striker', size=12)


def user_stats(
    df: pd.DataFrame
    ) -> None:
    
    if df.empty:
        profit, staked, roi = 0.0, 0.0, 0.0
        stats = {
            'flat_profit': 0.0,
            'avg_stake': 0.0,
            'median_stake': 0.0
        }
    else:
        profit, staked, roi = DataAnalyst.calculate_stats(df)
        stats = DataAnalyst.calculate_advanced_stats(df)
    # --------------------------------
    
    # --- Linha 1: 4 Métricas Principais ---
    cols1 = st.columns(4)
    cols1[0].metric(label="Profit", value=float_to_dol(profit))
    cols1[1].metric(label="ROI", value=float_to_pct(roi))
    cols1[2].metric(label="Staked", value=float_to_dol(staked))
    cols1[3].metric(label="Flat Profit", value=float_to_units(stats['flat_profit']))

    # --- Linha 2: 3 Métricas Avançadas ---
    cols2 = st.columns(4)
    cols2[0].metric(label="Total Trades", value=len(df))
    cols2[1].metric(label="Avg Stake", value=float_to_dol(stats['avg_stake']))
    cols2[2].metric(label="Median Stake", value=float_to_dol(stats['median_stake']))
    cols2[3].metric(label="Max Drawdown", value='Loading...')


def cum_profit(
    df: pd.DataFrame
    ) -> None:
    
    st.subheader('Cumulative Profit')

    if df.empty:
        st.info("No data available to plot cumulative profit.")
        return

    cum_profit = dh.cum_pnl(df=df, date_column='endDate')
    
    fig = px.area(
        cum_profit,
        x='Date',
        y='Cumulative Profit',
    )

    fig.update_layout(
        template='plotly_white',
        xaxis_title='Data',
        yaxis_title='Lucro Acumulado ($)',
        yaxis_tickprefix='$',
        xaxis_showgrid=False,
        yaxis_showgrid=False
    )
    
    fig.update_traces(
        line=dict(color='#00ADEF', width=2),   
        fillcolor='rgba(28, 55, 117, 0.2)', 
        hovertemplate="<b>Data:</b> %{x|%Y-%m-%d}<br><b>Lucro:</b> %{y:$,.2f}<extra></extra>"
    )

    st.plotly_chart(fig, width='stretch')

    
def daily_profit(
    df: pd.DataFrame
    ) -> None:
    st.subheader('PnL by Date')

    if df.empty:
        st.info("No data available.")
        return

    daily_profit_data = dh.create_daily_summary(df)
    
    st.dataframe(
        data=daily_profit_data,
        hide_index=True,
        width='stretch'
    )


def closed_positions(
    df: pd.DataFrame
    ) -> None:
    
    st.subheader('Closed Positions:')
    
    if df.empty:
        st.info("No closed positions found.")
        return


    df = df.copy()
    if 'endDate' in df.columns:
        df = df.sort_values(by='endDate', ascending=False)
    
    # 2. Definição segura das colunas para exportação
    # Só tenta pegar colunas que realmente existem no DF para evitar KeyError
    desired_cols = [
        'endDate', 'title', 'outcome', 'totalBought', 
        'avgPrice', 'curPrice', 'realizedPnl', 'slug', 'tags'
    ]
    existing_cols = [c for c in desired_cols if c in df.columns]

    # 3. Preparação do CSV
    csv_export_df = df[existing_cols].rename(columns={
        'endDate': 'End Date',
        'avgPrice': 'Average Price',
        'totalBought': 'Total Bought',
        'realizedPnl': 'Realized Profit',
        'curPrice': 'Current Price',
        'title': 'Event',
        'outcome': 'Bet'
    })

    df_config = {
        "hide_index": True,
        'column_config': {
            'Slug': None,
            'Tags': None
        }
    }

    dh.render_paginated_table(
        df=df,
        unique_key="closed_positions_table", 
        page_size=20,
        format_func=dh.filter_and_format_closed, 
        csv_df=csv_export_df,
        csv_file_name=f'closed_positions_{st.session_state.get("selected_wallet", "all")}.csv',
        **df_config 
    )


def tag_df(
    df: pd.DataFrame
    ) -> None:
    st.subheader('PnL by Market')

    dados_reais = df.data if hasattr(df, "data") else df
    if dados_reais.empty:
        st.info("No data available.")
        return

    st.dataframe(
        data=df,
        hide_index=True,
        column_order=[
            col for col in df.columns
            if col not in ["Staked"]],
        width='stretch'
    )


def time_filter_buttons(
    df: pd.DataFrame
    ) -> tuple:

    # Available filter options
    options = [
        "Current Week",
        "Current Month",
        "Previous Month",
        "Last 3 Months",
        "Last 6 Months",
        "Current Year",
        "Last Year",
        "Total",
        "Custom"
    ]

    today = datetime.today()

    # Default values
    start = None
    end = None

    selected = st.pills(
        label="Select Time Range",
        label_visibility="collapsed",
        options=options,
        default="Current Year",
    )

    if selected == "Current Week":
        start = today - timedelta(days=today.weekday())  # Monday of current week
        end = today

    elif selected == "Current Month":
        start = today.replace(day=1)
        end = today

    elif selected == "Previous Month":
        first_day_this_month = today.replace(day=1)
        last_day_prev_month = first_day_this_month - timedelta(days=1)
        start = last_day_prev_month.replace(day=1)
        end = last_day_prev_month

    elif selected == "Last 3 Months":
        start = today - relativedelta(months=3)
        end = today

    elif selected == "Last 6 Months":
        start = today - relativedelta(months=6)
        end = today

    elif selected == "Current Year":
        start = today.replace(month=1, day=1)
        end = today

    elif selected == "Last Year":
        start = datetime(today.year - 1, 1, 1)
        end = datetime(today.year - 1, 12, 31)

    elif selected == "Total":
        start = None
        end = None

    elif selected == "Custom":
        # Proteção se o DF estiver vazio e não tiver min/max date
        if not df.empty and "endDate" in df.columns:
            min_date = pd.to_datetime(df["endDate"]).min()
            max_date = pd.to_datetime(df["endDate"]).max()
        else:
            min_date = today
            max_date = today

        start, end = st.date_input(
            "Select a custom date range",
            value=(min_date, max_date),
        )

    return selected, start, end

 
def tag_buttons(
    tags: list
    ) -> list:
    
    if tags is None or len(tags) == 0:
        return []

    return st.pills(
        'Select Tags',
        label_visibility="collapsed",
        options=tags,
        selection_mode='multi'
        )

    
def get_filtered_df(
    df: pd.DataFrame,
    tags: list = [],
    stake: float | None = None,
    start_date=None,
    end_date=None
    ) -> dict:
    
    if df.empty:
        return {
            "raw": df,
            "main": df,
            "exploded": df
        }


    df = df.copy()

    # Normaliza datas
    if 'endDate' in df.columns:
        df["endDate"] = pd.to_datetime(df['endDate'], format='ISO8601', utc=True).dt.tz_localize(None)
        df["endDate"] = pd.to_datetime(df["endDate"], utc=False, errors="coerce")
    
    # Filtro de Data
    if isinstance(start_date, (datetime, pd.Timestamp)) and \
       isinstance(end_date, (datetime, pd.Timestamp)) and \
       'endDate' in df.columns:
        
        df = df[(df["endDate"] >= start_date) &
                (df["endDate"] <= end_date)]

    # Filtro de Stake
    if stake is not None and not df.empty:
        # Cria a coluna temporária calculada
        # Garante que as colunas existem antes de multiplicar
        if 'totalBought' in df.columns and 'avgPrice' in df.columns:
            df["calculated_stake"] = df["totalBought"] * df["avgPrice"]
            # Filtra onde o valor calculado é maior que a stake passada
            df = df[df["calculated_stake"] > stake]
    
    # exploded pós-filtro
    exploded_df = get_exploded_df(df=df)

    if tags and not exploded_df.empty:
        raw_df = exploded_df[exploded_df["tag"].isin(tags)]
        main_df = dh.filter_and_format_closed(raw_df)
        tag_trades_df = dh.filter_and_format_closed(raw_df)
    else:
        raw_df = df
        main_df = dh.filter_and_format_closed(df)
        tag_trades_df = dh.filter_and_format_closed(exploded_df)

    return {
        "raw": raw_df,
        "main": main_df,
        "exploded": tag_trades_df
    }


def stake(
    ) -> float:
    if "confirmed_stake" not in st.session_state:
        st.session_state.confirmed_stake = 100.00 

    def aplicar_valor():
        st.session_state.confirmed_stake = st.session_state.widget_stake

    def resetar_valor():
        st.session_state.widget_stake = 0.00
        st.session_state.confirmed_stake = 0.00

    st.number_input(
        label="Select Stake to Filter ($)",
        min_value=0.00,      
        value=0.0,        
        step=100.00,
        format="%.2f",
        help="Select the min USD size of all trades.",
        key="widget_stake"   
    )

    col1, col2 = st.columns(2)
    with col1:
        st.button("Apply", on_click=aplicar_valor, width='stretch')
    with col2:
        st.button("Reset", on_click=resetar_valor, width='stretch')

    st.caption(f"Current Filter: **${st.session_state.confirmed_stake:.2f}**")
    return st.session_state.confirmed_stake


def open_positions(df: pd.DataFrame) -> None:
    
    st.subheader('Open Positions:')

    if df.empty:
        st.info("No open positions found.")
        return

    
    # 1. Preparar DF
    df = df.copy()
    if 'endDate' in df.columns:
        df = df.sort_values(by='endDate', ascending=False)
    
    # 2. Definição segura das colunas para exportação
    csv_columns = [
        'endDate', 'title', 'outcome',
        'totalBought', 'avgPrice', 'curPrice', 'currentValue',
        'cashPnl', 'slug', 'tags'
    ]
    # Filtra colunas existentes
    existing_cols = [col for col in csv_columns if col in df.columns]
    
    csv_export_df = df[existing_cols].copy().rename(columns={
        'endDate': 'End Date',
        'avgPrice': 'Average Price',
        'totalBought': 'Total Bought',
        'cashPnl': 'Unrealized PnL',
        'currentValue': 'Current Value',
        'curPrice': 'Current Price',
        'title': 'Event',
        'outcome': 'Bet',
        'slug': 'Slug',
        'tags': 'Tags'
    })

    # 3. Configuração Visual
    df_config = {
        "hide_index": True,
        "column_config": {
            "Slug": None,  
            "Tags": None,  
        }
    }

    # 4. Renderização
    dh.render_paginated_table(
        df=df,
        unique_key="open_positions_table", 
        page_size=20,
        format_func=dh.filter_and_format_active, 
        csv_df=csv_export_df,
        csv_file_name=f'open_positions_{st.session_state.get("selected_wallet", "all")}.csv',
        **df_config 
    )
