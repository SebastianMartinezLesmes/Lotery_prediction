import requests
from datetime import datetime, timedelta
from tqdm import tqdm
from src.utils.config import FIND_LOTERY, API_URL, FECHA_DEFECTO, CLAVES_UNICAS  # ← constante desde config.py

def eliminar_duplicados(lista, claves):
    
    vistos = set()
    resultado_filtrado = []
    for item in lista:
        identidad = tuple(item.get(clave) for clave in claves)
        if identidad not in vistos:
            vistos.add(identidad)
            resultado_filtrado.append(item)
    return resultado_filtrado

def obtener_resultados_históricos_astro(fecha_inicio=None):
    
    hoy = datetime.today()

    if fecha_inicio is None:
        fecha_inicio = datetime.strptime(FECHA_DEFECTO, "%Y-%m-%d")

    todos_los_resultados = []
    dias_totales = (hoy - fecha_inicio).days + 1  # +1 para incluir hoy

    for i in tqdm(range(dias_totales), desc=f"Obteniendo {FIND_LOTERY}"):
        fecha_actual = fecha_inicio + timedelta(days=i)
        fecha_str = fecha_actual.strftime("%Y-%m-%d")
        url = f"{API_URL}{fecha_str}"

        try:
            respuesta = requests.get(url)
            respuesta.raise_for_status()
            json_api = respuesta.json()
            resultados_api_dia = json_api.get("data", [])

            resultados_filtrados = [
                resultado for resultado in resultados_api_dia
                if FIND_LOTERY in resultado.get("lottery", "").upper()
            ]

            resultados_unicos = eliminar_duplicados(
                resultados_filtrados,
                claves=CLAVES_UNICAS
            )

            if resultados_unicos:
                todos_los_resultados.append({
                    "fecha": fecha_str,
                    "resultados": resultados_unicos
                })
                print(f"✅ Resultados {FIND_LOTERY} obtenidos para {fecha_str}")
            else:
                print(f"❌ No hubo resultados {FIND_LOTERY} para {fecha_str}")

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error obteniendo resultados para {fecha_str}: {e}")

    return todos_los_resultados

if __name__ == "__main__":
    resultados = obtener_resultados_históricos_astro()
    for dia in resultados:
        print(f"\n📅 Fecha: {dia['fecha']}")
        for resultado in dia['resultados']:
            print(f"🔮 Lotería {FIND_LOTERY}:")
            for clave, valor in resultado.items():
                print(f"   {clave}: {valor}")
