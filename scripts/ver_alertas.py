"""
Script para visualizar y gestionar alertas del sistema.
Permite ver alertas recientes, filtrar por lotería y generar reportes.
"""
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict
from collections import Counter

from src.core.config import settings


def cargar_alertas() -> List[Dict]:
    """Carga las alertas desde el archivo JSON."""
    alert_file = settings.LOGS_DIR / "alerts.json"
    
    if not alert_file.exists():
        print(f"No se encontraron alertas en: {alert_file}")
        return []
    
    with open(alert_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def mostrar_alerta(alert: Dict, index: int = None) -> None:
    """Muestra una alerta de forma legible."""
    prefix = f"[{index}] " if index is not None else ""
    
    symbol = {
        "INFO": ">>",
        "WARNING": "!!",
        "CRITICAL": "ERROR"
    }.get(alert["level"], ">>")
    
    print(f"\n{prefix}{symbol} {alert['title']}")
    print(f"   Nivel: {alert['level']}")
    print(f"   Lotería: {alert['lottery']}")
    print(f"   Métrica: {alert['metric_name']}")
    print(f"   Valor: {alert['current_value']:.4f} (Umbral: {alert['threshold']:.4f})")
    print(f"   Fecha: {alert['timestamp']}")
    print(f"   Mensaje: {alert['message']}")


def mostrar_alertas_recientes(limit: int = 10) -> None:
    """Muestra las alertas más recientes."""
    alertas = cargar_alertas()
    
    if not alertas:
        return
    
    print(f"\n{'='*70}")
    print(f"ALERTAS RECIENTES (últimas {limit})")
    print('='*70)
    
    for i, alert in enumerate(alertas[-limit:], 1):
        mostrar_alerta(alert, i)
    
    print(f"\n{'='*70}")
    print(f"Total de alertas: {len(alertas)}")
    print('='*70)


def filtrar_por_loteria(lottery: str) -> None:
    """Filtra alertas por lotería."""
    alertas = cargar_alertas()
    
    if not alertas:
        return
    
    filtradas = [a for a in alertas if a['lottery'].lower() == lottery.lower()]
    
    print(f"\n{'='*70}")
    print(f"ALERTAS PARA: {lottery.upper()}")
    print('='*70)
    
    if not filtradas:
        print(f"\nNo se encontraron alertas para {lottery}")
        return
    
    for i, alert in enumerate(filtradas, 1):
        mostrar_alerta(alert, i)
    
    print(f"\n{'='*70}")
    print(f"Total: {len(filtradas)} alertas")
    print('='*70)


def filtrar_por_nivel(level: str) -> None:
    """Filtra alertas por nivel."""
    alertas = cargar_alertas()
    
    if not alertas:
        return
    
    filtradas = [a for a in alertas if a['level'].upper() == level.upper()]
    
    print(f"\n{'='*70}")
    print(f"ALERTAS DE NIVEL: {level.upper()}")
    print('='*70)
    
    if not filtradas:
        print(f"\nNo se encontraron alertas de nivel {level}")
        return
    
    for i, alert in enumerate(filtradas, 1):
        mostrar_alerta(alert, i)
    
    print(f"\n{'='*70}")
    print(f"Total: {len(filtradas)} alertas")
    print('='*70)


def filtrar_por_fecha(days: int = 7) -> None:
    """Filtra alertas de los últimos N días."""
    alertas = cargar_alertas()
    
    if not alertas:
        return
    
    fecha_limite = datetime.now() - timedelta(days=days)
    
    filtradas = [
        a for a in alertas
        if datetime.fromisoformat(a['timestamp']) >= fecha_limite
    ]
    
    print(f"\n{'='*70}")
    print(f"ALERTAS DE LOS ÚLTIMOS {days} DÍAS")
    print('='*70)
    
    if not filtradas:
        print(f"\nNo se encontraron alertas en los últimos {days} días")
        return
    
    for i, alert in enumerate(filtradas, 1):
        mostrar_alerta(alert, i)
    
    print(f"\n{'='*70}")
    print(f"Total: {len(filtradas)} alertas")
    print('='*70)


def generar_reporte() -> None:
    """Genera un reporte estadístico de las alertas."""
    alertas = cargar_alertas()
    
    if not alertas:
        return
    
    print(f"\n{'='*70}")
    print("REPORTE DE ALERTAS")
    print('='*70)
    
    # Estadísticas generales
    print(f"\nTotal de alertas: {len(alertas)}")
    
    # Por nivel
    niveles = Counter(a['level'] for a in alertas)
    print("\nPor nivel:")
    for nivel, count in niveles.most_common():
        porcentaje = (count / len(alertas)) * 100
        print(f"  {nivel:10} | {count:3} ({porcentaje:5.1f}%)")
    
    # Por lotería
    loterias = Counter(a['lottery'] for a in alertas)
    print("\nPor lotería:")
    for loteria, count in loterias.most_common():
        porcentaje = (count / len(alertas)) * 100
        print(f"  {loteria:15} | {count:3} ({porcentaje:5.1f}%)")
    
    # Por métrica
    metricas = Counter(a['metric_name'] for a in alertas)
    print("\nPor métrica:")
    for metrica, count in metricas.most_common():
        porcentaje = (count / len(alertas)) * 100
        print(f"  {metrica:20} | {count:3} ({porcentaje:5.1f}%)")
    
    # Alertas críticas
    criticas = [a for a in alertas if a['level'] == 'CRITICAL']
    if criticas:
        print(f"\n!! Alertas críticas: {len(criticas)}")
        print("   Requieren atención inmediata:")
        for alert in criticas[-5:]:  # Últimas 5
            print(f"   - {alert['lottery']}: {alert['metric_name']} = {alert['current_value']:.4f}")
    
    # Tendencia temporal
    if len(alertas) >= 2:
        primera = datetime.fromisoformat(alertas[0]['timestamp'])
        ultima = datetime.fromisoformat(alertas[-1]['timestamp'])
        dias = (ultima - primera).days + 1
        promedio_diario = len(alertas) / dias if dias > 0 else 0
        
        print(f"\nTendencia temporal:")
        print(f"  Primera alerta: {primera.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Última alerta:  {ultima.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Período: {dias} días")
        print(f"  Promedio: {promedio_diario:.1f} alertas/día")
    
    print(f"\n{'='*70}")


def limpiar_alertas(confirmar: bool = False) -> None:
    """Limpia el archivo de alertas."""
    alert_file = settings.LOGS_DIR / "alerts.json"
    
    if not alert_file.exists():
        print("No hay alertas para limpiar")
        return
    
    alertas = cargar_alertas()
    
    if not confirmar:
        print(f"\n!! Esta acción eliminará {len(alertas)} alertas")
        print("   Usa --confirm para confirmar la eliminación")
        return
    
    alert_file.unlink()
    print(f"\n✅ {len(alertas)} alertas eliminadas")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Visualizador de alertas del sistema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python scripts/ver_alertas.py                    # Ver últimas 10 alertas
  python scripts/ver_alertas.py --recent 20        # Ver últimas 20 alertas
  python scripts/ver_alertas.py --lottery "ASTRO LUNA"  # Filtrar por lotería
  python scripts/ver_alertas.py --level CRITICAL   # Solo alertas críticas
  python scripts/ver_alertas.py --days 7           # Últimos 7 días
  python scripts/ver_alertas.py --report           # Generar reporte
  python scripts/ver_alertas.py --clear --confirm  # Limpiar alertas
        """
    )
    
    parser.add_argument(
        '--recent',
        type=int,
        default=10,
        help='Número de alertas recientes a mostrar (default: 10)'
    )
    
    parser.add_argument(
        '--lottery',
        type=str,
        help='Filtrar por lotería específica'
    )
    
    parser.add_argument(
        '--level',
        type=str,
        choices=['INFO', 'WARNING', 'CRITICAL'],
        help='Filtrar por nivel de alerta'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        help='Filtrar alertas de los últimos N días'
    )
    
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generar reporte estadístico'
    )
    
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Limpiar todas las alertas'
    )
    
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Confirmar limpieza de alertas'
    )
    
    args = parser.parse_args()
    
    try:
        if args.clear:
            limpiar_alertas(args.confirm)
        elif args.report:
            generar_reporte()
        elif args.lottery:
            filtrar_por_loteria(args.lottery)
        elif args.level:
            filtrar_por_nivel(args.level)
        elif args.days:
            filtrar_por_fecha(args.days)
        else:
            mostrar_alertas_recientes(args.recent)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
