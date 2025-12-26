import pandas as pd
import os
import asyncio
from striker_polymarket_api.rest import fetch_all_positions
from managers.trade_manager import load_trade_history

async def generate_segmented_report(user_address: str):
    output_path = "../files/relatorio_detalhado_api.xlsx"
    
    # 1. Coleta dados oficiais da API (Retorna Live e Closed)
    print("📡 Puxando dados da Blockchain...")
    df_api = await asyncio.to_thread(fetch_all_positions, user_address)
    
    if df_api is None or df_api.empty:
        print("⚠️ Nenhuma posição encontrada na API.")
        return

    # 2. Mapeamento de Metadados (Traders)
    local_history = load_trade_history()
    asset_to_traders = {}
    for t in local_history:
        asset = str(t.get('asset_id', ''))
        trader = t.get('copy_from', 'Unknown')
        if asset:
            if asset not in asset_to_traders:
                asset_to_traders[asset] = set()
            asset_to_traders[asset].add(trader)

    def get_traders(asset_id):
        traders = asset_to_traders.get(str(asset_id), ["Unknown/Direct"])
        return " | ".join(sorted(traders))

    # 3. Preparação do DataFrame Geral com Tags e Cálculos
    df_api['trader_followed'] = df_api['asset'].apply(get_traders)
    
    # Garantir que colunas críticas são numéricas para evitar erros no Excel
    numeric_cols = ['curPrice', 'avgPrice', 'size', 'realizedPnl', 'initialValue']
    for col in numeric_cols:
        if col in df_api.columns:
            df_api[col] = pd.to_numeric(df_api[col], errors='coerce').fillna(0)

    df_api['unrealized_pnl_usd'] = (df_api['curPrice'] - df_api['avgPrice']) * df_api['size']
    df_api['total_value_usd'] = df_api['curPrice'] * df_api['size']

    # 4. SEPARAÇÃO REFORMULADA (Baseada na coluna 'active')
    # Live: O mercado ainda está rolando (active == True)
    # Closed: O mercado acabou ou a posição foi zerada (active == False ou size == 0)
    
    # Tratamento para garantir que comparamos booleanos ou strings corretamente
    df_api['active_bool'] = df_api['active'].apply(lambda x: str(x).upper() in ['TRUE', 'VERDADEIRO', '1'])
    
    df_live = df_api[(df_api['active_bool'] == True) & (df_api['size'] > 0)].copy()
    df_closed = df_api[(df_api['active_bool'] == False) | (df_api['size'] <= 0)].copy()

    # 5. Somatório por Trader
    summary = df_api.groupby('trader_followed').agg({
        'total_value_usd': 'sum',
        'unrealized_pnl_usd': 'sum',
        'realizedPnl': 'sum'
    }).rename(columns={
        'total_value_usd': 'Valor Atual em Aberto',
        'unrealized_pnl_usd': 'Lucro Flutuante (Unrealized)',
        'realizedPnl': 'Lucro Realizado (Closed)'
    })

    # 6. Exportação com Verificação de Conteúdo
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Aba 1: Live
        if not df_live.empty:
            df_live.drop(columns=['active_bool']).to_excel(writer, sheet_name='Live Positions', index=False)
        else:
            pd.DataFrame([["Nenhuma posição ativa"]]).to_excel(writer, sheet_name='Live Positions', header=False, index=False)
            
        # Aba 2: Closed (Aqui entrarão os 4 datapoints que a API reportou)
        if not df_closed.empty:
            df_closed.drop(columns=['active_bool']).to_excel(writer, sheet_name='Closed Positions', index=False)
        else:
            pd.DataFrame([["Nenhuma posição encerrada"]]).to_excel(writer, sheet_name='Closed Positions', header=False, index=False)
            
        # Aba 3: Resumo
        summary.to_excel(writer, sheet_name='Somatório por Trader')

    print(f"✅ Relatório atualizado com {len(df_live)} Live e {len(df_closed)} Closed.")

if __name__ == "__main__":
    load_dotenv()
    funder = os.getenv("FUNDER")
    asyncio.run(generate_segmented_report(funder))