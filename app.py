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
        p, div, h1, h2, h3, h4, h5, h6 { text-align: right; }
        .stMetric { direction: rtl; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 הדאשבורד הפיננסי שלי")

# 2. פונקציות עזר (חסינות כדורים)
def clean_amount(val):
    if pd.isna(val): return 0.0
    val_str = str(val).replace(',', '').strip()
    try: return float(val_str)
    except: return 0.0

def is_date(val):
    val_str = str(val).strip()
    return bool(re.search(r'\d{2,4}[-/]\d{2}[-/]\d{2,4}', val_str)) or (isinstance(val, (int, float)) and 30000 < val < 100000)

def map_category(desc):
    desc = str(desc).lower()
    if any(w in desc for w in ["שופרסל", "פרשמרקט", "רמי לוי", "מגה", "יינות ביתן", "ויקטורי", "אושר עד", "מחסני השוק", "חצי חינם", "וולט", "wolt", "תן ביס", "משלוחה", "מכולת", "מסעד", "קפה", "אוכל"]):
        return "מזון ומסעדות"
    if any(w in desc for w in ["דלק", "פז", "סונול", "דור אלון", "מיקה", "פנגו", "pango", "רב קו", "רכבת", "gett", "yango", "כביש 6", "חניה", "רכב", "תחבורה"]):
        return "תחבורה ורכב"
    if any(w in desc for w in ["הראל", "מנורה", "כללית", "מכבי", "הפניקס", "מגדל", "מאוחדת", "ביטוח", "סופר פארם", "be", "פארם"]):
        return "בריאות וביטוח"
    if any(w in desc for w in ["פרטנר", "סלקום", "הוט", "פלאפון", "יס", "partner", "cellcom", "netflix", "spotify", "תקשורת"]):
        return "תקשורת ופנאי"
    if any(w in desc for w in ["חשמל", "מים", "ארנונה", "גז", "תאגיד", "ועד בית"]):
        return "חשבונות בית"
    return "כללי / אחר"

# 3. מנוע קריאת קבצים
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
    parsed['Desc'] = df[2].astype(str)
    parsed['Income'] = df[3].apply(clean_amount)
    parsed['Expense'] = df[4].apply(clean_amount)
    parsed['Balance'] = df[5].apply(clean_amount) if df.shape[1] > 5 else 0.0
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
    
    parsed['Desc'] = df[2].astype(str)
    exp_col = 4 if df.shape[1] >= 5 else df.shape[1] - 1
    parsed['Expense'] = df[exp_col].apply(clean_amount)
    return parsed.dropna(subset=['Date'])

# 4. ממשק המשתמש - העלאת קבצים
st.sidebar.header("העלאת נתונים 📂")
osh_file = st.sidebar.file_uploader("בחר קובץ תנועות עו\"ש", type=['csv', 'xlsx', 'xls'])
ash_files = st.sidebar.file_uploader("בחר קבצי כרטיס אשראי", type=['csv', 'xlsx', 'xls'], accept_multiple_files=True)

if osh_file:
    with st.spinner('מעבד נתונים...'):
        osh_df = process_osh(osh_file)
        ash_dfs = [process_ash(f) for f in ash_files] if ash_files else []
        ash_df = pd.concat(ash_dfs, ignore_index=True) if ash_dfs else pd.DataFrame(columns=['Date', 'Desc', 'Expense'])
        
        # סינון כפילויות של אשראי בעו"ש
        cc_keywords = ["ישראכרט", "ויזה", "לאומי קארד", "מקס", "כאל", "מסטרקרד", "אמריקן אקספרס"]
        is_cc = osh_df['Desc'].str.contains('|'.join(cc_keywords), na=False)
        osh_filtered = osh_df[~is_cc]
        
        # איחוד נתונים
        all_expenses = pd.concat([
            osh_filtered[osh_filtered['Expense'] > 0][['Date', 'Desc', 'Expense']], 
            ash_df[ash_df['Expense'] > 0]
        ], ignore_index=True)
        all_expenses['Category'] = all_expenses['Desc'].apply(map_category)
        all_expenses['Month'] = all_expenses['Date'].dt.to_period('M').astype(str)
        
        all_incomes = osh_df[osh_df['Income'] > 0][['Date', 'Desc', 'Income']].copy()
        all_incomes['Month'] = all_incomes['Date'].dt.to_period('M').astype(str)
        
        # 5. ציור דאשבורד (תמונת מצב כללית)
        st.markdown("---")
        st.header("מבט על: כללי")
        
        col1, col2 = st.columns(2)
        
        # תזרים מזומנים מרוכז
        monthly_summary = pd.DataFrame({
            'Month': pd.concat([all_incomes['Month'], all_expenses['Month']]).unique()
        }).sort_values('Month')
        monthly_summary['Income'] = monthly_summary['Month'].map(all_incomes.groupby('Month')['Income'].sum()).fillna(0)
        monthly_summary['Expense'] = monthly_summary['Month'].map(all_expenses.groupby('Month')['Expense'].sum()).fillna(0)
        
        fig_cf = go.Figure()
        fig_cf.add_trace(go.Bar(x=monthly_summary['Month'], y=monthly_summary['Income'], name='הכנסות', marker_color='green'))
        fig_cf.add_trace(go.Bar(x=monthly_summary['Month'], y=monthly_summary['Expense'], name='הוצאות', marker_color='red'))
        fig_cf.update_layout(barmode='group', title="תזרים מזומנים לפי חודשים", hovermode="x unified")
        col1.plotly_chart(fig_cf, use_container_width=True)
        
        # התפלגות קטגוריות מצטברת
        cat_sum = all_expenses.groupby('Category')['Expense'].sum().reset_index()
        fig_pie = px.pie(cat_sum, values='Expense', names='Category', title='לאן הלך הכסף? (כל התקופה)')
        col2.plotly_chart(fig_pie, use_container_width=True)
        
        # 6. דאשבורד לפי חודש (Monthly Focus)
        st.markdown("---")
        st.header("צלילה לעומק: ניתוח חודשי")
        
        selected_month = st.selectbox("בחר חודש לניתוח ממוקד:", reversed(monthly_summary['Month'].tolist()))
        
        exp_m = all_expenses[all_expenses['Month'] == selected_month]
        inc_m = all_incomes[all_incomes['Month'] == selected_month]
        
        st.subheader(f"סיכום חודש {selected_month}")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("סה\"כ הכנסות", f"{inc_m['Income'].sum():,.0f} ₪")
        m_col2.metric("סה\"כ הוצאות", f"{exp_m['Expense'].sum():,.0f} ₪")
        m_col3.metric("נטו (חיסכון)", f"{(inc_m['Income'].sum() - exp_m['Expense'].sum()):,.0f} ₪")
        
        row2_col1, row2_col2 = st.columns(2)
        
        # הוצאות לפי קטגוריה (עוגה)
        if not exp_m.empty:
            fig_pie_m = px.pie(exp_m, values='Expense', names='Category', title='פילוח הוצאות חודשי', hole=0.3)
            row2_col1.plotly_chart(fig_pie_m, use_container_width=True)
            
            # טבלת פיבוט חודשית
            pivot_m = exp_m.groupby(['Category', 'Desc'])['Expense'].sum().reset_index()
            pivot_m = pivot_m.sort_values(['Category', 'Expense'], ascending=[True, False])
            pivot_m.columns = ['קטגוריה', 'בית עסק', 'סה"כ (₪)']
            row2_col2.write("**פירוט הוצאות חודשי (Pivot)**")
            row2_col2.dataframe(pivot_m, use_container_width=True, hide_index=True)
        else:
            st.info("אין הוצאות לחודש זה.")

else:
    st.info("👈 כדי להתחיל, העלה את קובץ העו\"ש (ואת קבצי האשראי אם יש) בסרגל הצד.")