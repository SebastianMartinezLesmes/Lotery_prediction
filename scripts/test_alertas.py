"""
Script de prueba para el sistema de alertas.
Genera alertas de ejemplo para verificar el funcionamiento.
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.utils.alerts import AlertManager, check_model_performance


def main():
    """Genera alertas de prueba."""
    print("="*70)
    print("PRUEBA DEL SISTEMA DE ALERTAS")
    print("="*70)
    
    manager = AlertManager()
    
    print("\n1. Escenario: Accuracy normal (no genera alerta)")
    print("-" * 70)
    alert = manager.check_accuracy("ASTRO LUNA", "result", 0.75, 0.72)
    if not alert:
        print(">> OK: No se generó alerta (accuracy dentro del rango)")
    
    print("\n2. Escenario: Accuracy bajo - WARNING")
    print("-" * 70)
    alert = manager.check_accuracy("ASTRO SOL", "series", 0.58, 0.56)
    
    print("\n3. Escenario: Accuracy crítico - CRITICAL")
    print("-" * 70)
    alert = manager.check_accuracy("ASTRO LUNA", "result", 0.45, 0.42)
    
    print("\n4. Escenario: F1-score crítico")
    print("-" * 70)
    alert = manager.check_accuracy("ASTRO SOL", "series", 0.65, 0.40)
    
    print("\n5. Usando función de conveniencia")
    print("-" * 70)
    check_model_performance("ASTRO LUNA", "series", 0.55, 0.52)
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    print(f"Total de alertas generadas: {len(manager.alerts_history)}")
    print(f"Archivo de alertas: {manager.alert_file}")
    
    print("\nPara ver las alertas generadas, ejecuta:")
    print("  python scripts/ver_alertas.py")
    print("  python scripts/ver_alertas.py --report")
    print("="*70)


if __name__ == "__main__":
    main()
