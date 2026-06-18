import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Monitor Macroeconómico Regional", layout="wide")

st.title("Monitor Macroeconómico Regional")
st.subheader("Argentina")

BCRA = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"
DATOS_GOB = "https://apis.datos.gob.ar/series/api/series/"

def get_json(url, params=None):
    r = requests.get(url, params=params, timeout=30, headers={"Accept-Language": "es-AR"})
    r.raise_for_status()
    return r.json()

def fmt_num(x):
    try:
        return f"{float(x):,.2f}"
    except:
        return x

def fmt_pct(x):
    try:
        v = float(x)
        if v < 1:
            v *= 100
        return f"{v:,.2f}"
    except:
        return x

def datos_bcra():
    js = get_json(BCRA)
    return js.get("results", [])

def buscar_bcra(textos):
    data = datos_bcra()
    for item in data:
        desc = item.get("descripcion", "").lower()
        if any(t.lower() in desc for t in textos):
            return item
    return None

def agregar_bcra(filas, indicador, textos, unidad, periodicidad, porcentaje=False, no_cero=False):
    item = buscar_bcra(textos)
    if not item:
        valor = "No disponible"
        fecha = ""
    else:
        raw = item.get("ultValorInformado")
        fecha = item.get("ultFechaInformada", "")
        try:
            if no_cero and float(raw) == 0:
                valor = "No disponible"
            else:
                valor = fmt_pct(raw) if porcentaje else fmt_num(raw)
        except:
            valor = "No disponible"

    filas.append({
        "Indicador": indicador,
        "Valor": valor,
        "Unidad": unidad,
        "Fecha dato": fecha,
        "Periodicidad": periodicidad,
        "Fuente": "BCRA oficial",
        "Tipo fuente": "Oficial"
    })

def serie_datos_gob(series_id):
    js = get_json(DATOS_GOB, {
        "ids": series_id,
        "limit": 1,
        "sort": "desc",
        "format": "json"
    })
    data = js.get("data", [])
    return data[0] if data else None

filas = []

agregar_bcra(
    filas,
    "Reservas internacionales",
    ["reservas internacionales"],
    "millones de USD",
    "Diaria"
)

agregar_bcra(
    filas,
    "Tipo de cambio minorista ARS/USD",
    ["tipo de cambio minorista", "minorista vendedor"],
    "ARS por USD",
    "Diaria"
)

agregar_bcra(
    filas,
    "Tipo de cambio mayorista ARS/USD",
    ["tipo de cambio mayorista", "comunicación a 3500", "a3500"],
    "ARS por USD",
    "Diaria"
)

agregar_bcra(
    filas,
    "Tasa de interés oficial / política monetaria",
    [
        "tasa de política monetaria",
        "tasa de politica monetaria",
        "pases pasivos",
        "tasa de pases"
    ],
    "% TNA",
    "Diaria",
    porcentaje=True,
    no_cero=True
)

agregar_bcra(
    filas,
    "Inflación mensual",
    ["inflación mensual", "inflacion mensual"],
    "%",
    "Mensual",
    porcentaje=True
)

try:
    desempleo = serie_datos_gob("45.2_ECTDT_0_T_33")
    filas.append({
        "Indicador": "Tasa de desempleo total",
        "Valor": fmt_pct(desempleo[1]),
        "Unidad": "%",
        "Fecha dato": desempleo[0],
        "Periodicidad": "Trimestral",
        "Fuente": "datos.gob.ar / INDEC",
        "Tipo fuente": "Oficial"
    })
except:
    filas.append({
        "Indicador": "Tasa de desempleo total",
        "Valor": "No disponible",
        "Unidad": "%",
        "Fecha dato": "",
        "Periodicidad": "Trimestral",
        "Fuente": "datos.gob.ar / INDEC",
        "Tipo fuente": "Oficial"
    })

try:
    pbi = serie_datos_gob("9.1_PBI_2004_T_19")
    filas.append({
        "Indicador": "PBI real",
        "Valor": fmt_num(pbi[1]),
        "Unidad": "millones de ARS 2004",
        "Fecha dato": pbi[0],
        "Periodicidad": "Trimestral",
        "Fuente": "datos.gob.ar / INDEC",
        "Tipo fuente": "Oficial"
    })
except:
    filas.append({
        "Indicador": "PBI",
        "Valor": "No disponible",
        "Unidad": "",
        "Fecha dato": "",
        "Periodicidad": "Trimestral",
        "Fuente": "datos.gob.ar / INDEC",
        "Tipo fuente": "Oficial"
    })

df = pd.DataFrame(filas)
st.dataframe(df, use_container_width=True)

st.download_button(
    "Descargar datos en CSV",
    df.to_csv(index=False).encode("utf-8"),
    "monitor_macro_argentina.csv",
    "text/csv"
)

st.caption(
    "Fecha y hora de consulta: "
    + datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")
)

st.markdown("""
### Fuentes utilizadas
- BCRA API oficial: estadísticas monetarias.
- datos.gob.ar / INDEC: series públicas.
""")
