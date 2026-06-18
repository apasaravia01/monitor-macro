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
    r = requests.get(url, params=params, timeout=25, headers={"Accept-Language": "es-AR"})
    r.raise_for_status()
    return r.json()

def buscar_bcra_por_id(id_variable):
    js = get_json(BCRA_MONETARIAS, {"IdVariable": id_variable})
    results = js.get("results", [])
    return results[0] if results else None

def serie_datos_gob(series_id):
    js = get_json(DATOS_GOB, {
        "ids": series_id,
        "limit": 2,
        "sort": "desc",
        "format": "json"
    })
    data = js.get("data", [])
    return data[0] if data else None

filas = []

# BCRA IDs oficiales documentados:
# 1 Reservas internacionales
# 4 Tipo de cambio minorista vendedor
# 5 Tipo de cambio mayorista A3500
for nombre, idv, unidad in [
    ("Reservas internacionales", 1, "millones de USD"),
    ("Tipo de cambio minorista ARS/USD", 4, "ARS por USD"),
    ("Tipo de cambio mayorista ARS/USD", 5, "ARS por USD"),
]:
    try:
        v = buscar_bcra_por_id(idv)
        filas.append({
            "Indicador": nombre,
            "Valor": v["ultValorInformado"],
            "Unidad": unidad,
            "Fecha dato": v["ultFechaInformada"],
            "Periodicidad": "Diaria",
            "Fuente": "BCRA oficial",
            "Tipo fuente": "Oficial"
        })
    except Exception as e:
        filas.append({
            "Indicador": nombre,
            "Valor": "No disponible",
            "Unidad": unidad,
            "Fecha dato": "",
            "Periodicidad": "Diaria",
            "Fuente": "BCRA oficial",
            "Tipo fuente": "Oficial"
        })

# Inflación mensual BCRA, búsqueda por texto en catálogo BCRA
try:
    js = get_json(BCRA_MONETARIAS, {"Limit": 1000})
    inflacion = None
    tamar = None

    for item in js.get("results", []):
        desc = item.get("descripcion", "").lower()
        if "inflación mensual" in desc or "inflacion mensual" in desc:
            inflacion = item
        if "tamar en pesos de bancos privados" in desc and "% n.a" in desc.lower():
            tamar = item

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

    if tamar:
        filas.append({
            "Indicador": "Tasa de interés TAMAR bancos privados",
            "Valor": tamar["ultValorInformado"],
            "Unidad": "% n.a.",
            "Fecha dato": tamar["ultFechaInformada"],
            "Periodicidad": "Diaria",
            "Fuente": "BCRA oficial",
            "Tipo fuente": "Oficial"
        })

except Exception:
    pass

# Desempleo total Argentina desde datos.gob.ar
try:
    desempleo = serie_datos_gob("45.2_ECTDT_0_T_33")
    filas.append({
        "Indicador": "Tasa de desempleo total",
        "Valor": desempleo[1],
        "Unidad": "%",
        "Fecha dato": desempleo[0],
        "Periodicidad": "Trimestral",
        "Fuente": "datos.gob.ar / INDEC",
        "Tipo fuente": "Oficial"
    })
except Exception:
    filas.append({
        "Indicador": "Tasa de desempleo total",
        "Valor": "No disponible",
        "Unidad": "%",
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
- BCRA API oficial: estadísticas monetarias.
- datos.gob.ar / INDEC: series de tiempo públicas.
""")
