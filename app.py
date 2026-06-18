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
WORLD_BANK_GDP = "https://api.worldbank.org/v2/country/ARG/indicator/NY.GDP.MKTP.CD"

def get_json(url, params=None):
    r = requests.get(
        url,
        params=params,
        timeout=30,
        headers={"Accept-Language": "es-AR"}
    )
    r.raise_for_status()
    return r.json()

def fmt_num(x):
    try:
        return f"{float(x):,.2f}"
    except Exception:
        return "No disponible"

def fmt_pct(x):
    try:
        v = float(x)
        if 0 < v < 1:
            v = v * 100
        return f"{v:.2f}"
    except Exception:
        return "No disponible"

def add_row(filas, indicador, valor, unidad, fecha, periodicidad, fuente, tipo_fuente):
    filas.append({
        "Indicador": indicador,
        "Valor": valor,
        "Unidad": unidad,
        "Fecha dato": fecha,
        "Periodicidad": periodicidad,
        "Fuente": fuente,
        "Tipo fuente": tipo_fuente
    })

def bcra_variable_por_id(id_variable):
    try:
        js = get_json(BCRA, {"IdVariable": id_variable, "Limit": 1000})
        data = js.get("results", [])

        for item in data:
            if int(item.get("idVariable", -1)) == int(id_variable):
                return item

        return data[0] if data else None
    except Exception:
        return None

def bcra_variable_por_texto(textos):
    try:
        js = get_json(BCRA, {"Limit": 1000})
        data = js.get("results", [])

        for item in data:
            desc = item.get("descripcion", "").lower()
            if any(t.lower() in desc for t in textos):
                return item

        return None
    except Exception:
        return None

def bcra_ultimos_valores(id_variable, cantidad=2):
    try:
        url = f"{BCRA}/{id_variable}"
        js = get_json(url, {"Limit": cantidad})
        results = js.get("results", [])

        if not results:
            return []

        detalle = results[0].get("detalle", [])
        detalle = sorted(detalle, key=lambda x: x.get("fecha", ""), reverse=True)
        return detalle[:cantidad]
    except Exception:
        return []

def variacion_diaria_bcra(id_variable):
    datos = bcra_ultimos_valores(id_variable, 2)

    if len(datos) < 2:
        return "No disponible", ""

    actual = float(datos[0]["valor"])
    previo = float(datos[1]["valor"])
    fecha = datos[0]["fecha"]

    if previo == 0:
        return "No disponible", fecha

    var = ((actual / previo) - 1) * 100
    return f"{var:.2f}", fecha

def serie_datos_gob(series_id):
    try:
        js = get_json(DATOS_GOB, {
            "ids": series_id,
            "limit": 1,
            "sort": "desc",
            "format": "json"
        })
        data = js.get("data", [])
        return data[0] if data else None
    except Exception:
        return None

def pbi_banco_mundial():
    try:
        js = get_json(WORLD_BANK_GDP, {
            "format": "json",
            "mrnev": 1
        })

        data = js[1] if isinstance(js, list) and len(js) > 1 else []

        for item in data:
            if item.get("value") is not None:
                return item

        return None
    except Exception:
        return None

filas = []

# 1. Reservas internacionales
reservas = bcra_variable_por_id(1)
add_row(
    filas,
    "Reservas internacionales",
    fmt_num(reservas.get("ultValorInformado")) if reservas else "No disponible",
    "millones de USD",
    reservas.get("ultFechaInformada", "") if reservas else "",
    "Diaria",
    "BCRA oficial",
    "Oficial"
)

# 2. Tipo de cambio minorista
tc_minorista = bcra_variable_por_id(4)
add_row(
    filas,
    "Tipo de cambio minorista ARS/USD",
    fmt_num(tc_minorista.get("ultValorInformado")) if tc_minorista else "No disponible",
    "ARS por USD",
    tc_minorista.get("ultFechaInformada", "") if tc_minorista else "",
    "Diaria",
    "BCRA oficial",
    "Oficial"
)

# 3. Tipo de cambio mayorista
tc_mayorista = bcra_variable_por_id(5)
add_row(
    filas,
    "Tipo de cambio mayorista ARS/USD",
    fmt_num(tc_mayorista.get("ultValorInformado")) if tc_mayorista else "No disponible",
    "ARS por USD",
    tc_mayorista.get("ultFechaInformada", "") if tc_mayorista else "",
    "Diaria",
    "BCRA oficial",
    "Oficial"
)

# 4. Variación diaria tipo de cambio mayorista
var_tc, fecha_var_tc = variacion_diaria_bcra(5)
add_row(
    filas,
    "Variación diaria tipo de cambio mayorista",
    var_tc,
    "%",
    fecha_var_tc,
    "Diaria",
    "BCRA oficial",
    "Oficial"
)

# 5. Tasa de interés oficial / política monetaria
tasa = bcra_variable_por_id(6)

if not tasa:
    tasa = bcra_variable_por_texto([
        "tasa de política monetaria",
        "tasa de politica monetaria"
    ])

valor_tasa = "No disponible"
fecha_tasa = ""

if tasa:
    raw_tasa = tasa.get("ultValorInformado")
    fecha_tasa = tasa.get("ultFechaInformada", "")

    try:
        if float(raw_tasa) > 0:
            valor_tasa = fmt_pct(raw_tasa)
    except Exception:
        valor_tasa = "No disponible"

add_row(
    filas,
    "Tasa de interés oficial / política monetaria",
    valor_tasa,
    "% TNA",
    fecha_tasa,
    "Diaria",
    "BCRA oficial",
    "Oficial"
)

# 6. Inflación mensual
inflacion = bcra_variable_por_texto([
    "inflación mensual",
    "inflacion mensual"
])

add_row(
    filas,
    "Inflación mensual",
    fmt_pct(inflacion.get("ultValorInformado")) if inflacion else "No disponible",
    "%",
    inflacion.get("ultFechaInformada", "") if inflacion else "",
    "Mensual",
    "BCRA / INDEC",
    "Oficial"
)

# 7. Desempleo
desempleo = serie_datos_gob("45.2_ECTDT_0_T_33")

add_row(
    filas,
    "Tasa de desempleo total",
    fmt_pct(desempleo[1]) if desempleo else "No disponible",
    "%",
    desempleo[0] if desempleo else "",
    "Trimestral",
    "datos.gob.ar / INDEC",
    "Oficial"
)

# 8. PBI nominal
pbi = pbi_banco_mundial()

add_row(
    filas,
    "PBI nominal",
    fmt_num(pbi.get("value")) if pbi else "No disponible",
    "USD corrientes",
    pbi.get("date", "") if pbi else "",
    "Anual",
    "Banco Mundial",
    "Organismo internacional"
)

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
- Banco Mundial: PBI nominal en USD corrientes.
""")
# =========================
# URUGUAY
# =========================

st.subheader("Uruguay")

def banco_mundial_uruguay(indicator):
    try:
        url = f"https://api.worldbank.org/v2/country/URY/indicator/{indicator}"
        js = get_json(url, {
            "format": "json",
            "mrnev": 1
        })

        data = js[1] if isinstance(js, list) and len(js) > 1 else []

        for item in data:
            if item.get("value") is not None:
                return item

        return None
    except Exception:
        return None

filas_uy = []

# 1. Reservas internacionales
reservas_uy = banco_mundial_uruguay("FI.RES.TOTL.CD")
add_row(
    filas_uy,
    "Reservas internacionales",
    fmt_num(reservas_uy.get("value")) if reservas_uy else "No disponible",
    "USD corrientes",
    reservas_uy.get("date", "") if reservas_uy else "",
    "Anual",
    "Banco Mundial",
    "Organismo internacional"
)

# 2. Tipo de cambio UYU/USD
tc_uy = banco_mundial_uruguay("PA.NUS.FCRF")
add_row(
    filas_uy,
    "Tipo de cambio UYU/USD",
    fmt_num(tc_uy.get("value")) if tc_uy else "No disponible",
    "UYU por USD",
    tc_uy.get("date", "") if tc_uy else "",
    "Anual",
    "Banco Mundial",
    "Organismo internacional"
)

# 3. Variación diaria tipo de cambio
add_row(
    filas_uy,
    "Variación diaria tipo de cambio",
    "No disponible",
    "%",
    "",
    "Diaria",
    "Pendiente de fuente diaria verificable",
    "No disponible"
)

# 4. Tasa de interés oficial
add_row(
    filas_uy,
    "Tasa de interés oficial / política monetaria",
    "No disponible",
    "% TNA",
    "",
    "Según decisión COPOM",
    "BCU oficial",
    "Oficial"
)

# 5. Inflación
inflacion_uy = banco_mundial_uruguay("FP.CPI.TOTL.ZG")
add_row(
    filas_uy,
    "Inflación anual",
    fmt_pct(inflacion_uy.get("value")) if inflacion_uy else "No disponible",
    "%",
    inflacion_uy.get("date", "") if inflacion_uy else "",
    "Anual",
    "Banco Mundial",
    "Organismo internacional"
)

# 6. Desempleo
desempleo_uy = banco_mundial_uruguay("SL.UEM.TOTL.ZS")
add_row(
    filas_uy,
    "Tasa de desempleo total",
    fmt_pct(desempleo_uy.get("value")) if desempleo_uy else "No disponible",
    "%",
    desempleo_uy.get("date", "") if desempleo_uy else "",
    "Anual",
    "Banco Mundial",
    "Organismo internacional"
)

# 7. PBI nominal
pbi_uy = banco_mundial_uruguay("NY.GDP.MKTP.CD")
add_row(
    filas_uy,
    "PBI nominal",
    fmt_num(pbi_uy.get("value")) if pbi_uy else "No disponible",
    "USD corrientes",
    pbi_uy.get("date", "") if pbi_uy else "",
    "Anual",
    "Banco Mundial",
    "Organismo internacional"
)

df_uy = pd.DataFrame(filas_uy)

st.dataframe(df_uy, use_container_width=True)
