#!/usr/bin/env python3
"""
CEREBRO 7: CIENTÍFICO DE MINIATURAS (Psicología del Clic)

Analiza resultados de A/B testing de miniaturas y construye base de conocimiento
de patrones ganadores vs perdedores.

Funcionalidad:
- Obtiene resultados de A/B test de YouTube Analytics
- Identifica miniatura ganadora (mayor CTR)
- Analiza elementos visuales (opcional con Google Vision API)
- Actualiza patrones ganadores/perdedores en thumbnail_patterns
- Guarda resultados en Supabase (thumbnail_ab_testing)

Uso:
    python analizar_thumbnails_ab.py                  # Analiza todos los A/B tests pendientes
    python analizar_thumbnails_ab.py --video VIDEO_ID # Video específico
    python analizar_thumbnails_ab.py --use-vision     # Activar Google Vision API (PAGA)

Costo API:
    YouTube Analytics API: 0 unidades (cuota separada)
    Google Vision API: $0 (si no usas --use-vision) o $0.018/mes (si usas)

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

# Umbrales de clasificación de CTR
CTR_GANADOR = 8.0    # >= 8% = ganador
CTR_NEUTRAL_MIN = 5.0 # 5-8% = neutral
# < 5% = perdedor

# Tiempo mínimo de test (horas)
MIN_TEST_DURATION = 48  # 48 horas mínimo para tener datos confiables

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

def obtener_resultados_ab_youtube(analytics, video_id: str) -> Optional[Dict]:
    """
    Obtiene resultados de A/B test de miniaturas desde YouTube Analytics

    NOTA: YouTube no expone directamente A/B test de thumbnails en Analytics API.
    Esta función obtiene métricas generales (impressions, clicks, CTR).
    El A/B testing real se hace desde YouTube Studio web.

    Para implementación completa, necesitarías:
    1. Subir 3 miniaturas manualmente en YouTube Studio
    2. Activar A/B test desde YouTube Studio
    3. Después de 48-72h, YouTube elige ganadora automáticamente
    4. Este script lee el resultado final

    Returns:
        Dict con métricas del video, o None si no hay datos
    """
    try:
        # Fecha de inicio: últimos 7 días
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        # Query a Analytics API
        response = analytics.reports().query(
            ids=f"channel=={CHANNEL_ID}",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage",
            filters=f"video=={video_id}"
        ).execute()

        if "rows" not in response or len(response["rows"]) == 0:
            print(f"[WARNING] No hay datos de Analytics para video {video_id}")
            return None

        row = response["rows"][0]

        # Obtener CTR desde tabla video_monitoring (donde Cerebro 1 lo guarda)
        # Esto es temporal hasta que YouTube exponga A/B data directamente

        return {
            "views": int(row[0]),
            "estimated_minutes_watched": float(row[1]),
            "avg_view_duration": float(row[2]),
            "avg_view_percentage": float(row[3])
        }

    except Exception as e:
        print(f"[ERROR] Obteniendo datos de Analytics para {video_id}: {e}")
        return None

def obtener_datos_ab_desde_monitoring(sb: Client, video_id: str) -> Optional[Dict]:
    """
    Obtiene datos de A/B testing desde tabla video_monitoring
    (donde Cerebro 1 guarda resultados de A/B de títulos y CTR)

    Esto es un workaround hasta que YouTube exponga A/B de thumbnails en API
    """
    try:
        result = sb.table("video_monitoring") \
            .select("*") \
            .eq("video_id", video_id) \
            .eq("ab_test_uploaded", True) \
            .single() \
            .execute()

        if not result.data:
            return None

        data = result.data

        # Extraer métricas de checkpoints
        metrics = data.get("metrics", {})
        if not metrics:
            return None

        # Obtener CTR del último checkpoint
        latest_checkpoint = None
        for checkpoint in ["72h", "48h", "24h", "6h", "1h"]:
            if checkpoint in metrics:
                latest_checkpoint = metrics[checkpoint]
                break

        if not latest_checkpoint:
            return None

        return {
            "video_id": video_id,
            "ctr": latest_checkpoint.get("ctr", 0.0),
            "impressions": latest_checkpoint.get("impressions", 0),
            "clicks": latest_checkpoint.get("clicks", 0),
            "views": latest_checkpoint.get("views", 0),
            "vph": latest_checkpoint.get("vph", 0),
            "test_start": data.get("created_at"),
            "test_duration_hours": calcular_horas_desde(data.get("created_at"))
        }

    except Exception as e:
        print(f"[WARNING] No se encontraron datos de A/B para {video_id}: {e}")
        return None

def calcular_horas_desde(timestamp_str: str) -> int:
    """Calcula horas transcurridas desde un timestamp"""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - timestamp
        return int(delta.total_seconds() / 3600)
    except:
        return 0

def clasificar_ctr(ctr: float) -> str:
    """
    Clasifica CTR en categorías

    Returns:
        'ganador', 'neutral', o 'perdedor'
    """
    if ctr >= CTR_GANADOR:
        return "ganador"
    elif ctr >= CTR_NEUTRAL_MIN:
        return "neutral"
    else:
        return "perdedor"

def analizar_elementos_visuales_manual(video_title: str) -> Dict:
    """
    Análisis básico sin Google Vision API (GRATIS)

    Esto es un placeholder. En producción, el usuario debería:
    1. Marcar manualmente elementos de la miniatura en la GUI
    2. O usar Google Vision API (--use-vision flag)

    Por ahora, retorna estructura vacía
    """
    return {
        "method": "manual",
        "note": "Análisis visual requiere marcado manual o Google Vision API"
    }

def actualizar_patrones(sb: Client, pattern_type: str, pattern_value: str, ctr: float, video_id: str, video_title: str):
    """
    Actualiza o crea patrón en thumbnail_patterns

    Args:
        pattern_type: Tipo de patrón (emotion, text_length, etc)
        pattern_value: Valor del patrón (shock, 1_word, etc)
        ctr: CTR de este video
        video_id: ID del video
        video_title: Título del video (para example_thumbnails)
    """
    try:
        # Obtener patrón actual
        result = sb.table("thumbnail_patterns") \
            .select("*") \
            .eq("pattern_type", pattern_type) \
            .eq("pattern_value", pattern_value) \
            .execute()

        if result.data and len(result.data) > 0:
            # Actualizar patrón existente
            pattern = result.data[0]
            times_used = pattern["times_used"] + 1

            # Recalcular promedio
            old_avg = pattern["avg_ctr"] or 0.0
            new_avg = ((old_avg * (times_used - 1)) + ctr) / times_used

            # Actualizar min/max
            min_ctr = min(pattern.get("min_ctr", ctr), ctr)
            max_ctr = max(pattern.get("max_ctr", ctr), ctr)

            # Agregar ejemplo
            examples = pattern.get("example_thumbnails", [])
            if len(examples) < 5:  # Mantener máximo 5 ejemplos
                examples.append({
                    "video_id": video_id,
                    "ctr": ctr,
                    "title": video_title[:50]
                })

            # Clasificar según nuevo promedio
            performance = clasificar_ctr(new_avg)

            # Update
            sb.table("thumbnail_patterns").update({
                "times_used": times_used,
                "avg_ctr": round(new_avg, 2),
                "min_ctr": round(min_ctr, 2),
                "max_ctr": round(max_ctr, 2),
                "performance_category": performance,
                "example_thumbnails": examples,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", pattern["id"]).execute()

            print(f"   [OK] Patrón actualizado: {pattern_type}={pattern_value} (CTR promedio: {new_avg:.1f}%)")

        else:
            # Crear patrón nuevo
            performance = clasificar_ctr(ctr)

            sb.table("thumbnail_patterns").insert({
                "pattern_type": pattern_type,
                "pattern_value": pattern_value,
                "times_used": 1,
                "avg_ctr": round(ctr, 2),
                "min_ctr": round(ctr, 2),
                "max_ctr": round(ctr, 2),
                "performance_category": performance,
                "example_thumbnails": [{
                    "video_id": video_id,
                    "ctr": ctr,
                    "title": video_title[:50]
                }]
            }).execute()

            print(f"   [OK] Patrón creado: {pattern_type}={pattern_value} (CTR: {ctr:.1f}%)")

    except Exception as e:
        print(f"[ERROR] Actualizando patrón {pattern_type}={pattern_value}: {e}")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def analizar_thumbnail_ab(sb: Client, analytics, video_id: str, video_data: Dict, use_vision_api: bool = False) -> bool:
    """
    Analiza resultados de A/B testing de miniatura

    Returns:
        True si el análisis fue exitoso
    """
    print(f"\n[INFO] Analizando miniatura: {video_data.get('title', 'Sin título')[:50]}...")

    # 1. Obtener datos de A/B test
    ab_data = obtener_datos_ab_desde_monitoring(sb, video_id)
    if not ab_data:
        print(f"[WARNING] No hay datos de A/B test para {video_id}")
        return False

    # 2. Verificar duración mínima del test
    if ab_data["test_duration_hours"] < MIN_TEST_DURATION:
        print(f"[WARNING] Test muy reciente ({ab_data['test_duration_hours']}h < {MIN_TEST_DURATION}h). Esperar más datos")
        return False

    # 3. Obtener CTR
    ctr = ab_data.get("ctr", 0.0)
    if ctr == 0.0:
        print(f"[WARNING] CTR no disponible para {video_id}")
        return False

    # 4. Clasificar CTR
    performance = clasificar_ctr(ctr)

    # 5. Análisis visual (manual o con Vision API)
    thumbnail_analysis = None
    if use_vision_api:
        # TODO: Implementar Google Vision API
        print("[INFO] Google Vision API no implementado aún. Usar análisis manual")
        thumbnail_analysis = analizar_elementos_visuales_manual(video_data.get("title", ""))
    else:
        thumbnail_analysis = analizar_elementos_visuales_manual(video_data.get("title", ""))

    # 6. Guardar en Supabase
    try:
        data = {
            "video_id": video_id,
            "thumbnail_a_url": None,  # Usuario debe agregar manualmente
            "thumbnail_b_url": None,
            "thumbnail_c_url": None,
            "thumbnail_a_impressions": ab_data.get("impressions", 0),
            "thumbnail_a_clicks": ab_data.get("clicks", 0),
            "thumbnail_a_ctr": ctr,
            "winning_thumbnail": "A",  # Por defecto A (único disponible)
            "winning_ctr": ctr,
            "improvement_percent": 0.0,
            "thumbnail_a_analysis": thumbnail_analysis,
            "test_start_date": ab_data.get("test_start"),
            "test_end_date": datetime.now(timezone.utc).isoformat(),
            "test_duration_hours": ab_data["test_duration_hours"]
        }

        result = sb.table("thumbnail_ab_testing").upsert(data).execute()

        print(f"[OK] Miniatura analizada - CTR: {ctr:.1f}% ({performance.upper()})")

        # 7. Actualizar patrones (ejemplos básicos)
        # En producción, el usuario marcaría estos patrones en la GUI
        # Por ahora, actualizamos patrón genérico basado en CTR
        actualizar_patrones(sb, "ctr_range", f"{int(ctr//2)*2}-{int(ctr//2)*2+2}%", ctr, video_id, video_data.get("title", ""))

        return True

    except Exception as e:
        print(f"[ERROR] Guardando análisis de miniatura: {e}")
        return False

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Cerebro 7: Científico de Miniaturas")
    parser.add_argument("--video", type=str, help="Analizar video específico por ID")
    parser.add_argument("--use-vision", action="store_true", help="Usar Google Vision API (PAGA)")
    args = parser.parse_args()

    print("=" * 70)
    print("CEREBRO 7: CIENTÍFICO DE MINIATURAS (Psicología del Clic)")
    print("=" * 70)

    if args.use_vision:
        print("[WARNING] Google Vision API activado - Costo: $0.018/mes estimado")

    # Inicializar clientes
    sb = init_supabase()
    analytics = init_youtube_analytics()

    # Obtener videos con A/B test activo
    if args.video:
        # Video específico
        result = sb.table("videos").select("*").eq("video_id", args.video).execute()
        videos = result.data
    else:
        # Videos con A/B test hace >48h
        fecha_limite = (datetime.now() - timedelta(hours=MIN_TEST_DURATION)).isoformat()
        result = sb.table("video_monitoring") \
            .select("video_id") \
            .eq("ab_test_uploaded", True) \
            .lt("created_at", fecha_limite) \
            .execute()

        video_ids = [v["video_id"] for v in result.data]

        if not video_ids:
            print(f"\n[INFO] No hay videos con A/B test pendiente de análisis")
            return

        # Obtener datos completos de videos
        result = sb.table("videos").select("*").in_("video_id", video_ids).execute()
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
            if analizar_thumbnail_ab(sb, analytics, video["video_id"], video, args.use_vision):
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
