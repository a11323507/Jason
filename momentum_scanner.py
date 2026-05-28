import pandas as pd
import yfinance as yf
import numpy as np
import time
from tabulate import tabulate
from macro_regime import get_macro_regime
from sector_logic import get_top_sectors
from discord_utils import send_to_discord
from chip_utils import get_latest_chip_data
from FinMind.data import DataLoader
from datetime import datetime, timedelta

def scan_momentum():
    exposure, macro_report = get_macro_regime()
    if exposure <= 0:
        print("Market regime is too dangerous (Exposure 0%). Skipping scan.")
        send_to_discord("Momentum 掃描報告 (未執行)", "大盤風險過高，今日不建議操作。", macro_report)
        return pd.DataFrame()

    top_sectors = get_top_sectors()
    
    try:
        stock_list = pd.read_csv("stock_list.csv")
    except:
        return pd.DataFrame()

    # Filter by top sectors and 4-digit IDs
    targets = stock_list[(stock_list['industry_category'].isin(top_sectors)) & 
                        (stock_list['stock_id'].str.len() == 4)]
    
    # Limitation: to keep it fast, we'll take top 100 stocks from these sectors if there are too many
    if len(targets) > 100:
        targets = targets.head(100)

    all_ids = []
    for _, r in targets.iterrows():
        suffix = ".TW" if r['type'] == 'twse' else ".TWO"
        all_ids.append(f"{r['stock_id']}{suffix}")

    print(f"🚀 Scanning {len(all_ids)} stocks in top sectors: {top_sectors}")
    
    # Download data for all target stocks
    # Need 80 days for 60MA and ATR
    data = yf.download(all_ids, period="100d", progress=False, group_by='ticker')
    
    results = []
    for sid in all_ids:
        try:
            if len(all_ids) == 1:
                t_data = data.dropna()
            else:
                t_data = data[sid].dropna()
                
            if len(t_data) < 65: continue
            
            close = t_data['Close']
            curr_p = close.iloc[-1]
            prev_p = close.iloc[-2]
            open_p = t_data['Open'].iloc[-1]
            
            # Momentum 20d
            mom_20d = curr_p / close.iloc[-21]
            
            # Trend 60MA
            ma60 = close.rolling(60).mean().iloc[-1]
            trend60_val = curr_p / ma60
            
            # Trend 20MA
            ma20 = close.rolling(20).mean().iloc[-1]
            trend20_val = curr_p / ma20
            
            # ATR 20d
            high = t_data['High']
            low = t_data['Low']
            tr = pd.concat([high - low, 
                            (high - close.shift(1)).abs(), 
                            (low - close.shift(1)).abs()], axis=1).max(axis=1)
            atr20 = tr.rolling(20).mean().iloc[-1]
            
            # Gap Filter: Gap < 1.5 * ATR20
            gap = abs(open_p - prev_p)
            if gap > 1.5 * atr20:
                continue
                
            # Filter: price > MA60
            if curr_p <= ma60:
                continue

            results.append({
                "代號": sid,
                "現價": curr_p,
                "20d動能": mom_20d,
                "20MA趨勢": trend20_val,
                "60MA趨勢": trend60_val,
                "ATR": atr20,
                "跳空": gap,
                "停利價": round(curr_p + (4.0 * atr20), 2),
                "停損價": round(curr_p - (2.0 * atr20), 2)
            })
        except:
            continue

    if not results:
        print("No stocks passed the technical filters.")
        return pd.DataFrame()

    df_results = pd.DataFrame(results)
    
    # Cross-sectional Ranking (Percentile)
    df_results['動能排名'] = df_results['20d動能'].rank(pct=True)
    df_results['趨勢排名'] = df_results['60MA趨勢'].rank(pct=True)
    
    # v8.5 Score = MomRank * 3 + TrendRank * 1
    df_results['綜合分數'] = df_results['動能排名'] * 3 + df_results['趨勢排名'] * 1
    
    # Sort and pick Top-7 (as per tw_stocker)
    # We also apply Exposure limit here. E.g. if exposure is 0.5, we might only pick top 4.
    num_to_pick = int(7 * exposure)
    if num_to_pick < 1 and exposure > 0: num_to_pick = 1
    
    final_picks = df_results.sort_values(by="綜合分數", ascending=False).head(num_to_pick)
    
    # --- Discord Optimization ---
    # Create a simplified version for Discord to prevent line wrapping
    discord_picks = final_picks[["代號", "現價", "20MA趨勢", "停利價", "停損價", "綜合分數"]].copy()
    discord_picks["20MA趨勢"] = discord_picks["20MA趨勢"].round(3)
    discord_picks["綜合分數"] = discord_picks["綜合分數"].round(2)
    
    table_str = tabulate(discord_picks, headers='keys', tablefmt='psql', showindex=False)
    send_to_discord("Momentum 策略掃描結果", table_str, macro_report)
    # ---------------------------
    
    return final_picks

def analyze_specific_stock(ticker):
    """
    Analyzes a specific stock ticker using the momentum strategy logic.
    """
    print(f"🧐 正在分析指定標的: {ticker}...")
    
    industry = "未知"
    # Ensure ticker format and get industry
    try:
        df_list = pd.read_csv("stock_list.csv")
        # Clean ticker for lookup
        clean_id = ticker.split('.')[0]
        row_info = df_list[df_list['stock_id'] == clean_id].iloc[0]
        industry = row_info['industry_category']
        
        if not (ticker.endswith(".TW") or ticker.endswith(".TWO")):
            suffix = ".TW" if row_info['type'] == 'twse' else ".TWO"
            ticker = f"{clean_id}{suffix}"
    except:
        if not (ticker.endswith(".TW") or ticker.endswith(".TWO")):
            return f"❌ 找不到代號 {ticker}，請確認格式 (例如 2330 或 2330.TW)"

    try:
        # Calculate Industry Momentum as well
        industry_mom_str = "計算中..."
        if industry != "未知":
            industry_proxies = df_list[df_list['industry_category'] == industry].head(3)
            proxy_ids = []
            for _, p_row in industry_proxies.iterrows():
                p_suffix = ".TW" if p_row['type'] == 'twse' else ".TWO"
                proxy_ids.append(f"{p_row['stock_id']}{p_suffix}")
            
            p_data = yf.download(proxy_ids, period="30d", progress=False, group_by='ticker')
            if isinstance(p_data.columns, pd.MultiIndex):
                p_moms = []
                for pid in proxy_ids:
                    try:
                        p_close = p_data[pid]['Close'].dropna()
                        if len(p_close) >= 21:
                            r10 = (p_close.iloc[-1] - p_close.iloc[-11]) / p_close.iloc[-11]
                            r15 = (p_close.iloc[-1] - p_close.iloc[-16]) / p_close.iloc[-16]
                            r20 = (p_close.iloc[-1] - p_close.iloc[-21]) / p_close.iloc[-21]
                            p_moms.append((r10 + r15 + r20) / 3)
                    except: continue
                if p_moms:
                    industry_mom_str = f"{np.mean(p_moms)*100:+.2f}%"

        data = yf.download(ticker, period="100d", progress=False)
        if data.empty or len(data) < 65:
            return f"❌ {ticker} 資料不足或代號錯誤。"

        # Flatten DataFrame if it has multi-index columns (common in new yfinance)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
            
        close = data['Close'].squeeze()
        high = data['High'].squeeze()
        low = data['Low'].squeeze()
        open_col = data['Open'].squeeze()

        curr_p = float(close.iloc[-1])
        prev_p = float(close.iloc[-2])
        open_p = float(open_col.iloc[-1])
        
        # Calculate Indicators
        mom_20d = float(curr_p / close.iloc[-21])
        ma60 = float(close.rolling(60).mean().iloc[-1])
        ma20 = float(close.rolling(20).mean().iloc[-1])
        trend60 = float(curr_p / ma60)
        trend20 = float(curr_p / ma20)
        
        tr = pd.concat([high - low, 
                        (high - close.shift(1)).abs(), 
                        (low - close.shift(1)).abs()], axis=1).max(axis=1)
        atr20 = float(tr.rolling(20).mean().iloc[-1])
        
        tp = float(curr_p + (4.0 * atr20))
        sl = float(curr_p - (2.0 * atr20))
        
        # Chip Data Integration
        chip_info = ""
        chip_data_3d = get_latest_chip_data(ticker, days=3)
        if chip_data_3d and "daily_history" in chip_data_3d:
            history = chip_data_3d["daily_history"]
            t_net = history[0]['foreign'] + history[0]['trust'] + history[0]['dealer']
            
            # Get volume for participation ratio
            try:
                # data['Volume'] is a series
                vol_today = float(data['Volume'].iloc[-1])
                part_ratio = (t_net / vol_today) * 100 if vol_today > 0 else 0
            except:
                part_ratio = 0
            
            # Flow Momentum (Today vs Yesterday)
            momentum_str = "持平"
            if len(history) > 1:
                y_net = history[1]['foreign'] + history[1]['trust'] + history[1]['dealer']
                diff = t_net - y_net
                if diff > 0:
                    momentum_str = "📈 買盤轉強" if t_net > 0 else "📉 賣壓減緩"
                else:
                    momentum_str = "📉 買盤縮減" if t_net > 0 else "📈 賣壓增加"

            chip_info = f"--- 法人籌碼動向 ({history[0]['date']}) ---\n"
            chip_info += f"單日合計: {t_net:>12,d} 股\n"
            chip_info += f"成交佔比: {part_ratio:>11.2f}%\n"
            chip_info += f"力道變動: {momentum_str}\n"
            
            # 3-day cumulative
            total_3d = chip_data_3d['foreign'] + chip_data_3d['trust'] + chip_data_3d['dealer']
            chip_info += f"\n--- 三日累計 ---\n"
            chip_info += f"外資: {chip_data_3d['foreign']:>12,d}\n"
            chip_info += f"投信: {chip_data_3d['trust']:>12,d}\n"
            chip_info += f"累計合計: {total_3d:>12,d}\n"

        # Build Report String
        report = f"🔍 **{ticker} 策略分析報告**\n"
        report += f"```\n"
        report += f"所屬產業: {industry}\n"
        report += f"產業動量: {industry_mom_str}\n"
        report += f"-------------------\n"
        report += f"現價: {curr_p:.2f}\n"
        report += f"20d動能: {((mom_20d-1)*100):+.2f}%\n"
        report += f"20MA趨勢: {trend20:.3f} ({'多頭' if trend20 > 1 else '空頭'})\n"
        report += f"60MA趨勢: {trend60:.3f} ({'站穩' if trend60 > 1 else '跌破'})\n"
        report += f"ATR (20d): {atr20:.2f}\n"
        
        # Revenue YOY Integration
        rev_info = "無資料"
        warnings = []
        try:
            dl = DataLoader()
            start_d = (datetime.now() - timedelta(days=500)).strftime("%Y-%m-01")
            rev_df = dl.taiwan_stock_month_revenue(stock_id=clean_id, start_date=start_d)
            if not rev_df.empty and len(rev_df) >= 15:
                rev_df['yoy'] = rev_df['revenue'].pct_change(12) * 100
                recent_3_yoy = rev_df['yoy'].tail(3).tolist()
                months = rev_df['date'].str[:7].tail(3).tolist()
                
                rev_info = ""
                all_above_20 = True
                for m, y in zip(months, recent_3_yoy):
                    rev_info += f"{m}: {y:+.1f}%, "
                    if y <= 20:
                        all_above_20 = False
                rev_info = rev_info.strip(", ")
                
                if not all_above_20:
                    warnings.append("⚠️ 近3個月營收 YOY 未達全面 > 20% 門檻。")
            elif len(rev_df) > 0:
                rev_info = "資料筆數不足以計算 YOY"
        except Exception as e:
            rev_info = "讀取失敗"
            
        report += f"近3月營收YOY: {rev_info}\n"
        
        if chip_info:
            report += f"-------------------\n"
            report += chip_info
        report += f"-------------------\n"
        report += f"建議停利價: {tp:.2f}\n"
        report += f"建議停損價: {sl:.2f}\n"
        report += f"```\n"
        
        # Condition checks
        if curr_p <= ma60: warnings.append("⚠️ 股價低於季線，不符強勢股準則。")
        gap = abs(open_p - prev_p)
        if gap > 1.5 * atr20: warnings.append("⚠️ 今日跳空過大，進場風險高。")
        
        if warnings:
            report += "\n".join(warnings)
        else:
            report += "✅ 符合 v8.5 技術面進場初篩條件。"
            
        return report

    except Exception as e:
        return f"❌ 分析過程中發生錯誤: {e}"

if __name__ == "__main__":
    picks = scan_momentum()
    print("\n" + "="*80)
    print("🏆 【 Momentum Strategy Picks (v8.5 Logic) 】")
    if not picks.empty:
        print(tabulate(picks, headers='keys', tablefmt='psql', showindex=False))
        picks.to_csv("momentum_picks.csv", index=False)
    else:
        print("No recommendations for today.")
    print("="*80)
