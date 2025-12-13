import pandas as pd
import streamlit as st
from striker_polymarket_api.rest import number_of_trades
from striker_polymarket_api.subgraph import fetch_pnl_data
from dashboard.ui.formatting import center_text


def select_user(
    ) -> str:
    # Retora um user válido    
    st.subheader("Select User")

    # campo de input do chat
    user_address = st.chat_input("Type user address")
    center_text('Hint: 0x9930084378ad9040b656c7d0945bde5e4db32afc', size=12)
    
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
            st.session_state["selected_wallet"] = user_address
            return user_address

       
def get_trades(
    user_address: str
    ) -> pd.DataFrame:
    # Wrapper para puxar todas as Posições do User
    with st.spinner("Fetching trades..."):
        return fetch_pnl_data(user_address)

def merge_dfs(
    closed_df: pd.DataFrame, 
    active_df: pd.DataFrame
):
    # Recebe os dois dataframes e cria um só
    
    # 1. União com ignore_index (Evita índices duplicados que quebram a UI)
    merge_df = pd.concat([active_df, closed_df], ignore_index=True)
    
    # 2. Proteção contra DataFrame Vazio
    if merge_df.empty:
        # Retorna estrutura mínima para não dar erro de "KeyError" lá na frente
        cols = ['realizedPnl', 'cashPnl', 'total_profit', 'tags', 'endDate']
        return pd.DataFrame(columns=cols)

    # 3. 🔥 A CORREÇÃO DO LOG: Garante que 'tags' existe
    if 'tags' not in merge_df.columns:
        merge_df['tags'] = "[]"
    else:
        # Se existir mas tiver buracos (NaN), preenche com lista vazia string
        merge_df['tags'] = merge_df['tags'].fillna("[]")

    # 4. Garante colunas de PnL
    if 'realizedPnl' not in merge_df.columns:
        merge_df['realizedPnl'] = 0.0
    
    if 'cashPnl' not in merge_df.columns:
        merge_df['cashPnl'] = 0.0

    merge_df['total_profit'] = merge_df['realizedPnl'].fillna(0) + merge_df['cashPnl'].fillna(0)
    
    return merge_df