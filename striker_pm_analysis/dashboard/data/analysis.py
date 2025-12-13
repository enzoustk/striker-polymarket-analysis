import pandas as pd
from helpers import safe_divide, to_list

class DataAnalyst:
    @staticmethod
    def calculate_advanced_stats(
        df:pd.DataFrame
        ) -> dict:

        df = df.copy()
        stats = {}
        
        df['staked'] = df['totalBought'] * df['avgPrice']
        df['roi'] = safe_divide(df['realizedPnl'], df['staked'])
        
        stats['flat_profit'] = df['roi'].sum()
        stats['avg_stake'] = df['staked'].mean()
        stats['median_stake'] = df['staked'].median() 
        
        return stats
    

    @staticmethod
    def calculate_stats(
        df: pd.DataFrame
        ) -> tuple[float,float,float]:
        """
        Recebe um dataframe, calcula e retorna:
        Profit, Vol e ROI
        """
        df = df.copy()
        
        df['total_profit'] = df['realizedPnl'].fillna(0)
        if 'cashPnl' in df.columns:
            df['total_profit'] += df['cashPnl'].fillna(0)
        
        df['volume'] = df['totalBought'] * df['avgPrice']
        df['roi'] = safe_divide(df['total_profit'], df['volume'])

        total_profit = df['total_profit'].sum()
        total_volume = df['volume'].sum()
        total_roi = safe_divide(total_profit, total_volume) or 0
        
        return total_profit, total_volume, total_roi
    

    @staticmethod
    def return_stats(
        df: pd.DataFrame
    ):
        """
        Alias para calculate_stats para compatibilidade com o dashboard.
        Recebe um dataframe, calcula e retorna:
        Profit, Vol e ROI
        """
        return DataAnalyst.calculate_stats(df)
    

    @staticmethod
    def tag_analysis(
        df: pd.DataFrame,
        min_bets: int = 50,
        exclude_tags: list = [],
        ):
        """
        Recebe um dataframe e retorna a análise do user por "tag"
        (Versão com LOGS DE DEBUG)
        """
        
        df = df.copy()
        
        # Verificar se a coluna 'tags' existe
        if 'tags' not in df.columns:
            print("ERRO: Coluna 'tags' não encontrada no DataFrame.")
            return pd.DataFrame(columns=['tag', 'profit', 'volume', 'roi', 'bets'])
                
        removed_tags = ['Games', 'Sports'] + exclude_tags
        
        # Passo 1: Criar o df
        tmp = df.copy()
        tmp['__tags_list'] = tmp['tags'].apply(to_list)
        exploded = tmp.explode('__tags_list', ignore_index=True)
        exploded = exploded.rename(columns={'__tags_list': 'tag'})
        exploded = exploded[exploded['tag'].notna()]
        exploded = exploded[~exploded['tag'].isin(removed_tags)]
        
        # LOG: Tags únicas encontradas
        unique_tags = exploded['tag'].unique()
        print(f"5. Tags Únicas encontradas ({len(unique_tags)}): {list(unique_tags)[:10]} ...") # Mostra só as 10 primeiras
        
        # Filtrar quais tags vamos estudar
        bets_per_tag = exploded.groupby('tag').size()
        valid_tags = bets_per_tag[bets_per_tag >= int(min_bets)].index

        result = []
        
        for tag in valid_tags:
            tag_df = exploded[exploded['tag'] == tag]
            profit, vol, roi = DataAnalyst.calculate_stats(tag_df)
            adv_stats = DataAnalyst.calculate_advanced_stats(tag_df)
            tag_data = {
                'tag': tag,
                'profit': profit,
                'volume': vol,
                'roi': roi,
                'units': adv_stats['flat_profit'],
                'bets': int(bets_per_tag.get(tag, 0))
            }
            result.append(tag_data)
       
        df_result = pd.DataFrame(result)

        if df_result.empty:
            print("AVISO: df_result final está VAZIO.")
            return pd.DataFrame(columns=['tag', 'profit', 'volume', 'roi', 'units', 'bets'])

        print(f"--- Fim Debug tag_analysis (Retornando {len(df_result)} linhas) ---\n")
        return df_result.sort_values(by='roi', ascending=False)

    @staticmethod
    def print_tag_report(
        tag_df: pd.DataFrame
    ) -> None:
        """
        Printa os dados para o user ver a análise de Tags
        """
        
        # Verifica se o DataFrame está vazio
        if tag_df.empty:
            print("Nenhuma tag encontrada para exibir no relatório.")
            return
            
        print("\n--- Relatório de Análise por Tag (Ordenado por ROI) ---")
        
        # Define o formato do cabeçalho
        header = f"{'Tag':<20} | {'ROI':>8} | {'Profit':>10} | {'Volume':>12} | {'Bets':>6}"
        print(header)
        print("-" * len(header))
        
        # Itera sobre as linhas do DataFrame para printar cada tag
        for _, row in tag_df.iterrows():
            
            # Formata as strings para um print alinhado
            tag_str = f"{str(row['tag']):<20}"
            roi_str = f"{row['roi']:>8.2%}"  # Formata como porcentagem
            profit_str = f"{row['profit']:>10.2f}"
            volume_str = f"{row['volume']:>12.2f}"
            bets_str = f"{row['bets']:>6}"
            
            # Monta a linha de output
            line = f"{tag_str} | {roi_str} | {profit_str} | {volume_str} | {bets_str}"
            print(line)
            
        print("-" * len(header))
        print("--- Fim do Relatório ---")


    @staticmethod
    def daily_balance(
        df: pd.DataFrame
    ):
        """
        Recebe um dataframe e retorna o PL 
        separado por dia
        """
        df = df.copy()
        df['endDate'] = pd.to_datetime(
            df['endDate'], format='ISO8601', utc=True
            ).dt.tz_localize(None).dt.to_period('D')
        
        all_data = []
        
        
        for date, date_df in df.groupby('endDate'):
            profit, vol, roi = DataAnalyst.calculate_stats(date_df)
            single_date = {
                'date': date,
                'profit': profit,
                'volume': vol,
                'roi': roi
            }
            all_data.append(single_date)
        
        return pd.DataFrame(all_data)


    @staticmethod
    def monthly_balance(
        df: pd.DataFrame
        ):
        """
        Recebe um dataframe e retorna o PL 
        separado por mês
        """
        df = df.copy()       
        df['month'] = pd.to_datetime(
            df['endDate'], format='ISO8601', utc=True
            ).dt.tz_localize(None).dt.to_period('M')
        
        all_data = []
        
        for date, date_df in df.groupby('month'):
            profit, vol, roi = DataAnalyst.calculate_stats(date_df)
            single_date = {
                'date': date,
                'profit': profit,
                'volume': vol,
                'roi': roi
            }
            all_data.append(single_date)
        
        return pd.DataFrame(all_data)
