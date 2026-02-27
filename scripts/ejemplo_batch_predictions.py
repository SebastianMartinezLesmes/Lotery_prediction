"""
Script de ejemplo para demostrar el uso de batch predictions.
Muestra diferentes casos de uso del sistema de predicciones por lotes.
"""
from datetime import datetime, timedelta
from src.utils.batch_prediction import (
    BatchPredictor,
    predecir_batch_todas_loterias,
    mostrar_predicciones_batch,
    guardar_predicciones_batch
)


def ejemplo_1_proximos_dias():
    """Ejemplo 1: Predicción para los próximos 7 días."""
    print("\n" + "="*70)
    print("EJEMPLO 1: Predicción para los próximos 7 días")
    print("="*70)
    
    predictor = BatchPredictor("ASTRO LUNA")
    predicciones = predictor.predecir_proximos_dias(dias=7)
    
    print(f"\nPredicciones generadas: {len(predicciones)}")
    for pred in predicciones:
        print(f"  {pred['fecha']} ({pred['dia_semana'][:3]}) | "
              f"Número: {pred['numero']} | Símbolo: {pred['simbolo']}")


def ejemplo_2_rango_fechas():
    """Ejemplo 2: Predicción para un rango de fechas específico."""
    print("\n" + "="*70)
    print("EJEMPLO 2: Predicción para rango de fechas (marzo 2026)")
    print("="*70)
    
    predictor = BatchPredictor("ASTRO SOL")
    
    fecha_inicio = datetime(2026, 3, 1)
    fecha_fin = datetime(2026, 3, 31)
    
    predicciones = predictor.predecir_rango(fecha_inicio, fecha_fin)
    
    print(f"\nPredicciones para marzo 2026: {len(predicciones)} días")
    print("\nPrimeros 5 días:")
    for pred in predicciones[:5]:
        print(f"  {pred['fecha']} | Número: {pred['numero']} | Símbolo: {pred['simbolo']}")
    
    print("\n...")
    print("\nÚltimos 5 días:")
    for pred in predicciones[-5:]:
        print(f"  {pred['fecha']} | Número: {pred['numero']} | Símbolo: {pred['simbolo']}")


def ejemplo_3_fechas_especificas():
    """Ejemplo 3: Predicción para fechas específicas (días de pago)."""
    print("\n" + "="*70)
    print("EJEMPLO 3: Predicción para fechas específicas (días de pago)")
    print("="*70)
    
    predictor = BatchPredictor("ASTRO LUNA")
    
    # Fechas de pago típicas
    fechas = [
        datetime(2026, 3, 15),  # Quincena
        datetime(2026, 3, 30),  # Fin de mes
        datetime(2026, 4, 15),  # Quincena
        datetime(2026, 4, 30),  # Fin de mes
    ]
    
    predicciones = predictor.predecir_fechas_especificas(fechas)
    
    print("\nPredicciones para días de pago:")
    for pred in predicciones:
        print(f"  {pred['fecha']} | Número: {pred['numero']} | Símbolo: {pred['simbolo']}")


def ejemplo_4_todas_loterias():
    """Ejemplo 4: Predicción para todas las loterías disponibles."""
    print("\n" + "="*70)
    print("EJEMPLO 4: Predicción para todas las loterías (14 días)")
    print("="*70)
    
    predicciones = predecir_batch_todas_loterias(dias=14)
    mostrar_predicciones_batch(predicciones)


def ejemplo_5_guardar_json():
    """Ejemplo 5: Generar y guardar predicciones en JSON."""
    print("\n" + "="*70)
    print("EJEMPLO 5: Generar y guardar predicciones en JSON")
    print("="*70)
    
    predicciones = predecir_batch_todas_loterias(dias=30)
    guardar_predicciones_batch(predicciones)
    
    print("\n✅ Predicciones guardadas en: data/batch_predictions_*.json")
    print("   Puedes usar este archivo para análisis posterior")


def ejemplo_6_analisis_tendencias():
    """Ejemplo 6: Análisis de tendencias en predicciones."""
    print("\n" + "="*70)
    print("EJEMPLO 6: Análisis de tendencias")
    print("="*70)
    
    predictor = BatchPredictor("ASTRO LUNA")
    predicciones = predictor.predecir_proximos_dias(dias=30)
    
    # Contar frecuencia de símbolos
    simbolos = {}
    for pred in predicciones:
        simbolo = pred['simbolo']
        simbolos[simbolo] = simbolos.get(simbolo, 0) + 1
    
    print("\nFrecuencia de símbolos en los próximos 30 días:")
    for simbolo, count in sorted(simbolos.items(), key=lambda x: x[1], reverse=True):
        porcentaje = (count / len(predicciones)) * 100
        print(f"  {simbolo:15} | {count:2} veces ({porcentaje:5.1f}%)")
    
    # Análisis de números
    numeros = [int(pred['numero']) for pred in predicciones]
    promedio = sum(numeros) / len(numeros)
    minimo = min(numeros)
    maximo = max(numeros)
    
    print(f"\nEstadísticas de números:")
    print(f"  Promedio: {promedio:.0f}")
    print(f"  Mínimo:   {minimo:04d}")
    print(f"  Máximo:   {maximo:04d}")


def main():
    """Ejecuta todos los ejemplos."""
    print("\n" + "="*70)
    print("EJEMPLOS DE USO: BATCH PREDICTIONS")
    print("="*70)
    print("\nEste script demuestra diferentes formas de usar el sistema")
    print("de predicciones por lotes.\n")
    
    try:
        # Ejecutar ejemplos
        ejemplo_1_proximos_dias()
        input("\nPresiona Enter para continuar al siguiente ejemplo...")
        
        ejemplo_2_rango_fechas()
        input("\nPresiona Enter para continuar al siguiente ejemplo...")
        
        ejemplo_3_fechas_especificas()
        input("\nPresiona Enter para continuar al siguiente ejemplo...")
        
        ejemplo_4_todas_loterias()
        input("\nPresiona Enter para continuar al siguiente ejemplo...")
        
        ejemplo_5_guardar_json()
        input("\nPresiona Enter para continuar al siguiente ejemplo...")
        
        ejemplo_6_analisis_tendencias()
        
        print("\n" + "="*70)
        print("EJEMPLOS COMPLETADOS")
        print("="*70)
        print("\nPara más información, consulta: Docs/BATCH_PREDICTIONS.md")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nAsegúrate de entrenar los modelos primero:")
        print("  python main.py --train")
    
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
