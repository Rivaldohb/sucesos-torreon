# sucesos_app.py
# Proyecto: Antecedentes de sucesos catastróficos - Tec Laguna / Torreón
# Autor: Rivaldo Hernández (Administración, Tec Laguna)
# Requisitos: pip install streamlit pandas matplotlib folium streamlit-folium

import sqlite3
from hmac import trans_5C

import pandas as pd
import streamlit as st
import datetime
import matplotlib.pyplot as plt
from math import exp
import folium
from streamlit_folium import st_folium

DB_PATH = "sucesos_torreon.db"

# --------------------------------------------------
# FUNCIONES DE BASE DE DATOS
# --------------------------------------------------
def crear_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sucesos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        tipo TEXT,
        subtipo TEXT,
        lugar TEXT,
        lat REAL,
        lon REAL,
        gravedad INTEGER,
        impacto TEXT,
        fuente TEXT,
        notas TEXT
    )
    ''')
    conn.commit()
    conn.close()

def agregar_suceso(fecha, tipo, subtipo, lugar, lat, lon, gravedad, impacto, fuente, notas):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO sucesos (fecha, tipo, subtipo, lugar, lat, lon, gravedad, impacto, fuente, notas)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fecha, tipo, subtipo, lugar, lat, lon, gravedad, impacto, fuente, notas))
    conn.commit()
    conn.close()

def cargar_datos():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM sucesos", conn)
    conn.close()
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    return df

# --------------------------------------------------
# FUNCIONES ANALÍTICAS
# --------------------------------------------------
def probabilidad_poisson(lmbda):
    return 1 - exp(-lmbda)

def resumen_probabilidades(df):
    if df.empty:
        return pd.DataFrame(columns=["Tipo", "Eventos últimos 5 años", "Promedio anual", "Probabilidad (al menos 1/año)"])
    df["year"] = df["fecha"].dt.year
    current_year = datetime.date.today().year
    recent = df[df["year"] >= current_year - 4]
    conteo = recent["tipo"].value_counts()
    data = []
    for tipo, n in conteo.items():
        avg = n / 5
        p = probabilidad_poisson(avg)
        data.append({"Tipo": tipo,
                     "Eventos últimos 5 años": n,
                     "Promedio anual": round(avg, 2),
                     "Probabilidad (al menos 1/año)": f"{p*100:.1f}%"})
    return pd.DataFrame(data)

# --------------------------------------------------
# INTERFAZ STREAMLIT
# --------------------------------------------------
st.set_page_config(page_title="Antecedentes de Sucesos - Tec Laguna", page_icon="🌪️", layout="wide")
st.title("🌪️ Antecedentes de Sucesos Catastróficos - Tec Laguna / Torreón")
st.caption("Proyecto universitario - Evaluación de riesgos urbanos (Rivaldo Hernández)")

crear_db()

tabs = st.tabs(["📋 Registrar suceso", "📈 Análisis", "🗺️ Mapa Interactivo"])

# --------------------------------------------------
# TAB 1: REGISTRO
# --------------------------------------------------
with tabs[0]:
    st.subheader("Registrar un nuevo suceso")
    # === Configurar modo solo lectura ===
allow_write = st.secrets.get("ALLOW_WRITE", "true").lower() == "true"
if not allow_write:
    st.info("🔒 Esta versión es pública y está en modo de solo lectura. Solo se pueden consultar antecedentes.")

    with st.form("form_suceso"):
        col1, col2 = st.columns(2)
        fecha = col1.date_input("Fecha del suceso", datetime.date.today())
        tipo = col2.selectbox("Tipo de suceso", ["Inundación", "Apagón", "Sismo", "Pandemia", "Protesta", "Derrumbe", "Otro"])
        subtipo = st.text_input("Título / subtipo breve")
        lugar = st.text_input("Lugar (ej. Tec Laguna, Torreón, colonia...)")
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitud (ej. 25.538)", value=25.538, format="%.6f")
        lon = c2.number_input("Longitud (ej. -103.448)", value=-103.448, format="%.6f")
        gravedad = st.slider("Nivel de gravedad", 1, 5, 3)
        impacto = st.text_area("Impacto / descripción breve")
        fuente = st.text_input("Fuente o enlace (opcional)")
        notas = st.text_area("Notas adicionales (opcional)")
        submit = st.form_submit_button("Guardar suceso")

        if allow_write:
    submit = st.form_submit_button("Guardar suceso")
    if submit:
        agregar_suceso(str(fecha), tipo, subtipo, lugar, lat, lon, gravedad, impacto, fuente, notas)
        st.success("✅ Suceso registrado correctamente.")
else:
    st.form_submit_button("Guardar suceso", disabled=True)


# --------------------------------------------------
# TAB 2: ANÁLISIS
# --------------------------------------------------
with tabs[1]:
    st.subheader("Análisis histórico y probabilidades")

    df = cargar_datos()
    if df.empty:
        st.warning("No hay datos registrados todavía.")
    else:
        col1, col2 = st.columns(2)
        tipo_sel = col1.multiselect("Filtrar por tipo", sorted(df["tipo"].unique()), default=sorted(df["tipo"].unique()))
        años = sorted(df["fecha"].dt.year.unique())
        año_sel = col2.multiselect("Filtrar por año", años, default=años)
        filtrado = df[df["tipo"].isin(tipo_sel) & df["fecha"].dt.year.isin(año_sel)]

        st.dataframe(filtrado.sort_values("fecha", ascending=False), use_container_width=True)

        # Gráfica de frecuencia
        st.markdown("### Frecuencia de sucesos por año")
        resumen = filtrado.groupby([filtrado["fecha"].dt.year, "tipo"]).size().reset_index(name="conteo")
        if not resumen.empty:
            fig, ax = plt.subplots()
            for tipo in resumen["tipo"].unique():
                subset = resumen[resumen["tipo"] == tipo]
                ax.plot(subset["fecha"], subset["conteo"], marker="o", label=tipo)
            ax.legend()
            ax.set_xlabel("Año")
            ax.set_ylabel("Número de sucesos")
            ax.set_title("Evolución de sucesos por tipo")
            st.pyplot(fig)

        # Tabla de probabilidades
        st.markdown("### Probabilidad estimada (últimos 5 años)")
        tabla_probs = resumen_probabilidades(df)
        st.dataframe(tabla_probs, use_container_width=True)

        st.download_button(
            label="📤 Descargar base (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="sucesos_torreon.csv",
            mime="text/csv"
        )

# --------------------------------------------------
# TAB 3: MAPA
# --------------------------------------------------
with tabs[2]:
    st.subheader("🗺️ Mapa interactivo de sucesos registrados")

    df = cargar_datos()
    if df.empty:
        st.info("Aún no hay sucesos registrados con coordenadas.")
    else:
        # Crear mapa centrado en Torreón
        mapa = folium.Map(location=[25.539, -103.448], zoom_start=12, tiles="CartoDB positron")

        for _, row in df.iterrows():
            if pd.notnull(row["lat"]) and pd.notnull(row["lon"]):
                popup = f"""
                <b>{row['tipo']}</b><br>
                Fecha: {row['fecha'].date()}<br>
                Lugar: {row['lugar']}<br>
                Gravedad: {row['gravedad']}<br>
                Impacto: {row['impacto'][:100]}...
                """
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=6 + row["gravedad"],
                    color="red" if row["gravedad"] >= 4 else "orange",
                    fill=True,
                    fill_opacity=0.7,
                    popup=popup
                ).add_to(mapa)

        st_data = st_folium(mapa, width=900, height=550)


