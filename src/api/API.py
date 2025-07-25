import requests
from datetime import datetime, timedelta
from src.utils.config import FIND_LOTERY  # ← constante importada desde config.py

def eliminar_duplicados(lista, claves):
    """Elimina duplicados de una lista de diccionarios según las claves indicadas."""
    vistos = set()
    resultado_filtrado = []
    for item in lista:
        identidad = tuple(item.get(clave) for clave in claves)
        if identidad not in vistos:
            vistos.add(identidad)
            resultado_filtrado.append(item)
    return resultado_filtrado

def obtener_resultados_históricos_astro(fecha_inicio=None):
    url_base = "https://api-resultadosloterias.com/api/results/"
    hoy = datetime.today()

    if fecha_inicio is None:
        fecha_inicio = datetime.strptime("2023-02-01", "%Y-%m-%d")

    resultados_astro = []
    dias_totales = (hoy - fecha_inicio).days + 1  # +1 para incluir hoy

    for i in range(dias_totales):
        fecha_actual = fecha_inicio + timedelta(days=i)
        fecha_str = fecha_actual.strftime("%Y-%m-%d")
        url = f"{url_base}{fecha_str}"

        try:
            respuesta = requests.get(url)
            respuesta.raise_for_status()
            datos = respuesta.json()
            resultados_dia = datos.get("data", [])

            resultados_filtrados = [
                resultado for resultado in resultados_dia
                if FIND_LOTERY in resultado.get("lottery", "").upper()
            ]

            resultados_unicos = eliminar_duplicados(
                resultados_filtrados,
                claves=["lottery", "slug", "date", "result", "series"]
            )

            if resultados_unicos:
                resultados_astro.append({
                    "fecha": fecha_str,
                    "resultados": resultados_unicos
                })
                print(f"✅ Resultados {FIND_LOTERY} obtenidos para {fecha_str}")
            else:
                print(f"❌ No hubo resultados {FIND_LOTERY} para {fecha_str}")

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error obteniendo resultados para {fecha_str}: {e}")

    return resultados_astro

# Ejecutar y mostrar resumen detallado
if __name__ == "__main__":
    resultados = obtener_resultados_históricos_astro()
    for dia in resultados:
        print(f"\n📅 Fecha: {dia['fecha']}")
        for resultado in dia['resultados']:
            print(f"🔮 Lotería {FIND_LOTERY}:")
            for clave, valor in resultado.items():
                print(f"   {clave}: {valor}")
