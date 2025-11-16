#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CEREBRO 1: ENTRENAMIENTO DE PREFERENCIAS DE USUARIO
====================================================

Analiza aprobaciones/rechazos del usuario para actualizar patrones.
Este script se ejecuta SEMANALMENTE (no cada 6h).

FUNCIÓN:
- Analiza user_content_preferences
- Detecta patrones de títulos/descripciones aprobados vs rechazados
- Actualiza gui_training_context con nuevos patrones
- Gemini usa estos patrones en próximas generaciones

EJECUCIÓN:
- GitHub Actions: Domingos 5 AM UTC (semanal)
- Manual: python scripts/train_user_preferences.py
"""

import os
import json
from datetime import datetime, timedelta
from collections import Counter
from supabase import create_client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Conectar a Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] Faltan variables de entorno: SUPABASE_URL o SUPABASE_SERVICE_KEY")
    print("[INFO] Este script requiere acceso a Supabase para funcionar")
    exit(0)  # Exit code 0 = no error (solo advertencia)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("CEREBRO 1: ENTRENAMIENTO DE PREFERENCIAS DE USUARIO")
print("=" * 80)


def analyze_title_preferences(tipo_video=None):
    """Analiza preferencias de títulos (aprobados vs rechazados)"""
    print(f"\n[INFO] Analizando preferencias de títulos ({tipo_video or 'todos'})...")

    # Filtro por tipo de video
    query = sb.table("user_content_preferences")\
        .select("*")\
        .eq("content_type", "titulo")

    if tipo_video:
        query = query.eq("tipo_video", tipo_video)

    result = query.execute()

    if not result.data:
        print(f"[WARN] No hay datos de títulos para analizar")
        return {}

    aprobados = [item for item in result.data if item["user_action"] == "approved"]
    rechazados = [item for item in result.data if item["user_action"] == "rejected"]

    print(f"[OK] Títulos aprobados: {len(aprobados)}")
    print(f"[OK] Títulos rechazados: {len(rechazados)}")

    # Analizar features de títulos aprobados
    features_aprobados = []
    for item in aprobados:
        if item.get("features"):
            features_aprobados.append(item["features"])

    # Analizar features de títulos rechazados
    features_rechazados = []
    for item in rechazados:
        if item.get("features"):
            features_rechazados.append(item["features"])

    # Calcular patrones
    patrones = {
        "total_aprobados": len(aprobados),
        "total_rechazados": len(rechazados),
        "ratio_aprobacion": round(len(aprobados) / max(len(aprobados) + len(rechazados), 1) * 100, 1)
    }

    # Detectar patrones de APROBADOS
    if features_aprobados:
        # ¿Usan mayúsculas?
        usa_mayusculas = sum(1 for f in features_aprobados if f.get("tiene_mayusculas")) / len(features_aprobados)
        patrones["patron_mayusculas"] = {
            "frecuencia": round(usa_mayusculas * 100, 1),
            "recomendacion": "usar" if usa_mayusculas > 0.6 else "evitar"
        }

        # ¿Usan emojis?
        usa_emojis = sum(1 for f in features_aprobados if f.get("tiene_emojis")) / len(features_aprobados)
        patrones["patron_emojis"] = {
            "frecuencia": round(usa_emojis * 100, 1),
            "recomendacion": "usar" if usa_emojis > 0.5 else "opcional"
        }

        # ¿Usan números?
        usa_numeros = sum(1 for f in features_aprobados if f.get("tiene_numeros")) / len(features_aprobados)
        patrones["patron_numeros"] = {
            "frecuencia": round(usa_numeros * 100, 1),
            "recomendacion": "incluir" if usa_numeros > 0.5 else "opcional"
        }

        # ¿Usan año?
        usa_año = sum(1 for f in features_aprobados if f.get("tiene_año")) / len(features_aprobados)
        patrones["patron_año"] = {
            "frecuencia": round(usa_año * 100, 1),
            "recomendacion": "incluir 2025" if usa_año > 0.6 else "opcional"
        }

        # Palabras de impacto más usadas
        todas_palabras = []
        for f in features_aprobados:
            if f.get("palabras_impacto"):
                todas_palabras.extend(f["palabras_impacto"])

        if todas_palabras:
            contador = Counter(todas_palabras)
            patrones["palabras_impacto_top"] = contador.most_common(10)

        # Longitud promedio
        longitudes = [f.get("longitud", 0) for f in features_aprobados if f.get("longitud")]
        if longitudes:
            patrones["longitud_promedio"] = round(sum(longitudes) / len(longitudes), 1)
            patrones["longitud_recomendada"] = f"{min(longitudes)}-{max(longitudes)} caracteres"

    # Detectar patrones a EVITAR (rechazados)
    if features_rechazados:
        evitar = []

        # Si rechazados tienen más mayúsculas que aprobados
        usa_mayusculas_rechazados = sum(1 for f in features_rechazados if f.get("tiene_mayusculas")) / len(features_rechazados)
        if usa_mayusculas_rechazados > 0.7 and usa_mayusculas < 0.3:
            evitar.append("Evitar MAYÚSCULAS excesivas")

        # Si rechazados NO tienen emojis
        usa_emojis_rechazados = sum(1 for f in features_rechazados if f.get("tiene_emojis")) / len(features_rechazados)
        if usa_emojis_rechazados < 0.2 and usa_emojis > 0.6:
            evitar.append("Incluir emojis (rechazados no los tenían)")

        patrones["evitar"] = evitar

    return patrones


def analyze_description_preferences():
    """Analiza preferencias de descripciones"""
    print(f"\n[INFO] Analizando preferencias de descripciones...")

    result = sb.table("user_content_preferences")\
        .select("*")\
        .eq("content_type", "descripcion")\
        .execute()

    if not result.data:
        print(f"[WARN] No hay datos de descripciones")
        return {}

    aprobados = [item for item in result.data if item["user_action"] == "approved"]
    rechazados = [item for item in result.data if item["user_action"] == "rejected"]

    print(f"[OK] Descripciones aprobadas: {len(aprobados)}")
    print(f"[OK] Descripciones rechazadas: {len(rechazados)}")

    return {
        "total_aprobados": len(aprobados),
        "total_rechazados": len(rechazados),
        "ratio_aprobacion": round(len(aprobados) / max(len(aprobados) + len(rechazados), 1) * 100, 1)
    }


def update_training_context(patrones_largos, patrones_shorts, patrones_descripcion):
    """Actualiza gui_training_context con nuevos patrones"""
    print(f"\n[INFO] Actualizando gui_training_context con nuevos patrones...")

    try:
        # Obtener contexto actual
        current = sb.table("gui_training_context")\
            .select("*")\
            .eq("context_type", "main")\
            .eq("is_active", True)\
            .limit(1)\
            .execute()

        if not current.data:
            print("[ERROR] No se encontró contexto activo")
            return False

        current_patrones = current.data[0]["patrones"]
        if isinstance(current_patrones, str):
            current_patrones = json.loads(current_patrones)

        # Actualizar con nuevos patrones de usuario
        current_patrones["user_preferences"] = {
            "titulos_largos": patrones_largos,
            "titulos_shorts": patrones_shorts,
            "descripciones": patrones_descripcion,
            "ultima_actualizacion": datetime.now().isoformat(),
            "proxima_actualizacion": (datetime.now() + timedelta(days=7)).isoformat()
        }

        # Guardar actualización
        sb.table("gui_training_context")\
            .update({"patrones": current_patrones})\
            .eq("context_type", "main")\
            .eq("is_active", True)\
            .execute()

        print("[OK] Patrones actualizados exitosamente")
        return True

    except Exception as e:
        print(f"[ERROR] Error actualizando contexto: {e}")
        return False


def generar_reporte(patrones_largos, patrones_shorts, patrones_descripcion):
    """Genera reporte de entrenamiento"""
    print("\n" + "=" * 80)
    print("REPORTE DE ENTRENAMIENTO")
    print("=" * 80)

    print("\n[LARGOS] TITULOS VIDEOS LARGOS:")
    if patrones_largos:
        print(f"  • Total aprobados: {patrones_largos.get('total_aprobados', 0)}")
        print(f"  • Total rechazados: {patrones_largos.get('total_rechazados', 0)}")
        print(f"  • Ratio aprobación: {patrones_largos.get('ratio_aprobacion', 0):.1f}%")

        if patrones_largos.get("patron_mayusculas"):
            print(f"  • Mayúsculas: {patrones_largos['patron_mayusculas']['recomendacion']} ({patrones_largos['patron_mayusculas']['frecuencia']:.1f}%)")

        if patrones_largos.get("patron_emojis"):
            print(f"  • Emojis: {patrones_largos['patron_emojis']['recomendacion']} ({patrones_largos['patron_emojis']['frecuencia']:.1f}%)")

        if patrones_largos.get("palabras_impacto_top"):
            top_palabras = [p[0] for p in patrones_largos["palabras_impacto_top"][:5]]
            print(f"  • Palabras top: {', '.join(top_palabras)}")

        if patrones_largos.get("evitar"):
            print(f"  • Evitar: {', '.join(patrones_largos['evitar'])}")
    else:
        print("  (Sin datos suficientes)")

    print("\n[SHORTS] TITULOS SHORTS:")
    if patrones_shorts:
        print(f"  • Total aprobados: {patrones_shorts.get('total_aprobados', 0)}")
        print(f"  • Total rechazados: {patrones_shorts.get('total_rechazados', 0)}")
        print(f"  • Ratio aprobación: {patrones_shorts.get('ratio_aprobacion', 0):.1f}%")

        if patrones_shorts.get("palabras_impacto_top"):
            top_palabras = [p[0] for p in patrones_shorts["palabras_impacto_top"][:5]]
            print(f"  • Palabras top: {', '.join(top_palabras)}")
    else:
        print("  (Sin datos suficientes)")

    print("\n[DESCRIPCIONES] DESCRIPCIONES:")
    if patrones_descripcion:
        print(f"  • Total aprobadas: {patrones_descripcion.get('total_aprobados', 0)}")
        print(f"  • Ratio aprobación: {patrones_descripcion.get('ratio_aprobacion', 0):.1f}%")
    else:
        print("  (Sin datos suficientes)")

    print("\n" + "=" * 80)


def main():
    """Función principal de entrenamiento"""

    # 1. Analizar preferencias de títulos largos
    patrones_largos = analyze_title_preferences("largo")

    # 2. Analizar preferencias de títulos shorts
    patrones_shorts = analyze_title_preferences("short")

    # 3. Analizar preferencias de descripciones
    patrones_descripcion = analyze_description_preferences()

    # 4. Actualizar gui_training_context
    if patrones_largos or patrones_shorts or patrones_descripcion:
        success = update_training_context(patrones_largos, patrones_shorts, patrones_descripcion)

        if success:
            print("\n[SUCCESS] Entrenamiento completado exitosamente")
        else:
            print("\n[ERROR] Falló la actualización del contexto")
    else:
        print("\n[WARN] No hay suficientes datos para entrenar")
        print("[INFO] Esperando más aprobaciones/rechazos del usuario...")

    # 5. Generar reporte
    generar_reporte(patrones_largos, patrones_shorts, patrones_descripcion)

    print("\n[INFO] Próximo entrenamiento: en 7 días")
    print("=" * 80)


if __name__ == "__main__":
    main()
