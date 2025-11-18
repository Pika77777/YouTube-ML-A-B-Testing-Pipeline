#!/usr/bin/env python3
"""
Generador de Títulos A/B usando Gemini AI
Genera 3 variantes optimizadas para CTR
"""
import os
import google.generativeai as genai


def generate_ab_titles(original_title, sb=None):
    """
    Genera 3 variantes de título optimizadas para A/B Testing

    Args:
        original_title: Título original del video
        sb: Cliente Supabase (opcional, para futuros análisis)

    Returns:
        dict con keys: variant_a, variant_b, variant_c
    """
    try:
        # Configurar Gemini AI
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Prompt optimizado para generar títulos virales
        prompt = f"""Genera 3 variantes MEJORADAS de este título de YouTube para maximizar CTR:

Título original: "{original_title}"

REQUISITOS ESTRICTOS:
1. Variante A (Curiosidad): Usa curiosidad, misterio, preguntas intrigantes
   - Ejemplos: "El SECRETO que...", "Lo que NADIE te dice sobre...", "¿Por qué..."

2. Variante B (Beneficio): Promete beneficio claro y resultado específico
   - Ejemplos: "Cómo [resultado] en X pasos", "La forma más rápida de...", "Aumenta X en Y%"

3. Variante C (Urgencia): Usa urgencia, escasez, números, fechas
   - Ejemplos: "AHORA: ...", "Solo HOY...", "7 formas de... (2025)", "ÚLTIMA OPORTUNIDAD"

REGLAS:
- Mantén la esencia del contenido original
- Máximo 70 caracteres por variante
- Usa MAYÚSCULAS estratégicamente (no todo en mayúsculas)
- Incluye números cuando sea posible
- Evita clickbait engañoso

Formato de respuesta (EXACTO):
A: [título variante A]
B: [título variante B]
C: [título variante C]"""

        # Generar contenido
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Parsear respuesta
        variants = {}
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('A:'):
                variants['variant_a'] = line.replace('A:', '').strip()
            elif line.startswith('B:'):
                variants['variant_b'] = line.replace('B:', '').strip()
            elif line.startswith('C:'):
                variants['variant_c'] = line.replace('C:', '').strip()

        # Validar que se generaron las 3 variantes
        if len(variants) != 3:
            raise ValueError(f"Se esperaban 3 variantes, se obtuvieron {len(variants)}")

        print(f"[GEMINI AI] Variantes generadas exitosamente para: {original_title[:50]}...")
        return variants

    except Exception as e:
        print(f"[ERROR] Error generando variantes con Gemini AI: {e}")

        # Fallback: Variantes basadas en templates
        print("[FALLBACK] Usando templates predefinidos")

        # Extraer palabras clave del título
        palabras = original_title.split()
        primera_palabra = palabras[0] if palabras else "Esto"

        return {
            'variant_a': f"El SECRETO de {original_title[:55]}",
            'variant_b': f"Cómo {original_title[:60]} (Paso a Paso)",
            'variant_c': f"🔥 {original_title[:60]} - 2025"
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
    print("\n" + "=" * 80)
