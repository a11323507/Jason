import pandas as pd
import yfinance as yf
import numpy as np
import time

def get_all_sector_momentum():
    """
    Calculates the momentum for all industries based on 10, 15, and 20-day returns of proxies.
    Returns a DataFrame sorted by momentum.
    """
    print("Calculating All Sector Momentum...")
    try:
        df = pd.read_csv("stock_list.csv")
    except:
        print("Error: stock_list.csv not found.")
        return pd.DataFrame()

    # Exclude non-stock categories
    exclude = ['ETF', '上櫃指數股票型基金(ETF)', '上櫃ETF', '存託憑證', '其他', '受益證券']
    df = df[~df['industry_category'].isin(exclude)]
    df = df[df['stock_id'].str.len() == 4] # Only 4-digit stock IDs

    # Group by industry and pick top 3 stocks as proxies
    sectors = df.groupby('industry_category').head(3)
    
    unique_sectors = sectors['industry_category'].unique()
    sector_results = []

    # Batch download proxies
    proxies = []
    for idx, row in sectors.iterrows():
        suffix = ".TW" if row['type'] == 'twse' else ".TWO"
        proxies.append(f"{row['stock_id']}{suffix}")

    print(f"Downloading data for {len(proxies)} sector proxies...")
    data = yf.download(proxies, period="30d", progress=False, group_by='ticker')
    
    for industry in unique_sectors:
        industry_stocks = sectors[sectors['industry_category'] == industry]
        industry_returns = []
        
        for _, row in industry_stocks.iterrows():
            suffix = ".TW" if row['type'] == 'twse' else ".TWO"
            sid = f"{row['stock_id']}{suffix}"
            
            try:
                if len(proxies) == 1:
                    hist = data.dropna()
                else:
                    hist = data[sid].dropna()
                
                if len(hist) < 21: continue
                
                # Calculate 10, 15, 20d returns
                r10 = (hist['Close'].iloc[-1] - hist['Close'].iloc[-11]) / hist['Close'].iloc[-11]
                r15 = (hist['Close'].iloc[-1] - hist['Close'].iloc[-16]) / hist['Close'].iloc[-16]
                r20 = (hist['Close'].iloc[-1] - hist['Close'].iloc[-21]) / hist['Close'].iloc[-21]
                
                # Weighted average momentum
                avg_mom = (r10 + r15 + r20) / 3
                industry_returns.append(avg_mom)
            except:
                continue
        
        if industry_returns:
            sector_results.append({
                "Sector": industry,
                "Momentum": np.mean(industry_returns)
            })

    # Rank sectors
    sector_df = pd.DataFrame(sector_results).sort_values(by="Momentum", ascending=False)
    return sector_df

def get_top_sectors(num_sectors=3):
    """
    Calculates the strongest industries based on 10, 15, and 20-day momentum.
    """
    sector_df = get_all_sector_momentum()
    if sector_df.empty:
        return []

    # Filter: Momentum must be > -0.03 (as per tw_stocker v9.0)
    top_sectors = sector_df[sector_df['Momentum'] > -0.03].head(num_sectors)
    
    print("\n--- Sector Rotation Report ---")
    if not top_sectors.empty:
        print(top_sectors)
    else:
        print("No strong sectors found (> -3% momentum).")
    print("------------------------------")
    
    return top_sectors['Sector'].tolist()

def get_sector_top_volume(sector_name, limit=5):
    """
    Returns the top N stocks by volume for a given industry.
    """
    print(f"Fetching top volume stocks for sector: {sector_name}")
    try:
        df = pd.read_csv("stock_list.csv")
    except:
        return pd.DataFrame()

    # Filter by sector
    targets = df[(df['industry_category'] == sector_name) & (df['stock_id'].str.len() == 4)]
    if targets.empty:
        return pd.DataFrame()

    all_ids = []
    for _, r in targets.iterrows():
        suffix = ".TW" if r['type'] == 'twse' else ".TWO"
        all_ids.append(f"{r['stock_id']}{suffix}")

    # Download 1-day data for volume comparison
    data = yf.download(all_ids, period="5d", progress=False, group_by='ticker')
    
    results = []
    for sid in all_ids:
        try:
            if len(all_ids) == 1:
                t_data = data.dropna()
            else:
                t_data = data[sid].dropna()
            
            if t_data.empty: continue
            
            latest = t_data.iloc[-1]
            close = float(latest['Close'])
            volume = float(latest['Volume'])
            prev_close = float(t_data.iloc[-2]['Close']) if len(t_data) > 1 else close
            change_pct = (close - prev_close) / prev_close * 100 if prev_close != 0 else 0
            
            results.append({
                "代號": sid,
                "名稱": targets[targets['stock_id'] == sid.split('.')[0]]['stock_name'].values[0],
                "現價": round(close, 2),
                "漲跌幅": round(change_pct, 2),
                "成交量": int(volume)
            })
        except:
            continue

    if not results:
        return pd.DataFrame()

    res_df = pd.DataFrame(results).sort_values(by="成交量", ascending=False).head(limit)
    return res_df

if __name__ == "__main__":
    top = get_top_sectors()
    print(f"Top Sectors: {top}")
