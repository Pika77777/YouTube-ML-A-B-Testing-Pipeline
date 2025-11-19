#!/usr/bin/env python3
"""
Generador de Títulos A/B Multi-Nicho usando Gemini AI
Genera 3 variantes optimizadas según el perfil del canal (TECH vs GROWTH)
"""
import os
import random
import google.generativeai as genai
from config_profiles import (
    get_channel_profile,
    get_vocabulary,
    ChannelProfile
)


def build_prompt_tech(original_title, vocabulary):
    """Construye el prompt para canal TECH (SEO/Autoridad)"""
    accion = random.choice(vocabulary['accion'])
    seguridad = random.choice(vocabulary['seguridad'])
    velocidad = random.choice(vocabulary['velocidad'])
    autoridad = random.choice(vocabulary['autoridad'])

    year = 2025

    prompt = f"""Actúa como Experto SEO Técnico especializado en tutoriales y soluciones de software.

Genera 3 variantes MEJORADAS de este título para maximizar CTR en audiencia técnica:

Título original: "{original_title}"

BANCO DE VOCABULARIO (Variar siempre):
- Acción: {accion}, Solucionar, Reparar, Restaurar, Corregir, Eliminar, Quitar, Potenciar
- Seguridad: {seguridad}, Sin Formatear, Sin Perder Datos, Método Seguro, Reversible
- Velocidad: {velocidad}, Al Instante, En 1 Minuto, Rápido, Express
- Autoridad: {autoridad}, Definitivo, Garantizado, 100% Efectivo, Método {year}

LAS 3 VARIANTES OBLIGATORIAS:

Variante A (Autoridad SEO):
- Estructura: [Palabra Clave] + [Acción] + [Promesa de Autoridad]
- Ejemplo: "Windows 11: Solucionar Error X - Método Definitivo 2025"
- Enfoque: Posicionamiento en búsqueda, keywords claras

Variante B (Dolor/Seguridad):
- Estructura: ¿[Problema]? + [Solución] + [Gancho de Seguridad]
- Ejemplo: "¿Error al Iniciar Windows? Repáralo Sin Formatear (Reversible)"
- Enfoque: Resolver dolor específico con promesa de seguridad

Variante C (Velocidad/Impacto):
- Estructura: ¡[Resultado]! + [Contexto] + [Tiempo]
- Ejemplo: "¡PC Lenta? Acelérala al Instante - 3 Pasos Rápidos"
- Enfoque: Resultado inmediato, rapidez

REGLAS ESTRICTAS:
- Máximo 70 caracteres por variante
- Incluye números cuando sea posible (pasos, tiempo, versiones)
- Usa MAYÚSCULAS estratégicamente (1-2 palabras máximo)
- Mantén keywords principales del título original
- Evita clickbait engañoso
- Enfoque: SEO, autoridad, solución técnica

Formato de respuesta (EXACTO):
A: [título variante A]
B: [título variante B]
C: [título variante C]"""

    return prompt


def build_prompt_growth(original_title, vocabulary):
    """Construye el prompt para canal GROWTH (Emocional/Viral)"""
    dolor = random.choice(vocabulary['dolor'])
    revelacion = random.choice(vocabulary['revelacion'])
    autoridad = random.choice(vocabulary['autoridad'])
    transformacion = random.choice(vocabulary['transformacion'])
    habito = random.choice(vocabulary['habitos'])

    prompt = f"""Actúa como Experto en Psicología Viral y Estoicismo.

Primero, clasifica el tema en: Filosófico, Práctico (Hábitos) o Emocional.

Genera 3 variantes MEJORADAS de este título para maximizar CTR emocional/viral:

Título original: "{original_title}"

BANCO DE VOCABULARIO (Variar siempre):
- Dolor: {dolor}, Vacío, Soledad, Fracaso, Ansiedad, Cansado, Ignorado, Estancado
- Revelación: {revelacion}, La Verdad, El Secreto, Lo que nadie te dice, La Mentira
- Autoridad: {autoridad}, Marco Aurelio, Séneca, Sabiduría Japonesa, El Monje, La Ciencia
- Transformación: {transformacion}, Invencible, Control Total, Mente de Acero, Disciplina
- Hábitos: {habito}, Rutina, Mañana, 5 AM, Dopamina, Cerebro, Enfoque, Eliminar

LAS 3 VARIANTES OBLIGATORIAS:

Variante A (El Dolor/Negativa):
- Estructura: Por esto sigues siendo [Adjetivo Negativo] (Y cómo evitarlo)
- Ejemplo: "Por esto sigues siendo Débil (Y cómo cambiarlo en Silencio)"
- Enfoque: Confrontar el dolor, identificar el problema emocional

Variante B (La Autoridad/Sabiduría):
- Estructura: La Regla de [Filósofo/Ciencia] que cambiará tu [Beneficio]
- Ejemplo: "La Regla de Marco Aurelio que Transformó mi Mañana"
- Enfoque: Lección antigua, sabiduría probada, autoridad histórica

Variante C (El Hábito/Lista):
- Estructura: X Cosas que debes [Acción] en Silencio
- Ejemplo: "7 Hábitos que Eliminé para Ser Imparable (Dopamina Controlada)"
- Enfoque: Pasos concretos, lista numerada, transformación práctica

REGLAS ESTRICTAS:
- Máximo 70 caracteres por variante
- Usa lenguaje emocional FUERTE (no tibio)
- Prioriza impacto emocional sobre SEO
- Usa números impares (3, 5, 7) en listas
- Paréntesis para detalles impactantes: (Y cómo...), (Sin que nadie...)
- Evita clichés: "cambiar tu vida", "ser exitoso" (usa específicos)

Formato de respuesta (EXACTO):
A: [título variante A]
B: [título variante B]
C: [título variante C]"""

    return prompt


def generate_ab_titles(original_title, video_data=None, sb=None):
    """
    Genera 3 variantes de título optimizadas según el perfil del canal

    Args:
        original_title: Título original del video
        video_data: Dict con 'channel_id' y 'title' (para detectar perfil)
        sb: Cliente Supabase (opcional)

    Returns:
        dict con keys: variant_a, variant_b, variant_c, profile
    """
    try:
        # 1. DETECTAR PERFIL DEL CANAL
        if video_data is None:
            video_data = {'title': original_title}

        profile = get_channel_profile(video_data)
        vocabulary = get_vocabulary(profile)

        print(f"[PROFILE] Detectado: {profile.value.upper()}")

        # 2. CONSTRUIR PROMPT SEGÚN PERFIL
        if profile == ChannelProfile.PROFILE_TECH:
            prompt = build_prompt_tech(original_title, vocabulary)
        elif profile == ChannelProfile.PROFILE_GROWTH:
            prompt = build_prompt_growth(original_title, vocabulary)
        else:
            # Fallback a TECH
            prompt = build_prompt_tech(original_title, vocabulary)

        # 3. LLAMAR A GEMINI AI
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-1.5-flash')

        response = model.generate_content(prompt)
        text = response.text.strip()

        # 4. PARSEAR RESPUESTA
        variants = {}
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('A:'):
                variants['variant_a'] = line.replace('A:', '').strip()
            elif line.startswith('B:'):
                variants['variant_b'] = line.replace('B:', '').strip()
            elif line.startswith('C:'):
                variants['variant_c'] = line.replace('C:', '').strip()

        # 5. VALIDAR RESPUESTA
        if len(variants) != 3:
            raise ValueError(f"Se esperaban 3 variantes, se obtuvieron {len(variants)}")

        # 6. AGREGAR METADATOS
        variants['profile'] = profile.value

        print(f"[GEMINI AI] Variantes {profile.value.upper()} generadas: {original_title[:40]}...")
        return variants

    except Exception as e:
        print(f"[ERROR] Error generando variantes con Gemini AI: {e}")

        # FALLBACK: Templates predefinidos según perfil
        profile = get_channel_profile(video_data) if video_data else ChannelProfile.PROFILE_TECH
        print(f"[FALLBACK] Usando templates {profile.value.upper()} predefinidos")

        if profile == ChannelProfile.PROFILE_TECH:
            return {
                'variant_a': f"{original_title[:50]} - Solución Definitiva 2025",
                'variant_b': f"¿{original_title[:45]}? Repáralo Sin Formatear",
                'variant_c': f"¡{original_title[:45]}! Al Instante - 3 Pasos",
                'profile': profile.value
            }
        elif profile == ChannelProfile.PROFILE_GROWTH:
            return {
                'variant_a': f"Por esto sigues {original_title[:45]} (Cámbialo)",
                'variant_b': f"La Regla Estoica de {original_title[:40]}",
                'variant_c': f"7 Cosas para {original_title[:45]} en Silencio",
                'profile': profile.value
            }

        # Fallback genérico
        return {
            'variant_a': f"El SECRETO de {original_title[:50]}",
            'variant_b': f"Cómo {original_title[:55]} (Paso a Paso)",
            'variant_c': f"🔥 {original_title[:55]} - 2025",
            'profile': 'unknown'
        }


if __name__ == "__main__":
    # Test del módulo
    test_title = "Soluciona el Error 0xc00007b en Windows 10"

    print("=" * 80)
    print(f"GENERANDO VARIANTES A/B PARA:")
    print(f"  Original: {test_title}")
    print("=" * 80)

    variants = generate_ab_titles(test_title)

    print(f"\n✅ VARIANTES GENERADAS:\n")
    print(f"  A (Curiosidad): {variants['variant_a']}")
    print(f"  B (Beneficio):  {variants['variant_b']}")
    print(f"  C (Urgencia):   {variants['variant_c']}")
    print(f"  Perfil: {variants.get('profile', 'unknown').upper()}")
    print("\n" + "=" * 80)
