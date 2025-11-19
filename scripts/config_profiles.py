#!/usr/bin/env python3
"""
CONFIGURACIÓN DE PERFILES MULTI-NICHO
Router que detecta el tipo de canal y asigna estrategia
"""
import os
from enum import Enum

class ChannelProfile(Enum):
    """Perfiles de canal soportados"""
    PROFILE_TECH = "tech"        # Tutoriales, SEO, Soluciones
    PROFILE_GROWTH = "growth"    # Estoicismo, Motivación, Hábitos
    PROFILE_UNKNOWN = "unknown"  # Fallback


# ============================================================================
# MAPEO DE CANALES A PERFILES
# ============================================================================

# OPCIÓN 1: Por CHANNEL_ID (si tienes múltiples canales)
CHANNEL_PROFILES = {
    # Agregar tus channel_ids aquí
    # "UC1234567890TECH": ChannelProfile.PROFILE_TECH,
    # "UC0987654321GROWTH": ChannelProfile.PROFILE_GROWTH,
}

# OPCIÓN 2: Por KEYWORDS en el título del video (fallback si no conoces channel_id)
KEYWORDS_TECH = [
    "tutorial", "solucionar", "reparar", "instalar", "configurar",
    "windows", "linux", "android", "error", "problema", "bug",
    "pc", "software", "app", "código", "programar", "hack",
    "chatgpt", "ia", "gemini"
]

KEYWORDS_GROWTH = [
    "estoicismo", "marco aurelio", "séneca", "disciplina", "hábitos",
    "mentalidad", "motivación", "productividad", "mañana", "rutina",
    "psicología", "filosofía", "sabiduría", "autocontrol", "enfoque",
    "ansiedad", "fracaso", "éxito", "transformación", "dopamina"
]


# ============================================================================
# CONFIGURACIÓN DE UMBRALES POR PERFIL
# ============================================================================

PROFILE_CONFIG = {
    ChannelProfile.PROFILE_TECH: {
        # SEO-driven: Tráfico de búsqueda lento pero constante
        "min_hours_before_alert": 12,           # Esperar 12h para indexación
        "archive_after_hours": 48,              # Monitorear 48h (2 días)
        "healthy_views_velocity": 5,            # 5+ vistas/hora = goteo SEO saludable
        "stagnant_views_velocity": 2,           # <2 vistas/hora + bajo CTR = problema
        "min_ctr_threshold": 3.5,               # CTR mínimo aceptable (%)
        "min_retention_threshold": 35,          # Retention mínimo (%)
        "alert_priority": "LOW",                # SEO es más paciente
    },

    ChannelProfile.PROFILE_GROWTH: {
        # Viral-driven: Impacto inmediato o muerte
        "min_hours_before_alert": 6,            # Esperar 6h (viralidad rápida)
        "archive_after_hours": 24,              # Monitorear 24h (1 día)
        "healthy_views_velocity": 20,           # 20+ vistas/hora = viralidad
        "stagnant_views_velocity": 10,          # <10 vistas/hora = revisar
        "min_ctr_threshold": 4.0,               # CTR mínimo aceptable (%)
        "min_retention_threshold": 40,          # Retention mínimo (%)
        "alert_priority": "HIGH",               # Viralidad requiere acción rápida
    }
}


# ============================================================================
# VOCABULARIO PARA GENERACIÓN DE TÍTULOS
# ============================================================================

VOCABULARY_TECH = {
    "accion": [
        "Solucionar", "Reparar", "Restaurar", "Corregir", "Eliminar",
        "Quitar", "Potenciar", "Optimizar", "Acelerar", "Configurar"
    ],
    "seguridad": [
        "Sin Formatear", "Sin Perder Datos", "Método Seguro",
        "Reversible", "Sin Riesgos", "Respaldo Incluido", "Protegido"
    ],
    "velocidad": [
        "Al Instante", "En 1 Minuto", "Rápido", "Express", "Ya",
        "En Segundos", "Inmediato", "Sin Espera"
    ],
    "autoridad": [
        "Definitivo", "Garantizado", "100% Efectivo", "Solución Final",
        "Método 2025", "Comprobado", "Oficial", "El Mejor"
    ]
}

VOCABULARY_GROWTH = {
    "dolor": [
        "Vacío", "Soledad", "Fracaso", "Ansiedad", "Cansado",
        "Ignorado", "Pobreza Mental", "Estancado", "Débil", "Perdido"
    ],
    "revelacion": [
        "La Verdad", "El Secreto", "Lo que nadie te dice", "La Mentira",
        "Despertar", "La Regla Oculta", "El Error", "La Trampa"
    ],
    "autoridad": [
        "Marco Aurelio", "Séneca", "Lección Antigua", "Sabiduría Japonesa",
        "El Monje", "La Ciencia", "Los Estoicos", "Filosofía Milenaria"
    ],
    "transformacion": [
        "Invencible", "Control Total", "Mente de Acero", "Frialdad",
        "Disciplina", "Imparable", "Inquebrantable", "Poder Mental"
    ],
    "habitos": [
        "Rutina", "Mañana", "5 AM", "Dopamina", "Cerebro", "Enfoque",
        "1%", "Eliminar", "Construir", "Despertar"
    ]
}


# ============================================================================
# FUNCIONES DE DETECCIÓN
# ============================================================================

def get_channel_profile(video_data) -> ChannelProfile:
    """
    Detecta el perfil del canal basado en channel_id o título

    Args:
        video_data: Dict con keys 'channel_id' y 'title'

    Returns:
        ChannelProfile enum
    """
    # Método 1: Por CHANNEL_ID
    channel_id = video_data.get('channel_id')
    if channel_id and channel_id in CHANNEL_PROFILES:
        return CHANNEL_PROFILES[channel_id]

    # Método 2: Por KEYWORDS en el título (fallback)
    title = video_data.get('title', '').lower()

    tech_score = sum(1 for kw in KEYWORDS_TECH if kw in title)
    growth_score = sum(1 for kw in KEYWORDS_GROWTH if kw in title)

    if tech_score > growth_score:
        return ChannelProfile.PROFILE_TECH
    elif growth_score > tech_score:
        return ChannelProfile.PROFILE_GROWTH

    # Método 3: Por variable de entorno (si solo manejas un canal)
    default_profile = os.getenv('DEFAULT_CHANNEL_PROFILE', 'tech')
    if default_profile.lower() == 'growth':
        return ChannelProfile.PROFILE_GROWTH

    # Fallback: Asumir TECH
    return ChannelProfile.PROFILE_TECH


def get_profile_config(profile: ChannelProfile) -> dict:
    """
    Obtiene la configuración de umbrales para un perfil

    Args:
        profile: ChannelProfile enum

    Returns:
        Dict con configuración de umbrales
    """
    return PROFILE_CONFIG.get(profile, PROFILE_CONFIG[ChannelProfile.PROFILE_TECH])


def get_vocabulary(profile: ChannelProfile) -> dict:
    """
    Obtiene el vocabulario para generación de títulos

    Args:
        profile: ChannelProfile enum

    Returns:
        Dict con vocabulario específico del perfil
    """
    if profile == ChannelProfile.PROFILE_TECH:
        return VOCABULARY_TECH
    elif profile == ChannelProfile.PROFILE_GROWTH:
        return VOCABULARY_GROWTH

    return VOCABULARY_TECH  # Fallback
