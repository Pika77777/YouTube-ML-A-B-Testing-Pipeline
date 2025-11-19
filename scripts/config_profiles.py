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
        "archive_after_hours": 168,             # Monitorear 7 días (SEO toma tiempo)
        "healthy_views_velocity": 5,            # 5+ vistas/hora = goteo SEO saludable
        "stagnant_views_velocity": 2,           # <2 vistas/hora + bajo CTR = problema
        "min_ctr_threshold": 3.5,               # CTR mínimo aceptable (%)
        "min_retention_threshold": 35,          # Retention mínimo (%)
        "alert_priority": "LOW",                # SEO es más paciente

        # NUEVO: Checkpoints específicos para evaluación (horas)
        "evaluation_checkpoints": [24, 48, 168],  # 24h, 48h, 7 días

        # NUEVO: Umbrales para diagnóstico de impresiones
        "impressions_low_threshold": 500,       # <500 impresiones = FANTASMA
        "impressions_normal_threshold": 2000,   # 500-2000 = Normal, >2000 = Alto
    },

    ChannelProfile.PROFILE_GROWTH: {
        # Viral-driven: Impacto inmediato o muerte
        "min_hours_before_alert": 3,            # Esperar 3h (viralidad muy rápida)
        "archive_after_hours": 24,              # Monitorear 24h (ventana viral)
        "healthy_views_velocity": 20,           # 20+ vistas/hora = viralidad
        "stagnant_views_velocity": 10,          # <10 vistas/hora = revisar
        "min_ctr_threshold": 4.0,               # CTR mínimo aceptable (%)
        "min_retention_threshold": 40,          # Retention mínimo (%)
        "alert_priority": "HIGH",               # Viralidad requiere acción rápida

        # NUEVO: Checkpoints específicos para evaluación (horas)
        "evaluation_checkpoints": [3, 6, 12, 24],  # 3h, 6h, 12h, 24h

        # NUEVO: Umbrales para diagnóstico de impresiones
        "impressions_low_threshold": 1000,      # <1000 impresiones = FANTASMA
        "impressions_normal_threshold": 5000,   # 1000-5000 = Normal, >5000 = Alto
    }
}


# ============================================================================
# VOCABULARIO PARA GENERACIÓN DE TÍTULOS
# ============================================================================

VOCABULARY_TECH = {
    "accion": [
        "Solucionar", "Reparar", "Restaurar", "Corregir", "Eliminar", "Quitar",
        "Potenciar", "Optimizar", "Acelerar", "Configurar", "Activar", "Desactivar",
        "Actualizar", "Migrar", "Instalar", "Desinstalar", "Recuperar", "Rescatar",
        "Arreglar", "Debugear", "Limpiar", "Boost", "Tunear", "Hackear",
        "Automatizar", "Simplificar", "Revertir", "Forzar"
    ],
    "seguridad": [
        "Sin Formatear", "Sin Perder Datos", "Método Seguro", "Reversible",
        "Sin Riesgos", "Respaldo Incluido", "Protegido", "Con Backup",
        "No Destructivo", "Safe Mode", "Modo Seguro", "Sin Root",
        "Sin Admin", "Sin Permisos", "Portable", "Sin Instalar",
        "Probado", "Confiable", "Sin Virus", "Limpio"
    ],
    "velocidad": [
        "Al Instante", "En 1 Minuto", "Rápido", "Express", "Ya", "En Segundos",
        "Inmediato", "Sin Espera", "Ultra Rápido", "Flash", "One-Click",
        "Automático", "En 3 Pasos", "En 5 Minutos", "Speedrun", "Turbo",
        "Sin Complicaciones", "Directo", "Fast", "Quick Fix"
    ],
    "autoridad": [
        "Definitivo", "Garantizado", "100% Efectivo", "Solución Final", "Método 2025",
        "Comprobado", "Oficial", "El Mejor", "Profesional", "Experto", "Advanced",
        "Pro", "Ultimate", "Master", "Premium", "Gold", "Certified",
        "Verificado", "Testeado", "Método Real", "Sin Fake", "Funciona 2025",
        "Actualizado", "Última Versión", "Nueva Forma"
    ]
}

VOCABULARY_GROWTH = {
    "dolor": [
        # Emociones Negativas
        "Vacío", "Soledad", "Fracaso", "Ansiedad", "Cansado", "Ignorado", "Perdido",
        "Estancado", "Débil", "Confundido", "Roto", "Deprimido", "Agotado", "Frustrado",
        # Estados Mentales
        "Pobreza Mental", "Mente Dispersa", "Sin Rumbo", "Bloqueado", "Atrapado",
        "Mediocre", "Invisible", "Inseguro", "Cobarde", "Conformista", "Víctima",
        # Situaciones
        "Sin Dinero", "Sin Propósito", "Sin Motivación", "Sin Energía", "Sin Amigos",
        "Procrastinando", "Comparándote", "Autosaboteándote", "Sufriendo en Silencio"
    ],
    "revelacion": [
        # Verdades Ocultas
        "La Verdad", "El Secreto", "Lo que nadie te dice", "La Mentira", "Despertar",
        "La Regla Oculta", "El Error", "La Trampa", "El Lado Oscuro", "La Realidad",
        # Descubrimientos
        "Lo que Descubrí", "El Patrón Oculto", "La Fórmula Prohibida", "El Método Secreto",
        "La Lección Oculta", "El Código", "La Clave", "El Truco Mental",
        # Contradicción
        "La Paradoja", "Lo Opuesto", "Al Revés", "La Ironía", "El Absurdo",
        "La Contradicción", "Lo que No Ves", "El Punto Ciego"
    ],
    "autoridad": [
        # Filosofía Antigua
        "Marco Aurelio", "Séneca", "Epicteto", "Los Estoicos", "Lección Antigua",
        "Sabiduría Japonesa", "El Monje", "Filosofía Milenaria", "Buda", "Lao Tzu",
        # Ciencia/Psicología
        "La Ciencia", "Neurociencia", "Psicología", "Estudios de Harvard", "Carl Jung",
        "Viktor Frankl", "La Investigación", "Los Expertos", "Datos Reales",
        # Modernos
        "Jordan Peterson", "Naval Ravikant", "James Clear", "Cal Newport", "Tim Ferriss",
        "Elon Musk", "Steve Jobs", "Bruce Lee", "Kobe Bryant", "David Goggins",
        # Cultural
        "Sabiduría Samurái", "Bushido", "Ikigai", "Kaizen", "Wabi-Sabi", "Miyamoto Musashi"
    ],
    "transformacion": [
        # Poder Mental
        "Invencible", "Imparable", "Inquebrantable", "Mente de Acero", "Frialdad",
        "Control Total", "Poder Mental", "Disciplina", "Resiliencia", "Antifragil",
        # Estados Deseados
        "Paz Mental", "Libertad", "Abundancia", "Plenitud", "Felicidad", "Éxito",
        "Victoria", "Triunfo", "Maestría", "Excelencia", "Grandeza", "Legado",
        # Cualidades
        "Enfoque Láser", "Claridad Mental", "Confianza Brutal", "Propósito Claro",
        "Energía Infinita", "Productividad Máxima", "Flow State", "Modo Dios",
        "Versión Superior", "Nivel Siguiente", "Transformación Total"
    ],
    "habitos": [
        # Rutinas/Tiempo
        "Rutina", "Mañana", "5 AM", "Noche", "Antes de Dormir", "Al Despertar",
        "Ritual Diario", "Sistema", "Protocolo", "Método", "Práctica",
        # Conceptos Psicológicos
        "Dopamina", "Cerebro", "Enfoque", "Atención", "Concentración", "Willpower",
        "Fuerza de Voluntad", "Mentalidad", "Mindset", "Identidad", "Creencias",
        # Acciones
        "Eliminar", "Construir", "Despertar", "Renunciar", "Soltar", "Dejar Ir",
        "Comenzar", "Parar", "Cambiar", "Romper", "Crear", "Destruir",
        # Mejora Continua
        "1%", "Kaizen", "Compounding", "Momentum", "Consistencia", "Disciplina Diaria",
        "Pequeños Pasos", "Micro Hábitos", "Hábitos Atómicos", "Progreso Invisible"
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
