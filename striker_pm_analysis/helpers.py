import ast
import pandas as pd

def safe_divide(num, den, fallback=None):
    try: return num/den
    except: return fallback


def to_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        try:
            v = ast.literal_eval(x)
            return v if isinstance(v, list) else []
        except:
            return []
    return []


def get_exploded_df(
        df: pd.DataFrame,
        exclude_tags: list = []
    ) -> pd.DataFrame:
    """
    Cria DataFrame exploded com tags para análise detalhada.
    Usa a lógica de 'tag_analysis' para duplicar a funcionalidade.
    """
    df = df.copy()
    removed_tags = ['Games', 'Sports'] + exclude_tags
    
    tmp = df.copy()

    if 'tags' not in tmp.columns:
        tmp['tags'] = "[]"

    tmp['__tags_list'] = tmp['tags'].apply(to_list)
    exploded = tmp.explode('__tags_list', ignore_index=True)
    exploded = exploded.rename(columns={'__tags_list': 'tag'})
    exploded = exploded[exploded['tag'].notna()]
    exploded = exploded[~exploded['tag'].isin(removed_tags)]
    
    # Usar apenas realizedPnl para evitar duplicação
    if 'realizedPnl' not in exploded.columns:
        exploded['realizedPnl'] = 0
        
    exploded['total_profit'] = exploded['realizedPnl'].fillna(0)
    exploded['volume'] = exploded['totalBought'] * exploded['avgPrice']
    exploded['staked'] = exploded['totalBought'] * exploded['avgPrice']
    

    exploded['roi'] = safe_divide(exploded['total_profit'], exploded['volume'])

    
    return exploded
