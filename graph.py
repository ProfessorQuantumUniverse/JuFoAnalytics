import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Jugend Forscht Analytics 2.0", page_icon="🚀", layout="wide")

# --- DATEN LADEN UND VERARBEITEN (ERWEITERT) ---
@st.cache_data
def load_data():
    df = pd.read_csv("jugend_forscht_projekte.csv")
    
    # 1. Teamgröße & Kategorie
    df['Teamgröße'] = df['Teilnehmende'].apply(lambda x: len(str(x).split(',')))
    df['Team_Kategorie'] = df['Teamgröße'].apply(lambda x: 'Einzelprojekt' if x == 1 else ('2er Team' if x == 2 else '3er+ Team'))
    
    # 2. Alter extrahieren
    def extract_avg_age(text):
        ages = re.findall(r'\((\d{2})', str(text))
        ages =[int(a) for a in ages if 10 <= int(a) <= 22] 
        return sum(ages)/len(ages) if ages else None
    df['Durchschnittsalter'] = df['Beschreibung_und_Preise'].apply(extract_avg_age)
    
    # 3. Preise & Sponsoren extrahieren
    df['Ist_Bundessieger'] = df['Beschreibung_und_Preise'].apply(lambda x: True if 'Bundessieg' in str(x) else False)
    df['Anzahl_Preise'] = df['Beschreibung_und_Preise'].apply(lambda x: str(x).count('Preisstifter:'))
    
    def extract_sponsors(text):
        matches = re.findall(r'Preisstifter:\s*(.*?)(?=\n|$)', str(text))
        return [m.strip() for m in matches]
    df['Sponsoren'] = df['Beschreibung_und_Preise'].apply(extract_sponsors)
    
    # 4. Mega-Trends & Technologien (NLP Keyword Matching)
    df['Thema_KI_Software'] = df['Titel'].str.contains('KI|Künstliche Intelligenz|Software|Algorithmus|App|Neuronale', case=False, na=False)
    df['Thema_Klima_Umwelt'] = df['Titel'].str.contains('Klima|Umwelt|Solar|Wind|CO2|Wasser|Nachhaltig|Recycling', case=False, na=False)
    df['Thema_Medizin_Bio'] = df['Titel'].str.contains('Medizin|Zelle|Virus|Krankheit|Blut|Protein|Bakterien', case=False, na=False)
    
    df['Tech_3D_Druck'] = df['Beschreibung_und_Preise'].str.contains('3-D-Druck|3D-Druck|Drucker', case=False, na=False)
    df['Tech_Sensorik'] = df['Beschreibung_und_Preise'].str.contains('Sensor|Messen', case=False, na=False)
    df['Tech_App_Dev'] = df['Beschreibung_und_Preise'].str.contains('App|Smartphone|Bluetooth', case=False, na=False)
    df['Tech_Simulation'] = df['Beschreibung_und_Preise'].str.contains('Simulation|simulieren|Modell', case=False, na=False)
    
    # 5. Schul-/Institutionsarten
    df['Inst_Gymnasium'] = df['Beschreibung_und_Preise'].str.contains('Gymnasium', case=False, na=False)
    df['Inst_Uni_HS'] = df['Beschreibung_und_Preise'].str.contains('Universität|Hochschule|Institut', case=False, na=False)
    df['Inst_SFZ'] = df['Beschreibung_und_Preise'].str.contains('Forschungszentrum', case=False, na=False)
    
    # 6. NLP Features
    df['Titel_Länge'] = df['Titel'].apply(lambda x: len(str(x)))
    
    return df

df = load_data()

# --- SIDEBAR: FILTER ---
st.sidebar.image("https://www.jugend-forscht.de/typo3conf/ext/sms_jufoprojects/Resources/Public/Images/logo.png", width=200)
st.sidebar.header("🔍 Steuerpult (Filter)")

selected_years = st.sidebar.multiselect("Jahr(e) auswählen", options=sorted(df['Jahr'].unique(), reverse=True), default=sorted(df['Jahr'].unique(), reverse=True))
selected_fachgebiete = st.sidebar.multiselect("Fachgebiet(e)", options=df['Fachgebiet'].unique(), default=df['Fachgebiet'].unique())
selected_bundeslaender = st.sidebar.multiselect("Bundesland", options=df['Bundesland'].unique(), default=df['Bundesland'].unique())

# Nur Bundessieger?
only_winners = st.sidebar.checkbox("🏆 Nur Bundessieger anzeigen")

# Daten filtern
df_filtered = df[
    (df['Jahr'].isin(selected_years)) & 
    (df['Fachgebiet'].isin(selected_fachgebiete)) & 
    (df['Bundesland'].isin(selected_bundeslaender))
]

if only_winners:
    df_filtered = df_filtered[df_filtered['Ist_Bundessieger'] == True]

# --- MAIN DASHBOARD ---
st.title("🚀 Jugend Forscht Intelligence Dashboard 2.0")
st.markdown("Das ultimative Analysetool für Muster, Trends und Erfolgsfaktoren.")

if df_filtered.empty:
    st.warning("Keine Daten für die gewählten Filter gefunden.")
    st.stop()

# --- TABS ---
tabs = st.tabs([
    "📊 KPIs & Übersicht", 
    "👥 Demografie & Herkunft", 
    "🗺️ Geografie (Deep Dive)", 
    "🏆 Preise & Sponsoren",
    "🔬 Technologie-Stack",
    "🧠 Data Science & NLP",
    "💾 Daten-Export",
    "📈 Erfolgsfaktoren & Trends",
    "🔍 Text Mining & Explorer"
])

# --- TAB 1: ÜBERSICHT ---
with tabs[0]:
    st.header("Executive Summary")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Projekte", len(df_filtered))
    c2.metric("Teilnehmende", df_filtered['Teamgröße'].sum())
    c3.metric("Sonderpreise ges.", df_filtered['Anzahl_Preise'].sum())
    c4.metric("Bundessiege", df_filtered['Ist_Bundessieger'].sum())
    c5.metric("Ø Alter", f"{df_filtered['Durchschnittsalter'].mean():.1f} J." if pd.notna(df_filtered['Durchschnittsalter'].mean()) else "N/A")
    
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        df_year = df_filtered.groupby('Jahr').size().reset_index(name='Anzahl Projekte')
        fig_year = px.line(df_year, x='Jahr', y='Anzahl Projekte', markers=True, title="Projektanzahl im Zeitverlauf", line_shape="spline")
        fig_year.update_layout(xaxis=dict(tickmode='linear', dtick=1))
        st.plotly_chart(fig_year, use_container_width=True)
        
    with col_b:
        df_fach = df_filtered['Fachgebiet'].value_counts().reset_index(name='Anzahl')
        fig_fach = px.pie(df_fach, names='Fachgebiet', values='Anzahl', title="Verteilung nach Fachgebieten", hole=0.4)
        st.plotly_chart(fig_fach, use_container_width=True)

# --- TAB 2: DEMOGRAFIE & HERKUNFT ---
with tabs[1]:
    st.header("Wer forscht und woher kommen sie?")
    
    col1, col2 = st.columns(2)
    with col1:
        fig_age = px.histogram(df_filtered, x='Durchschnittsalter', nbins=15, title="Altersverteilung", marginal="box", color_discrete_sequence=['#005B9F'])
        st.plotly_chart(fig_age, use_container_width=True)
        
    with col2:
        fig_team = px.histogram(df_filtered, x='Team_Kategorie', color='Fachgebiet', title="Teamgrößen nach Fachgebiet", barmode='stack')
        st.plotly_chart(fig_team, use_container_width=True)
        
    st.markdown("### Welche Institutionen unterstützen die Projekte?")
    inst_data = {
        'Institution':['Gymnasium', 'Universität/Hochschule', 'Schülerforschungszentrum (SFZ)'],
        'Anzahl': [df_filtered['Inst_Gymnasium'].sum(), df_filtered['Inst_Uni_HS'].sum(), df_filtered['Inst_SFZ'].sum()]
    }
    fig_inst = px.bar(pd.DataFrame(inst_data), x='Anzahl', y='Institution', orientation='h', color='Institution', title="Erwähnung von Institutionen in der Beschreibung")
    st.plotly_chart(fig_inst, use_container_width=True)

# --- TAB 3: GEOGRAFIE DEEP DIVE ---
with tabs[2]:
    st.header("Interaktive Landkarte der Ideen")
    st.markdown("Klicke in das Diagramm, um von Bundesländern in die Fachgebiete hineinzuzoomen!")
    
    # Treemap
    fig_tree = px.treemap(df_filtered, path=[px.Constant("Deutschland"), 'Bundesland', 'Fachgebiet'], 
                          title="Projektverteilung (Hierarchie: Bundesland -> Fachgebiet)",
                          color='Bundesland', color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_tree.update_traces(root_color="lightgrey")
    fig_tree.update_layout(margin=dict(t=50, l=25, r=25, b=25), height=600)
    st.plotly_chart(fig_tree, use_container_width=True)

# --- TAB 4: PREISE & SPONSOREN ---
with tabs[3]:
    st.header("Wer sponsert die Jugend?")
    
    col1, col2 = st.columns(2)
    with col1:
        fig_preise = px.histogram(df_filtered, x='Anzahl_Preise', title="Wie viele Sonderpreise gewinnen Projekte?", text_auto=True)
        fig_preise.update_layout(xaxis_title="Anzahl Preise", yaxis_title="Anzahl Projekte")
        st.plotly_chart(fig_preise, use_container_width=True)
        
    with col2:
        # Sponsoren extrahieren und zählen
        all_sponsors =[sponsor for sublist in df_filtered['Sponsoren'] for sponsor in sublist]
        if all_sponsors:
            df_sponsors = pd.Series(all_sponsors).value_counts().reset_index()
            df_sponsors.columns = ['Sponsor', 'Anzahl']
            fig_sponsors = px.bar(df_sponsors.head(10), x='Anzahl', y='Sponsor', orientation='h', title="Top 10 Preisstifter & Sponsoren")
            fig_sponsors.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_sponsors, use_container_width=True)
        else:
            st.info("Keine Sponsorendaten in dieser Filterung gefunden.")

# --- TAB 5: TECHNOLOGIE-STACK ---
# --- TAB 5: TECHNOLOGIE-STACK ---
with tabs[4]:
    st.header("Verwendete Technologien & Methoden")
    
    tech_data = {
        'Technologie':['Simulation & Modellierung', 'Sensorik & Messen', '3D-Druck', 'App- & Smartphone-Dev'],
        'Projekte': [df_filtered['Tech_Simulation'].sum(), df_filtered['Tech_Sensorik'].sum(), 
                     df_filtered['Tech_3D_Druck'].sum(), df_filtered['Tech_App_Dev'].sum()]
    }
    df_tech = pd.DataFrame(tech_data)
    
    # NEU: Sortieren für den perfekten Trichter-Look (breiteste oben)
    df_tech = df_tech.sort_values(by='Projekte', ascending=False)
    
    # FEHLER BEHOBEN: x und y anstelle von path und values
    fig_tech = px.funnel(df_tech, x='Projekte', y='Technologie', title="Tech-Funnel: Was nutzen die Forscher am meisten?")
    st.plotly_chart(fig_tech, use_container_width=True)
    
    st.markdown("### Meta-Trends der Fachthemen")
    trend_data = {
        'Thema':['KI & Software', 'Klima & Umwelt', 'Medizin & Bio'],
        'Projekte':[df_filtered['Thema_KI_Software'].sum(), df_filtered['Thema_Klima_Umwelt'].sum(), df_filtered['Thema_Medizin_Bio'].sum()]
    }
    fig_trends = px.bar(pd.DataFrame(trend_data), x='Thema', y='Projekte', title="Mega-Trends in Projekttiteln", color='Thema', text_auto=True)
    st.plotly_chart(fig_trends, use_container_width=True)

# --- TAB 6: DATA SCIENCE & NLP ---
with tabs[5]:
    st.header("Tiefe Analysen: Zusammenhänge & Text Mining")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Korrelations-Matrix")
        st.markdown("Welche numerischen Faktoren hängen zusammen? (1.0 = starke Korrelation)")
        corr_cols =['Jahr', 'Teamgröße', 'Durchschnittsalter', 'Anzahl_Preise', 'Titel_Länge']
        corr_matrix = df_filtered[corr_cols].corr()
        
        fig_corr = px.imshow(corr_matrix, text_auto=True, color_continuous_scale='RdBu_r', aspect="auto")
        st.plotly_chart(fig_corr, use_container_width=True)
        
    with col2:
        st.subheader("Titel-Länge vs. Preise")
        fig_scatter = px.scatter(df_filtered, x='Titel_Länge', y='Anzahl_Preise', color='Fachgebiet', 
                                 size='Teamgröße', hover_data=['Titel'],
                                 title="Gewinnen lange Titel mehr Preise?")
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.divider()
    st.subheader("Wordcloud der Projekt-Beschreibungen")
    
    text = " ".join(desc for desc in df_filtered['Beschreibung_und_Preise'].astype(str))
    stopwords = set(["der", "die", "das", "und", "in", "im", "mit", "von", "für", "ein", "eine", "einer", "einem", "auf", "an", "zur", "zu", "aus", "über", "durch", "des", "den", "als", "am", "wie", "ist", "sind", "sich", "dass", "werden", "wurde", "es", "auch"])
    
    if text.strip() != "":
        wordcloud = WordCloud(width=1200, height=400, background_color='black', colormap='Wistia', stopwords=stopwords).generate(text)
        fig, ax = plt.subplots(figsize=(15, 5), facecolor='k')
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig)
    else:
        st.warning("Nicht genug Textdaten für Wordcloud.")

# --- TAB 7: DATEN-EXPORT ---
with tabs[6]:
    st.header("Daten-Export & Rohdaten")
    st.markdown("Hier siehst du die aufbereiteten Daten mit allen neu berechneten Features.")
    
    # Zeige Daten an
    st.dataframe(df_filtered, use_container_width=True)
    
    # CSV Download Button
    csv = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Gefilterte & Erweiterte Daten als CSV herunterladen",
        data=csv,
        file_name='jugend_forscht_analytics_export.csv',
        mime='text/csv',
    )

    # --- TAB 4: ERFOLG & TRENDS ---
with tabs [7]:
    st.header("Erfolgsfaktoren & Forschungs-Trends")
    
    col1, col2 = st.columns(2)
    with col1:
        # Bundessieger nach Bundesland
        df_bundessieger = df_filtered[df_filtered['Ist_Bundessieger'] == True]
        if not df_bundessieger.empty:
            fig_sieger = px.bar(df_bundessieger['Bundesland'].value_counts().reset_index(), x='Bundesland', y='count', title="Anzahl Bundessiege nach Bundesland", color_discrete_sequence=['#FFD700'])
            st.plotly_chart(fig_sieger, use_container_width=True)
        else:
            st.info("Keine Bundessiege in den gewählten Filtern vorhanden.")
            
    with col2:
        # Trend Themen
        trend_data = {
            'Thema': ['KI & Software', 'Klima & Umwelt', 'Medizin & Bio'],
            'Projekte':[df_filtered['Thema_KI_Software'].sum(), df_filtered['Thema_Klima_Umwelt'].sum(), df_filtered['Thema_Medizin_Bio'].sum()]
        }
        fig_trends = px.bar(pd.DataFrame(trend_data), x='Thema', y='Projekte', title="Identifizierte Mega-Trends in Projekttiteln", color='Thema')
        st.plotly_chart(fig_trends, use_container_width=True)

    # Zeige die Bundessieger-Projekte an
    st.subheader("Die Bundessieger-Projekte im Detail")
    st.dataframe(df_bundessieger[['Jahr', 'Fachgebiet', 'Bundesland', 'Titel', 'Teilnehmende']], use_container_width=True, hide_index=True)

# --- TAB 5: TEXTMINING ---
with tabs [8]:
    st.header("Wortwolke der Projekttitel")
    st.markdown("Welche Begriffe dominieren die Forschung der Jugendlichen?")
    
    # Text generieren
    text = " ".join(title for title in df_filtered['Titel'].astype(str))
    
    # Deutsche Stopwörter (vereinfachte Liste)
    stopwords = set(["der", "die", "das", "und", "in", "im", "mit", "von", "für", "ein", "eine", "einer", "einem", "auf", "an", "zur", "zu", "aus", "über", "durch", "des", "den", "als", "am", "wie", "ist", "sind"])
    
    if text.strip() != "":
        wordcloud = WordCloud(width=1200, height=500, background_color='white', colormap='tab20', stopwords=stopwords).generate(text)
        
        fig, ax = plt.subplots(figsize=(15, 6))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig)
    else:
        st.warning("Nicht genug Textdaten für Wordcloud.")
        
    st.header("Daten-Explorer")
    st.dataframe(df_filtered[['Jahr', 'Fachgebiet', 'Bundesland', 'Titel', 'Teilnehmende', 'Beschreibung_und_Preise']], use_container_width=True)