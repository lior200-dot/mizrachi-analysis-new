import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# 1. הגדרות בסיס ותצוגה מימין לשמאל (RTL)
st.set_page_config(page_title="הדאשבורד הפיננסי שלי", layout="wide", page_icon="💰")
st.markdown("""
    <style>
        .block-container { direction: rtl; text-align: right; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        p, div, h1, h2, h3, h4, h5, h6, table { text-align: right; }
        .stMetric { direction: rtl; }
        th { text-align: right !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 הדאשבורד הפיננסי שלי")

# 2. פונקציות עזר 
def clean_amount(val):
    if pd.isna(val): return 0.0
    val_str = str(val).replace(',', '').strip()
    try: return float(val_str)
    except: return 0.0

def is_date(val):
    val_str = str(val).strip()
    return bool(re.search(r'\d{2,4}[-/]\d{2}[-/]\d{2,4}', val_str)) or (isinstance(val, (int, float)) and 30000 < val < 100000)

# פונקציית סיווג היברידית (מילון אישי + אוטומטי)
def get_category(desc, mapping_dict):
    desc_clean = str(desc).strip()
    
    if desc_clean in mapping_dict:
        return mapping_dict[desc_clean], False 
    
    desc_lower = desc_clean.lower()
    auto_cat = "כללי / אחר"
    if any(w in desc_lower for w in ["שופרסל", "פרשמרקט", "רמי לוי", "מגה", "יינות ביתן", "ויקטורי", "אושר עד", "מחסני השוק", "חצי חינם", "וולט", "wolt", "תן ביס", "משלוחה", "מכולת", "מסעד", "קפה", "אוכל"]):
        auto_cat = "מזון ומסעדות"
    elif any(w in desc_lower for w in ["דלק", "פז", "סונול", "דור אלון", "מיקה", "פנגו", "pango", "רב קו", "רכבת", "gett", "yango", "כביש 6", "חניה", "רכב", "תחבורה"]):
        auto_cat = "תחבורה ורכב"
    elif any(w in desc_lower for w in ["הראל", "מנורה", "כללית", "מכבי", "הפניקס", "מגדל", "מאוחדת", "ביטוח", "סופר פארם", "be", "פארם"]):
        auto_cat = "בריאות וביטוח"
    elif any(w in desc_lower for w in ["פרטנר", "סלקום", "הוט", "פלאפון", "יס", "partner", "cellcom", "netflix", "spotify", "תקשורת"]):
        auto_cat = "תקשורת ופנאי"
    elif any(w in desc_lower for w in ["חשמל", "מים", "ארנונה", "גז", "תאגיד", "ועד בית"]):
        auto_cat = "חשבונות בית"
    
    return auto_cat, True

# 3. מנוע קריאת קבצי בנק
def process_osh(file):
    try: df = pd.read_csv(file, header=None, encoding='utf-8')
    except: 
        file.seek(0)
        df = pd.read_csv(file, header=None, encoding='windows-1255') if file.name.endswith('.csv') else pd.read_excel(file, header=None)
    
    start_idx = next((i for i in range(min(30, len(df))) if is_date(df.iloc[i, 0])), None)
    if start_idx is None: return pd.DataFrame()
    
    df = df.iloc[start_idx:].reset_index(drop=True)
    parsed = pd.DataFrame()
    parsed['Date'] = pd.to_datetime(df[0], errors='coerce', dayfirst=True)
    parsed['Desc'] = df[2].astype(str).str.strip()
    parsed['Income'] = df[3].apply(clean_amount)
    parsed['Expense'] = df[4].apply(clean_amount)
    if df.shape[1] > 5:
        parsed['Balance'] = df[5].apply(clean_amount)
    else:
        parsed['Balance'] = 0.0
    return parsed.dropna(subset=['Date'])

def process_ash(file):
    try: df = pd.read_csv(file, header=None, encoding='utf-8')
    except: 
        file.seek(0)
        df = pd.read_csv(file, header=None, encoding='windows-1255') if file.name.endswith('.csv') else pd.read_excel(file, header=None)
    
    start_idx = next((i for i in range(min(20, len(df))) if is_date(df.iloc[i, 0]) or is_date(df.iloc[i, 1])), None)
    if start_idx is None: return pd.DataFrame()
    
    df = df.iloc[start_idx:].reset_index(drop=True)
    parsed = pd.DataFrame()
    date_col = df[1].copy()
    date_col[date_col.isna()] = df[0][date_col.isna()]
    parsed['Date'] = pd.to_datetime(date_col, errors='coerce', dayfirst=True)
    parsed['Desc'] = df[2].astype(str).str.strip()
    exp_col = 4 if df.shape[1] >= 5 else df.shape[1] - 1
    parsed['Expense'] = df[exp_col].apply(clean_amount)
    return parsed.dropna(subset=['Date'])

# 4. ממשק המשתמש - העלאת קבצים
st.sidebar.header("העלאת נתונים 📂")
st.sidebar.markdown("**חובה:**")
osh_file = st.sidebar.file_uploader("בחר קובץ תנועות עו\"ש", type=['csv', 'xlsx', 'xls'])
ash_files = st.sidebar.file_uploader("בחר קבצי כרטיס אשראי", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)

st.sidebar.markdown("**רשות (מומלץ):**")
tagging_file = st.sidebar.file_uploader("בחר קובץ תיוג הוצאות (אקסל)", type=['xlsx', 'xls', 'csv'])

if osh_file:
    with st.spinner('מעבד נתונים...'):
        
        category_map = {}
        if tagging_file is not None:
            try:
                if tagging_file.name.endswith('.csv'): tags_df = pd.read_csv(tagging_file)
                else: tags_df = pd.read_excel(tagging_file)
                
                if "הוצאה" in tags_df.columns and "קטגוריה" in tags_df.columns:
                    tags_df = tags_df.dropna(subset=['הוצאה', 'קטגוריה'])
                    category_map = dict(zip(tags_df['הוצאה'].astype(str).str.strip(), tags_df['קטגוריה'].astype(str).str.strip()))
                    st.sidebar.success(f"נטענו {len(category_map)} תיוגים אישיים בהצלחה!")
                else: st.sidebar.warning("קובץ התיוג חייב להכיל עמודות בשם 'הוצאה' ו-'קטגוריה'.")
            except Exception as e: st.sidebar.error(f"שגיאה בקריאת קובץ התיוג: {e}")

        osh_df = process_osh(osh_file)
        ash_dfs = [process_ash(f) for f in ash_files] if ash_files else []
        ash_df = pd.concat(ash_dfs, ignore_index=True) if ash_dfs else pd.DataFrame(columns=['Date', 'Desc', 'Expense'])
        
        cc_keywords = ["ישראכרט", "ויזה", "לאומי קארד", "מקס", "כאל", "מסטרקרד", "אמריקן אקספרס"]
        is_cc = osh_df['Desc'].str.contains('|'.join(cc_keywords), na=False)
        osh_filtered = osh_df[~is_cc]
        
        all_expenses = pd.concat([
            osh_filtered[osh_filtered['Expense'] > 0][['Date', 'Desc', 'Expense']], 
            ash_df[ash_df['Expense'] > 0]
        ], ignore_index=True)
        
        tagging_results = all_expenses['Desc'].apply(lambda x: get_category(x, category_map))
        all_expenses['Category'] = [res[0] for res in tagging_results]
        all_expenses['Auto_Classified'] = [res[1] for res in tagging_results]
        all_expenses['Month'] = all_expenses['Date'].dt.to_period('M').astype(str)
        
        all_incomes = osh_df[osh_df['Income'] > 0][['Date', 'Desc', 'Income']].copy()
        all_incomes['Month'] = all_incomes['Date'].dt.to_period('M').astype(str)
        
        # --- תמונת מצב כללית ---
        st.markdown("---")
        st.header("🌍 מבט על: מגמות היסטוריות")
        
        monthly_summary = pd.DataFrame({
            'Month': pd.concat([all_incomes['Month'], all_expenses['Month']]).unique()
        }).sort_values('Month')
        monthly_summary['Income'] = monthly_summary['Month'].map(all_incomes.groupby('Month')['Income'].sum()).fillna(0)
        monthly_summary['Expense'] = monthly_summary['Month'].map(all_expenses.groupby('Month')['Expense'].sum()).fillna(0)
        
        col1, col2 = st.columns(2)
        
        # 1. תזרים מזומנים
        fig_cf = go.Figure()
        fig_cf.add_trace(go.Bar(x=monthly_summary['Month'], y=monthly_summary['Income'], name='הכנסות', marker_color='green'))
        fig_cf.add_trace(go.Bar(x=monthly_summary['Month'], y=monthly_summary['Expense'], name='הוצאות', marker_color='red'))
        fig_cf.update_layout(barmode='group', title="תזרים מזומנים חודשי (הכנסות מול הוצאות)", hovermode="x unified")
        col1.plotly_chart(fig_cf, use_container_width=True)
        
        # 2. מגמת יתרה (Balance Trend) - אם קיים
        osh_bal = osh_df[osh_df['Balance'] != 0].sort_values('Date')
        if not osh_bal.empty:
            fig_bal = px.line(osh_bal, x='Date', y='Balance', title='מגמת יתרת העו"ש לאורך זמן', markers=True)
            fig_bal.update_traces(line_color='blue')
            col2.plotly_chart(fig_bal, use_container_width=True)
        else:
            cat_sum = all_expenses.groupby('Category')['Expense'].sum().reset_index()
            fig_pie_all = px.pie(cat_sum, values='Expense', names='Category', title='התפלגות הוצאות (כל התקופה)')
            col2.plotly_chart(fig_pie_all, use_container_width=True)

        # --- חיתוך חודשי ---
        st.markdown("---")
        st.header("🔎 צלילה לעומק: ניתוח חודשי ממוקד")
        
        selected_month = st.selectbox("📅 בחר חודש לניתוח:", reversed(monthly_summary['Month'].tolist()))
        
        exp_m = all_expenses[all_expenses['Month'] == selected_month].copy()
        inc_m = all_incomes[all_incomes['Month'] == selected_month].copy()
        
        # מטריקות
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("סה\"כ הכנסות", f"{inc_m['Income'].sum():,.0f} ₪")
        m_col2.metric("סה\"כ הוצאות", f"{exp_m['Expense'].sum():,.0f} ₪")
        m_col3.metric("נטו (חיסכון)", f"{(inc_m['Income'].sum() - exp_m['Expense'].sum()):,.0f} ₪")
        
        # --- ניתוח הכנסות ---
        st.markdown("#### 💵 ניתוח הכנסות")
        inc_col1, inc_col2 = st.columns([1, 1.5])
        
        if not inc_m.empty:
            inc_sum_m = inc_m.groupby('Desc')['Income'].sum().reset_index()
            fig_inc_pie = px.pie(inc_sum_m, values='Income', names='Desc', title='מקורות הכנסה', hole=0.3)
            fig_inc_pie.update_traces(textposition='inside', textinfo='percent+label')
            inc_col1.plotly_chart(fig_inc_pie, use_container_width=True)
            
            inc_pivot = inc_sum_m.sort_values('Income', ascending=False)
            inc_pivot.columns = ['מקור הכנסה', 'סה"כ (₪)']
            inc_col2.markdown(f"**פירוט הכנסות - {selected_month}**")
            inc_col2.dataframe(inc_pivot.style.format({'סה"כ (₪)': "{:,.2f}"}), use_container_width=True, hide_index=True)
        else:
            st.info("אין הכנסות לחודש זה.")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- ניתוח הוצאות ---
        st.markdown("#### 💳 ניתוח הוצאות")
        exp_col1, exp_col2 = st.columns([1, 1.5])
        
        if not exp_m.empty:
            cat_sum_m = exp_m.groupby('Category')['Expense'].sum().reset_index()
            fig_exp_pie = px.pie(cat_sum_m, values='Expense', names='Category', title='פילוח הוצאות לפי קטגוריות', hole=0.3)
            fig_exp_pie.update_traces(textposition='inside', textinfo='percent+label')
            exp_col1.plotly_chart(fig_exp_pie, use_container_width=True)
            
            # פיבוט הוצאות (עם סימון תיוג אוטומטי)
            exp_m['Display_Desc'] = exp_m.apply(
                lambda row: f"{row['Desc']} ⚠️ (סיווג אוטומטי)" if row['Auto_Classified'] else row['Desc'], axis=1
            )
            pivot_m = exp_m.groupby(['Category', 'Display_Desc'])['Expense'].sum().reset_index()
            pivot_m = pivot_m.sort_values(['Category', 'Expense'], ascending=[True, False])
            pivot_m.columns = ['קטגוריה', 'בית עסק', 'סה"כ (₪)']
            
            exp_col2.markdown(f"**פירוט הוצאות (Pivot) - {selected_month}**")
            exp_col2.dataframe(pivot_m.style.format({'סה"כ (₪)': "{:,.2f}"}), use_container_width=True, height=350, hide_index=True)
            
            if exp_m['Auto_Classified'].any():
                st.info("💡 **שים לב:** הוצאות המסומנות ב-⚠️ תויגו על ידי המערכת מכיוון שלא הופיעו בקובץ התיוג שלך. תוכל להוסיף אותן לאקסל שלך לפעם הבאה.")
            
            # --- טופ 10 וקבועות/משתנות ---
            st.markdown("<br>", unsafe_allow_html=True)
            top_col1, top_col2 = st.columns([1.5, 1])
            
            # טופ 10
            top_10 = exp_m.groupby('Desc')['Expense'].sum().reset_index().sort_values('Expense', ascending=False).head(10)
            fig_top10 = px.bar(top_10, x='Desc', y='Expense', title='10 בתי העסק היקרים ביותר בחודש זה', text_auto='.0f')
            fig_top10.update_traces(marker_color='indianred', textposition='outside')
            fig_top10.update_layout(xaxis_title="", yaxis_title="סכום (₪)")
            top_col1.plotly_chart(fig_top10, use_container_width=True)
            
            # קבועות מול משתנות
            fixed_cats = ["בריאות וביטוח", "תקשורת ופנאי", "חשבונות בית"]
            exp_m['Type'] = exp_m['Category'].apply(lambda c: 'הוצאות קבועות (קשיחות)' if c in fixed_cats else 'הוצאות משתנות (בשליטתך)')
            fv_sum = exp_m.groupby('Type')['Expense'].sum().reset_index()
            fig_fv = px.pie(fv_sum, values='Expense', names='Type', title='שליטה תקציבית: קבועות לעומת משתנות', color='Type', 
                            color_discrete_map={'הוצאות קבועות (קשיחות)':'#1f77b4', 'הוצאות משתנות (בשליטתך)':'#ff7f0e'})
            top_col2.plotly_chart(fig_fv, use_container_width=True)

        else:
            st.info("אין הוצאות לחודש זה.")

else:
    st.info("👈 כדי להתחיל, העלה את קבצי הבנק שלך בסרגל הצד (ולאחר מכן את קובץ התיוג האישי שלך אם תרצה).")
