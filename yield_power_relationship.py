import streamlit as st
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px

st.set_page_config(layout="wide")

st.image("logo.PNG", width=800)
st.markdown("## 📊 產量用電 vs 產量 異常分析系統")
# st.title("📊 產量用電 vs 產量 異常分析系統")

uploaded_file = st.file_uploader("請上傳產量用電 Excel 檔案（格式如：產量、用電指數）", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    selected_sheet = st.selectbox("📄 請選擇工作表", sheet_names)

    df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=None)

    # 資料解析：改為使用「產量」「實際用電量 (kWh)」
    records = []
    for col in df.columns[1:]:
        try:
            month = df.iloc[0, col]
            產量 = pd.to_numeric(df.iloc[1, col], errors='coerce')
            power_index = pd.to_numeric(df.iloc[2, col], errors='coerce')
            records.append({
                'month': month,
                '產量': 產量,
                'power_index': power_index
            })
        except:
            continue

    data = pd.DataFrame(records)
    data['實際用電量 (kWh)'] = data['power_index'].diff() * 8000
    data = data.dropna(subset=['產量', '實際用電量 (kWh)'])

    # 線性回歸
    X = sm.add_constant(data['產量'])
    y = data['實際用電量 (kWh)']
    model = sm.OLS(y, X).fit()
    intercept = model.params['const']
    slope = model.params['產量']
    r2 = model.rsquared

    data['預測用電'] = intercept + slope * data['產量']
    data['誤差'] = data['實際用電量 (kWh)'] - data['預測用電']

    # 顯示預測公式
    st.subheader("📌 預測模型")
    st.markdown(f"預測用電量 (kWh) = 基礎電量 + 斜率 × 產量  ")
    st.code(f"預測用電量 (kWh) = {intercept:,.0f} + {slope:,.2f} × 產量", language="markdown")
    st.markdown(f"模型解釋度 R² = **{r2:.3f}**")

    # MAD 異常偵測
    st.markdown("使用 **中位數絕對偏差 (MAD)** 判斷異常")
    mad_threshold = st.slider("MAD 閾值倍數", 1.0, 5.0, 3.0, 0.5)
    st.caption("建議值為 3.0。下方即時顯示異常筆數。")

    median_resid = data['誤差'].median()
    mad = (data['誤差'] - median_resid).abs().median()
    data['異常'] = (data['誤差'] - median_resid).abs() > mad_threshold * mad

    # 加上異常方向與節能欄位
    data['異常方向'] = data.apply(
        lambda row: '用電過高' if row['異常'] and row['誤差'] > 0
        else ('用電過低' if row['異常'] and row['誤差'] < 0 else '正常'),
        axis=1
    )

    data['節能成功'] = data['誤差'] < 0
    data['節能幅度 (%)'] = (data['誤差'] / data['預測用電']) * 100

    # 統計提示
    st.markdown(f"🔎 目前偵測到異常筆數：**{data['異常'].sum()}** 筆，🌿 節能成功月份：**{data['節能成功'].sum()}** 筆")

    # 顯示資料
    cols_to_show = ['month', '產量', '實際用電量 (kWh)', '預測用電', '誤差', '節能成功', '節能幅度 (%)', '異常方向', '異常']

    st.subheader("📋 資料預覽（含異常與節能狀況）")
    st.dataframe(data[cols_to_show])

    # 異常圖表
    st.subheader("📈 互動圖：產量 vs 用電量（紅色為異常）")
    fig = px.scatter(
        data,
        x='產量',
        y='實際用電量 (kWh)',
        color='異常',
        color_discrete_map={True: 'red', False: 'blue'},
        hover_data={
            'month': True,
            '產量': ':.2f',
            '實際用電量 (kWh)': ':.0f',
            '預測用電': ':.0f',
            '誤差': ':.0f',
            '節能幅度 (%)': ':.2f',
            '異常方向': True
        },
        labels={'產量': '澱粉原料噸數', '實際用電量 (kWh)': '實際用電量 (kWh)'},
        title='澱粉用電量 vs 產量（MAD 異常分析）'
    )

    fig.add_scatter(
        x=data['產量'],
        y=data['預測用電'],
        mode='lines',
        name='預測線',
        line=dict(color='orange')
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("請上傳格式為『前3列資料：月份、產量、用電指數』的 Excel 檔案。")
