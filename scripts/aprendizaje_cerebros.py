#!/usr/bin/env python3
"""
MODULO DE APRENDIZAJE - 7 CEREBROS
====================================
Proporciona datos de feedback_loop_metrics a los cerebros
Repo: Cuenta 2 (Pika77777/YouTube-ML-A-B-Testing-Pipeline)
"""
import os, json
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

def conectar():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def obtener_detonadores_efectivos(min_score=70):
    """Detonadores mas exitosos (score >= 70)"""
    sb = conectar()
    result = sb.table("feedback_loop_metrics").select(
        "detonadores_usados, score_exito"
    ).gte("score_exito", min_score).execute()

    detonadores = {}
    for row in result.data:
        dets = json.loads(row.get("detonadores_usados", "[]"))
        for d in dets:
            if d and d.strip():
                detonadores[d] = detonadores.get(d, 0) + 1

    return dict(sorted(detonadores.items(), key=lambda x: x[1], reverse=True))

def obtener_detonadores_inefectivos(max_score=50):
    """Detonadores fallidos (score <= 50)"""
    sb = conectar()
    result = sb.table("feedback_loop_metrics").select(
        "detonadores_usados, score_exito"
    ).lte("score_exito", max_score).execute()

    detonadores = {}
    for row in result.data:
        dets = json.loads(row.get("detonadores_usados", "[]"))
        for d in dets:
            if d and d.strip():
                detonadores[d] = detonadores.get(d, 0) + 1

    return dict(sorted(detonadores.items(), key=lambda x: x[1], reverse=True))

def obtener_mejores_titulos(limit=10):
    """Mejores titulos por CTR real"""
    sb = conectar()
    result = sb.table("feedback_loop_metrics").select(
        "titulo_usado, ctr_real, score_exito"
    ).not_.is_("ctr_real", "null").order("ctr_real", desc=True).limit(limit).execute()

    return [{
        "titulo": r.get("titulo_usado"),
        "ctr": r.get("ctr_real"),
        "score": r.get("score_exito")
    } for r in result.data]

def obtener_estadisticas_globales():
    """Metricas agregadas del canal"""
    sb = conectar()
    result = sb.table("feedback_loop_metrics").select("*").execute()

    if not result.data:
        return {"error": "No hay datos"}

    total = len(result.data)
    scores = [r["score_exito"] for r in result.data if r.get("score_exito")]
    ctrs = [r["ctr_real"] for r in result.data if r.get("ctr_real")]
    rets = [r["retention_real"] for r in result.data if r.get("retention_real")]
    vphs = [r["vph_real"] for r in result.data if r.get("vph_real")]

    return {
        "total_videos": total,
        "score_promedio": round(sum(scores) / len(scores), 2) if scores else 0,
        "ctr_promedio": round(sum(ctrs) / len(ctrs), 2) if ctrs else 0,
        "retention_promedio": round(sum(rets) / len(rets), 2) if rets else 0,
        "vph_promedio": int(sum(vphs) / len(vphs)) if vphs else 0,
        "videos_exitosos": sum(1 for s in scores if s >= 70),
        "videos_fallidos": sum(1 for s in scores if s < 50)
    }

def obtener_recomendaciones_nuevo_video():
    """Recomendaciones para generar nuevo video"""
    det_top = obtener_detonadores_efectivos(min_score=70)
    titulos = obtener_mejores_titulos(limit=5)
    stats = obtener_estadisticas_globales()

    return {
        "detonadores_recomendados": list(det_top.keys())[:5],
        "ejemplos_titulos_exitosos": [t["titulo"] for t in titulos],
        "ctr_objetivo": round(stats.get("ctr_promedio", 5) * 1.1, 2),
        "retention_objetivo": round(stats.get("retention_promedio", 40) * 1.1, 2),
        "vph_objetivo": int(stats.get("vph_promedio", 50) * 1.1)
    }

# Funciones especificas por cerebro
def aprendizaje_cerebro_creativo():
    """Datos para CEREBRO CREATIVO"""
    return {
        "detonadores_efectivos": obtener_detonadores_efectivos(min_score=70),
        "detonadores_evitar": obtener_detonadores_inefectivos(max_score=50),
        "ejemplos_titulos": obtener_mejores_titulos(limit=10)
    }

def aprendizaje_cerebro_evaluador():
    """Datos para CEREBRO EVALUADOR"""
    stats = obtener_estadisticas_globales()
    return {
        "ctr_promedio_canal": stats.get("ctr_promedio", 5),
        "retention_promedio_canal": stats.get("retention_promedio", 40),
        "score_minimo_aceptable": 60
    }

def aprendizaje_cerebro_predictor():
    """Datos para CEREBRO 4 ML PREDICTOR"""
    sb = conectar()
    result = sb.table("feedback_loop_metrics").select(
        "ctr_predicho, ctr_real, retention_predicha, retention_real, "
        "vph_predicho, vph_real"
    ).not_.is_("ctr_real", "null").execute()

    return {
        "total_datos": len(result.data),
        "datos": result.data,
        "recomendacion": "Reentrenar modelo con estos datos reales"
    }

if __name__ == "__main__":
    print("="*60)
    print("MODULO DE APRENDIZAJE - 7 CEREBROS")
    print("="*60)

    recoms = obtener_recomendaciones_nuevo_video()
    print(f"\nDetonadores recomendados: {recoms['detonadores_recomendados']}")
    print(f"CTR objetivo: {recoms['ctr_objetivo']}%")
    print(f"Retention objetivo: {recoms['retention_objetivo']}%")

    stats = obtener_estadisticas_globales()
    print(f"\nVideos analizados: {stats.get('total_videos', 0)}")
    print(f"Score promedio: {stats.get('score_promedio', 0)}/100")
    print(f"CTR promedio: {stats.get('ctr_promedio', 0)}%")

    print("\n" + "="*60)
    print("[OK] Modulo de aprendizaje listo")
