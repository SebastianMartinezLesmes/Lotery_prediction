# src/utils/zodiaco.py

ZODIACO = [
    "ARIES", "TAURO", "GÉMINIS", "CÁNCER",
    "LEO", "VIRGO", "LIBRA", "ESCORPIO",
    "SAGITARIO", "CAPRICORNIO", "ACUARIO", "PISCIS"
]

def obtener_zodiaco(codigo):
    try:
        return ZODIACO[int(codigo)]
    except:
        return str(codigo)
