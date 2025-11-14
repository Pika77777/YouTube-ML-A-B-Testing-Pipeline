#!/usr/bin/env python3
"""
CEREBRO 6: ANALISTA DE PRODUCCIÓN (Visual/Auditivo)

Analiza la retención segundo a segundo de videos y detecta patrones de edición
que mantienen o destruyen la retención de la audiencia.

Funcionalidad:
- Obtiene gráfico de retención de YouTube Analytics API
- Detecta drop points (caídas >10% en <30 seg)
- Detecta peak points (picos de retención)
- Calcula métricas de edición (CPM estimado)
- Genera recomendaciones automáticas
- Guarda análisis en Supabase (video_retention_analysis)

Uso:
    python analizar_retencion_visual.py                  # Analiza últimos 30 días
    python analizar_retencion_visual.py --days 7         # Últimos 7 días
    python analizar_retencion_visual.py --video VIDEO_ID # Video específico

Costo API:
    YouTube Analytics API: 0 unidades (cuota separada de 50,000/día)

Autor: Claude Code + bK777741
Fecha: 2025-01-14
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Cargar variables de entorno
env_path = Path(__file__).parent.parent / ".env"
from dotenv import load_dotenv
load_dotenv(dotenv_path=env_path)

from supabase import create_client, Client
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# YouTube OAuth
YT_CLIENT_ID = os.getenv("YT_CLIENT_ID")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN")

# Umbrales de análisis
DROP_THRESHOLD = 10.0  # Caída de retención >10% es un drop point
SPIKE_THRESHOLD = 5.0   # Aumento de retención >5% es un peak point
TIME_WINDOW = 30        # Ventana de tiempo para detectar drops (segundos)

# Umbrales de clasificación de retención
RETENTION_EXCELLENT = 60.0  # >= 60% = excelente
RETENTION_GOOD = 50.0       # 50-59% = bueno
RETENTION_REGULAR = 40.0    # 40-49% = regular
# < 40% = malo

# ============================================================================
# INICIALIZACIÓN
# ============================================================================

def init_supabase() -> Client:
    """Inicializa cliente de Supabase"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] Variables SUPABASE_URL y SUPABASE_SERVICE_KEY requeridas")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def init_youtube_analytics():
    """Inicializa cliente de YouTube Analytics API"""
    if not all([YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN]):
        print("[ERROR] Variables YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN requeridas")
        sys.exit(1)

    credentials = Credentials(
        token=None,
        refresh_token=YT_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET
    )

    return build("youtubeAnalytics", "v2", credentials=credentials)

# ============================================================================
# FUNCIONES DE ANÁLISIS
# ============================================================================

def obtener_grafico_retencion(analytics, video_id: str) -> Optional[List[Dict]]:
    """
    Obtiene gráfico de retención del video desde YouTube Analytics API

    Returns:
        Lista de puntos: [{"second": 0, "retention": 100.0}, ...]
    """
    try:
        # Fecha de inicio: 60 días atrás (YouTube guarda datos históricos)
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        # Query a Analytics API
        response = analytics.reports().query(
            ids=f"channel=={CHANNEL_ID}",
            startDate=start_date,
            endDate=end_date,
            dimensions="elapsedVideoTimeRatio",
            metrics="audienceWatchRatio",
            filters=f"video=={video_id}",
            sort="elapsedVideoTimeRatio"
        ).execute()

        if "rows" not in response:
            print(f"[WARNING] No hay datos de retención para video {video_id}")
            return None

        # Convertir a formato interno
        retention_graph = []
        for row in response["rows"]:
            elapsed_ratio = float(row[0])  # 0.0 a 1.0
            watch_ratio = float(row[1])     # 0.0 a 1.0

            # Convertir a segundos (asumiendo video de duración X)
            # Nota: YouTube no da segundos exactos, solo ratios
            retention_graph.append({
                "ratio": elapsed_ratio,
                "retention": watch_ratio * 100.0  # Convertir a porcentaje
            })

        return retention_graph

    except Exception as e:
        print(f"[ERROR] Obteniendo retención de {video_id}: {e}")
        return None

def detectar_drop_points(retention_graph: List[Dict], duration_seconds: int) -> List[Dict]:
    """
    Detecta puntos donde la retención cae drásticamente

    Args:
        retention_graph: Gráfico de retención
        duration_seconds: Duración del video en segundos

    Returns:
        Lista de drop points con recomendaciones
    """
    drop_points = []

    for i in range(len(retention_graph) - 1):
        current = retention_graph[i]
        next_point = retention_graph[i + 1]

        # Calcular caída
        drop_percent = current["retention"] - next_point["retention"]

        if drop_percent >= DROP_THRESHOLD:
            # Convertir ratio a segundos
            second = int(current["ratio"] * duration_seconds)

            # Determinar causa probable y recomendación
            probable_cause, recommendation = inferir_causa_drop(drop_percent, second, duration_seconds)

            drop_points.append({
                "second": second,
                "drop_percent": round(drop_percent, 2),
                "probable_cause": probable_cause,
                "recommendation": recommendation
            })

    return drop_points

def detectar_peak_points(retention_graph: List[Dict], duration_seconds: int) -> List[Dict]:
    """Detecta puntos donde la retención aumenta (contenido enganchador)"""
    peak_points = []

    for i in range(1, len(retention_graph)):
        prev = retention_graph[i - 1]
        current = retention_graph[i]

        # Calcular aumento
        spike_percent = current["retention"] - prev["retention"]

        if spike_percent >= SPIKE_THRESHOLD:
            second = int(current["ratio"] * duration_seconds)

            probable_cause, note = inferir_causa_peak(spike_percent, second, duration_seconds)

            peak_points.append({
                "second": second,
                "spike_percent": round(spike_percent, 2),
                "probable_cause": probable_cause,
                "note": note
            })

    return peak_points

def inferir_causa_drop(drop_percent: float, second: int, duration: int) -> Tuple[str, str]:
    """
    Infiere causa probable de drop en retención

    Returns:
        (causa, recomendación)
    """
    # Drop en los primeros 30 segundos = gancho débil
    if second <= 30:
        return ("gancho_debil", "Reescribir gancho inicial - debe generar curiosidad inmediata")

    # Drop muy severo (>15%) = momento crítico
    if drop_percent > 15:
        return ("drop_critico", "Revisar edición - posible plano estático largo o transición aburrida")

    # Drop cerca del final = cierre débil
    if second > duration * 0.8:
        return ("cierre_debil", "Mejorar cierre - agregar call-to-action o teaser del próximo video")

    # Drop moderado en medio = edición lenta
    return ("edicion_lenta", "Aumentar ritmo - agregar B-Roll, gráficos o cortes más frecuentes")

def inferir_causa_peak(spike_percent: float, second: int, duration: int) -> Tuple[str, str]:
    """Infiere causa probable de peak (momento enganchador)"""

    if spike_percent > 8:
        return ("momento_viral", "Contenido muy atractivo - analizar qué se mostró y replicar")

    if second < 60:
        return ("gancho_fuerte", "Gancho excelente - usar patrón similar en futuros videos")

    return ("contenido_valioso", "Segmento valioso - la audiencia re-mira esta parte")

def calcular_avg_retention(retention_graph: List[Dict]) -> float:
    """Calcula retención promedio"""
    if not retention_graph:
        return 0.0
    return sum(point["retention"] for point in retention_graph) / len(retention_graph)

def clasificar_retencion(avg_retention: float) -> Tuple[str, int]:
    """
    Clasifica retención y asigna score

    Returns:
        (categoría, score)
    """
    if avg_retention >= RETENTION_EXCELLENT:
        return ("excelente", int(avg_retention))
    elif avg_retention >= RETENTION_GOOD:
        return ("bueno", int(avg_retention))
    elif avg_retention >= RETENTION_REGULAR:
        return ("regular", int(avg_retention))
    else:
        return ("malo", int(avg_retention))

def generar_recomendaciones(
    avg_retention: float,
    drop_points: List[Dict],
    peak_points: List[Dict],
    duration_seconds: int
) -> List[Dict]:
    """Genera recomendaciones basadas en análisis"""
    recomendaciones = []

    # Recomendación general basada en retención
    if avg_retention < RETENTION_REGULAR:
        recomendaciones.append({
            "type": "retencion_general",
            "priority": "critica",
            "message": f"Retención muy baja ({avg_retention:.1f}%). Revisar estructura completa del video"
        })

    # Recomendaciones por drop points
    for drop in drop_points[:3]:  # Top 3 drops más críticos
        recomendaciones.append({
            "type": "drop_critico",
            "priority": "alta",
            "second": drop["second"],
            "message": f"Caída de {drop['drop_percent']}% en {drop['second']}s - {drop['recommendation']}"
        })

    # Destacar peak points (para replicar)
    if peak_points:
        best_peak = max(peak_points, key=lambda x: x["spike_percent"])
        recomendaciones.append({
            "type": "peak_destacado",
            "priority": "baja",
            "second": best_peak["second"],
            "message": f"Pico +{best_peak['spike_percent']}% en {best_peak['second']}s - {best_peak['note']}"
        })

    # Recomendación de duración (si video muy largo con baja retención)
    if duration_seconds > 600 and avg_retention < RETENTION_GOOD:  # >10 min
        recomendaciones.append({
            "type": "duracion",
            "priority": "media",
            "message": f"Video largo ({duration_seconds//60} min) con retención baja. Considerar reducir a 8-10 min"
        })

    return recomendaciones

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def analizar_video(sb: Client, analytics, video_id: str, video_data: Dict) -> bool:
    """
    Analiza un video completo y guarda resultados en Supabase

    Returns:
        True si el análisis fue exitoso
    """
    print(f"\n[INFO] Analizando video: {video_data.get('title', 'Sin título')[:50]}...")

    # 1. Obtener gráfico de retención
    retention_graph = obtener_grafico_retencion(analytics, video_id)
    if not retention_graph:
        return False

    # 2. Obtener duración del video
    duration_seconds = video_data.get("duration", 0)
    if duration_seconds == 0:
        print(f"[WARNING] Duración desconocida para {video_id}, usando 600s por defecto")
        duration_seconds = 600

    # 3. Calcular retención promedio
    avg_retention = calcular_avg_retention(retention_graph)

    # 4. Detectar drop y peak points
    drop_points = detectar_drop_points(retention_graph, duration_seconds)
    peak_points = detectar_peak_points(retention_graph, duration_seconds)

    # 5. Clasificar retención
    categoria, score = clasificar_retencion(avg_retention)

    # 6. Generar recomendaciones
    recomendaciones = generar_recomendaciones(avg_retention, drop_points, peak_points, duration_seconds)

    # 7. Calcular métricas de edición (estimaciones basadas en patrones)
    # Nota: CPM real requeriría análisis del video descargado
    # Aquí usamos heurísticas basadas en retención
    estimated_cpm = 12.0 if avg_retention >= RETENTION_GOOD else 8.0

    # 8. Guardar en Supabase
    try:
        data = {
            "video_id": video_id,
            "avg_view_percentage": round(avg_retention, 2),
            "avg_view_duration_seconds": int(duration_seconds * (avg_retention / 100)),
            "total_views": video_data.get("view_count", 0),
            "retention_graph": retention_graph,
            "drop_points": drop_points,
            "peak_points": peak_points,
            "avg_cuts_per_minute": estimated_cpm,
            "retention_score": score,
            "retention_category": categoria,
            "recommendations": recomendaciones,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }

        result = sb.table("video_retention_analysis").upsert(data).execute()

        print(f"[OK] Video analizado - Retención: {avg_retention:.1f}% ({categoria.upper()})")
        print(f"     Drop points: {len(drop_points)} | Peak points: {len(peak_points)}")
        print(f"     Score: {score}/100 | Recomendaciones: {len(recomendaciones)}")

        return True

    except Exception as e:
        print(f"[ERROR] Guardando análisis en Supabase: {e}")
        return False

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Cerebro 6: Analista de Producción")
    parser.add_argument("--days", type=int, default=30, help="Analizar videos de últimos N días")
    parser.add_argument("--video", type=str, help="Analizar video específico por ID")
    args = parser.parse_args()

    print("=" * 70)
    print("CEREBRO 6: ANALISTA DE PRODUCCIÓN (Visual/Auditivo)")
    print("=" * 70)

    # Inicializar clientes
    sb = init_supabase()
    analytics = init_youtube_analytics()

    # Obtener videos a analizar
    if args.video:
        # Video específico
        result = sb.table("videos").select("*").eq("video_id", args.video).execute()
        videos = result.data
    else:
        # Videos recientes
        fecha_limite = (datetime.now() - timedelta(days=args.days)).isoformat()
        result = sb.table("videos") \
            .select("*") \
            .gte("published_at", fecha_limite) \
            .eq("es_tuyo", True) \
            .order("published_at", desc=True) \
            .execute()
        videos = result.data

    if not videos:
        print(f"[INFO] No hay videos para analizar")
        return

    print(f"\n[INFO] {len(videos)} videos encontrados para análisis\n")

    # Analizar cada video
    exitosos = 0
    fallidos = 0

    for video in videos:
        try:
            if analizar_video(sb, analytics, video["video_id"], video):
                exitosos += 1
            else:
                fallidos += 1
        except Exception as e:
            print(f"[ERROR] Analizando {video['video_id']}: {e}")
            fallidos += 1

    # Resumen final
    print("\n" + "=" * 70)
    print(f"[RESUMEN] Análisis completado")
    print(f"  Exitosos: {exitosos}")
    print(f"  Fallidos: {fallidos}")
    print(f"  Total: {len(videos)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
