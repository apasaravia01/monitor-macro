import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Monitor Macroeconómico Regional", layout="wide")

st.title("Monitor Macroeconómico Regional")
st.subheader("Argentina")

BCRA_MONETARIAS = "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias"
DATOS_GOB = "https://apis.datos.gob.ar/series/api/series/"

def get_json(url, params=None):
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    return r.json()

def buscar_bcra_por_id(id_variable):
    js = get_json(BCRA_MONETARIAS, {"IdVariable": id_variable})
    results = js.get("results", [])
    return results[0] if results else None

def buscar_bcra_por_texto(textos):
    js = get_json(BCRA_MONETARIAS, {"Limit": 1000})
    for item in js.get("results", []):
        desc = item.get("descripcion", "").lower()
        if any(t.lower() in desc for t in textos):
            return item
    return None

def serie_datos_gob(series_id):
    js = get_json(DATOS_GOB, {
        "ids": series_id,
        "limit": 2,
        "sort": "desc",
        "format": "json"
    })
    data = js.get("data", [])
    return data[0] if data else None

def formatear_porcentaje(valor):
    try:
        v = float(valor)
        if v < 1:
            v = v * 100
        return round(v, 2)
    except:
        return valor

filas = []

# BCRA: reservas y tipo de cambio
for nombre, idv, unidad in [
    ("Reservas internacionales", 1, "millones de USD"),
    ("Tipo de cambio minorista ARS/USD", 4, "ARS por USD"),
    ("Tipo de cambio mayorista ARS/USD", 5, "ARS por USD"),
]:
    try:
        v = buscar_bcra_por_id(idv)
        filas.append({
            "Indicador": nombre,
            "Valor": formatear_numero(v["ultValorInformado"]),
            "Unidad": unidad,
            "Fecha dato": v["ultFechaInformada"],
            "Periodicidad": "Diaria",
            "Fuente": "BCRA oficial",
            "Tipo fuente": "Oficial"
        })
    except:
        filas.append({
            "Indicador": nombre,
            "Valor": "No disponible",
            "Unidad": unidad,
            "Fecha dato": "",
            "Periodicidad": "Diaria",
            "Fuente": "BCRA oficial",
            "Tipo fuente": "Oficial"
        })

# Tasa de política monetaria oficial
try:
    tasa_oficial = buscar_bcra_por_texto([
        "tasa de política monetaria",
        "tasa de politica monetaria",
        "tasa de pases pasivos",
        "pases pasivos"
    ])

    if tasa_oficial:
        filas.append({
            "Indicador": "Tasa de interés oficial / política monetaria",
            "Valor": formatear_porcentaje(tasa_oficial["ultValorInformado"]),
            "Unidad": "%",
            "Fecha dato": tasa_oficial["ultFechaInformada"],
            "Periodicidad": "Diaria",
            "Fuente": "BCRA oficial",
            "Tipo fuente": "Oficial"
        })
    else:
        filas.append({
            "Indicador": "Tasa de interés oficial / política monetaria",
            "Valor": "No disponible",
            "Unidad": "%",
            "Fecha dato": "",
            "Periodicidad": "Diaria",
            "Fuente": "BCRA oficial",
            "Tipo fuente": "Oficial"
        })
except:
    pass

# Inflación mensual
try:
    inflacion = buscar_bcra_por_texto([
        "inflación mensual",
        "inflacion mensual"
    ])

    if inflacion:
        filas.append({
            "Indicador": "Inflación mensual",
            "Valor": inflacion["ultValorInformado"],
            "Unidad": "%",
            "Fecha dato": inflacion["ultFechaInformada"],
            "Periodicidad": "Mensual",
            "Fuente": "BCRA / INDEC",
            "Tipo fuente": "Oficial"
        })
except:
    pass

# Desempleo
try:
    desempleo = serie_datos_gob("45.2_ECTDT_0_T_33")
    filas.append({
        "Indicador": "Tasa de desempleo total",
        "Valor": formatear_porcentaje(desempleo[1]),
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

# PBI
try:
    pbi = serie_datos_gob("9.1_PDPC_2004_A_30")
    filas.append({
        "Indicador": "PBI en millones de USD corrientes",
        "Valor": formatear_numero(pbi[1]),
        "Unidad": "millones de USD",
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
    label="Descargar datos en CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="monitor_macro_argentina.csv",
    mime="text/csv"
)

st.caption(
    "Fecha y hora de consulta: "
    + datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")
)

st.markdown("""
### Fuentes utilizadas
- BCRA API oficial.
- datos.gob.ar / INDEC.
""")
