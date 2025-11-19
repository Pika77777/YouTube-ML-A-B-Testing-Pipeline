#!/usr/bin/env python3
"""
Monitor de Metricas de Videos + Aprendizaje Automatico MULTI-NICHO
Trackea metricas en checkpoints: 1h, 6h, 24h, 48h, 72h + Monitoreo extendido: 7d, 15d, 30d
Obtiene CTR desde YouTube Analytics API
Aprende de metricas reales (Stage 2 Learning)
NUEVO: Alertas inteligentes según perfil del canal (TECH vs GROWTH)
Detecta "sleeper hits" (videos que explotan tarde)
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config_profiles import (
    get_channel_profile,
    get_profile_config,
    ChannelProfile
)

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

def get_youtube_analytics_service():
    """Crea servicio de YouTube Analytics API con OAuth"""
    try:
        creds = Credentials(
            token=None,
            refresh_token=os.getenv("YT_REFRESH_TOKEN"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("YT_CLIENT_ID"),
            client_secret=os.getenv("YT_CLIENT_SECRET"),
            scopes=['https://www.googleapis.com/auth/yt-analytics.readonly']
        )

        # Refresh token si es necesario
        if creds.expired or not creds.valid:
            creds.refresh(Request())

        return build('youtubeAnalytics', 'v2', credentials=creds)
    except Exception as e:
        print(f"[ERROR] No se pudo crear servicio Analytics: {e}")
        return None

def get_video_analytics(video_id, published_date):
    """
    Obtiene métricas completas del video desde YouTube Analytics API
    INCLUYE: CTR, Retention, Traffic Sources
    CONSUMO API: 0 unidades (Analytics API tiene cuota separada de 50,000/dia)
    """
    try:
        analytics = get_youtube_analytics_service()
        if not analytics:
            print(f"[WARN] Analytics API no disponible para {video_id}")
            return None

        # Fechas para el query (desde publicacion hasta hoy)
        start_date = published_date.strftime('%Y-%m-%d')
        end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # Query 1: Métricas generales (CTR, Retention, IMPRESIONES)
        response = analytics.reports().query(
            ids='channel==MINE',
            startDate=start_date,
            endDate=end_date,
            metrics='views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,cardImpressions,cardClickRate',
            dimensions='video',
            filters=f'video=={video_id}'
        ).execute()

        metrics = {}

        if response.get('rows'):
            row = response['rows'][0]
            metrics['views'] = row[0] if len(row) > 0 else None
            metrics['retention'] = row[3] if len(row) > 3 else None  # averageViewPercentage
            metrics['avg_view_duration'] = row[2] if len(row) > 2 else None
            metrics['impressions'] = row[5] if len(row) > 5 else None  # NUEVO: Impresiones
            metrics['ctr'] = row[6] if len(row) > 6 else None
            print(f"[ANALYTICS] {video_id}: Impresiones={metrics.get('impressions')} CTR={metrics.get('ctr')}% Retention={metrics.get('retention')}%")

        # Query 2: Traffic Sources (para saber si problema es título o miniatura)
        try:
            traffic_response = analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='views,estimatedMinutesWatched',
                dimensions='insightTrafficSourceType',
                filters=f'video=={video_id}',
                sort='-views'
            ).execute()

            if traffic_response.get('rows'):
                traffic_sources = {}
                total_views = sum(row[0] for row in traffic_response['rows'])

                for row in traffic_response['rows']:
                    source_type = row[0]
                    views = row[1]
                    percentage = (views / total_views * 100) if total_views > 0 else 0
                    traffic_sources[source_type] = {
                        'views': views,
                        'percentage': percentage
                    }

                metrics['traffic_sources'] = traffic_sources
                print(f"[TRAFFIC] Top source: {list(traffic_sources.keys())[0] if traffic_sources else 'None'}")

        except Exception as e:
            print(f"[WARN] No se pudieron obtener traffic sources: {e}")
            metrics['traffic_sources'] = {}

        return metrics if metrics else None

    except Exception as e:
        print(f"[ERROR] Error obteniendo analytics: {e}")
        return None

def diagnose_root_cause(impressions, ctr, retention, views, profile, config):
    """
    MATRIZ DE DIAGNÓSTICO DE CAUSA RAÍZ
    Determina QUÉ está fallando (Título, Miniatura o Coherencia)

    Args:
        impressions: int - Número de impresiones del video
        ctr: float - Click-Through Rate (%)
        retention: float - Retention promedio (%)
        views: int - Número de vistas
        profile: ChannelProfile enum
        config: dict - Configuración del perfil

    Returns:
        dict con:
        - syndrome: str - FANTASMA, INVISIBLE, CLICKBAIT, SUCCESS
        - culprit: str - TITULO, MINIATURA, COHERENCIA, NINGUNO
        - impressions_level: str - Baja, Normal, Alta
        - reason: str - Explicación técnica
        - action: str - Acción recomendada específica por perfil
    """
    min_ctr = config['min_ctr_threshold']
    min_retention = config['min_retention_threshold']
    imp_low = config['impressions_low_threshold']
    imp_normal = config['impressions_normal_threshold']

    # Clasificar impresiones
    if impressions is None:
        impressions_level = "Desconocido"
    elif impressions < imp_low:
        impressions_level = "Baja"
    elif impressions < imp_normal:
        impressions_level = "Normal"
    else:
        impressions_level = "Alta"

    # ========================================================================
    # CASO A: SÍNDROME DEL "FANTASMA" (Bajas Impresiones)
    # ========================================================================
    if impressions and impressions < imp_low:
        if profile == ChannelProfile.PROFILE_TECH:
            return {
                "syndrome": "FANTASMA",
                "culprit": "TITULO",
                "impressions_level": impressions_level,
                "reason": f"YouTube NO está mostrando el video ({impressions} impresiones < {imp_low}). El algoritmo no sabe de qué trata o no encuentra audiencia.",
                "action": "Reescribir Título enfocándose en KEYWORDS más buscadas (nombre del software, versión, error específico, solución). Agregar números de error exactos. Ejemplo: 'Solucionar Error 0xc00007b Windows 11 - Método 2025'"
            }
        elif profile == ChannelProfile.PROFILE_GROWTH:
            return {
                "syndrome": "FANTASMA",
                "culprit": "TITULO",
                "impressions_level": impressions_level,
                "reason": f"YouTube NO está mostrando el video ({impressions} impresiones < {imp_low}). El tema no interesa o el ángulo es muy aburrido.",
                "action": "Cambiar Título a algo más RADICAL/POLÉMICO/EMOCIONAL. Usar dolor específico + promesa clara. Ejemplo: 'Por esto sigues Fracasando (El Error que Nadie Ve)' o 'La Verdad sobre la Disciplina que te Ocultan'"
            }
        else:
            return {
                "syndrome": "FANTASMA",
                "culprit": "TITULO",
                "impressions_level": impressions_level,
                "reason": f"Bajas impresiones ({impressions} < {imp_low}). Problema de visibilidad SEO.",
                "action": "Mejorar título con keywords más específicas y relevantes para tu audiencia."
            }

    # ========================================================================
    # CASO B: SÍNDROME DEL "INVISIBLE" (Altas Impresiones + Bajo CTR)
    # ========================================================================
    if impressions and impressions >= imp_normal and ctr is not None and ctr < min_ctr:
        if profile == ChannelProfile.PROFILE_TECH:
            return {
                "syndrome": "INVISIBLE",
                "culprit": "MINIATURA",
                "impressions_level": impressions_level,
                "reason": f"YouTube muestra el video a muchas personas ({impressions} impresiones) pero nadie hace clic (CTR {ctr:.1f}% < {min_ctr}%). La imagen no detiene el scroll.",
                "action": "MANTÉN EL TÍTULO (está bien posicionado). Cambia la MINIATURA: Simplificar texto (máx 3 palabras), hacer zoom en el error o resultado final, usar colores de CONTRASTE (Rojo/Verde/Amarillo), agregar flecha señalando el problema."
            }
        elif profile == ChannelProfile.PROFILE_GROWTH:
            return {
                "syndrome": "INVISIBLE",
                "culprit": "MINIATURA",
                "impressions_level": impressions_level,
                "reason": f"YouTube muestra el video masivamente ({impressions} impresiones) pero nadie entra (CTR {ctr:.1f}% < {min_ctr}%). La imagen es genérica/aburrida.",
                "action": "MANTÉN EL TÍTULO (está funcionando). Cambia la MINIATURA: Usar expresión facial MÁS INTENSA (sorpresa, enojo, determinación), aumentar contraste brutal, texto emocional corto ('STOP', 'NADIE LO SABE', 'CUIDADO'), fondo oscuro con luz dramática."
            }
        else:
            return {
                "syndrome": "INVISIBLE",
                "culprit": "MINIATURA",
                "impressions_level": impressions_level,
                "reason": f"Alto alcance ({impressions} impresiones) pero bajo CTR ({ctr:.1f}%). Problema visual.",
                "action": "Mantén el título. Rediseña la miniatura con mayor contraste y simplicidad visual."
            }

    # ========================================================================
    # CASO C: SÍNDROME DEL "CLICKBAIT FALLIDO" (Alto CTR + Baja Retention)
    # ========================================================================
    if ctr is not None and ctr >= min_ctr and retention is not None and retention < min_retention:
        return {
            "syndrome": "CLICKBAIT",
            "culprit": "COHERENCIA",
            "impressions_level": impressions_level,
            "reason": f"La gente entra mucho (CTR {ctr:.1f}%) pero se va rápido (Retention {retention:.1f}% < {min_retention}%). El título/miniatura prometieron algo que el video NO entrega al inicio.",
            "action": "NO CAMBIES la miniatura (funciona). NO CAMBIES el título (funciona). PROBLEMA: Los primeros 30 segundos del video. Acción: 1) Entregar la promesa EN LOS PRIMEROS 10 SEGUNDOS, 2) Editar descripción explicando exactamente QUÉ encontrarán, 3) Poner comentario fijado con timestamp del contenido prometido."
        }

    # ========================================================================
    # CASO D: TODO BIEN (Éxito)
    # ========================================================================
    if ctr is not None and ctr >= min_ctr and (retention is None or retention >= min_retention):
        return {
            "syndrome": "SUCCESS",
            "culprit": "NINGUNO",
            "impressions_level": impressions_level,
            "reason": f"Video funcionando correctamente. CTR {ctr:.1f}% (>= {min_ctr}%)" + (f", Retention {retention:.1f}% (>= {min_retention}%)" if retention else ""),
            "action": "Continuar monitoreando. El título y miniatura están optimizados."
        }

    # ========================================================================
    # CASO E: DATOS INSUFICIENTES
    # ========================================================================
    return {
        "syndrome": "INSUFFICIENT_DATA",
        "culprit": "DESCONOCIDO",
        "impressions_level": impressions_level,
        "reason": "Datos insuficientes para diagnóstico completo. Esperar más tiempo para acumular métricas.",
        "action": "Continuar monitoreo en próximos checkpoints."
    }

def check_video_health(video_data, metrics, hours_online, profile, config):
    """
    LÓGICA DE ALERTAS MULTI-NICHO
    Evalúa la salud del video según el perfil del canal (TECH vs GROWTH)

    Args:
        video_data: Dict con datos del video (title, video_id, published_at)
        metrics: Dict con métricas actuales (views, ctr, retention, vph)
        hours_online: Float con horas desde publicación
        profile: ChannelProfile enum (TECH, GROWTH, UNKNOWN)
        config: Dict con configuración del perfil

    Returns:
        Tuple (status, message, priority)
        - status: str - Estado del video (WAITING_INDEXING, HEALTHY_SEO_DRIP, VIRAL_SUCCESS, ALERT_STAGNANT, etc)
        - message: str - Mensaje descriptivo
        - priority: str - Nivel de prioridad (INFO, SUCCESS, MEDIUM, HIGH)
    """
    views = metrics.get('views', 0)
    ctr = metrics.get('ctr')
    retention = metrics.get('retention')
    vph = metrics.get('vph', 0)

    # ========================================================================
    # REGLA UNIVERSAL: ZONA DE SILENCIO
    # ========================================================================
    min_hours = config['min_hours_before_alert']
    if hours_online < min_hours:
        return (
            "WAITING_INDEXING",
            f"Video en indexación... Esperar {min_hours}h antes de evaluar ({hours_online:.1f}h transcurridas)",
            "INFO"
        )

    # ========================================================================
    # REGLA UNIVERSAL: ARCHIVO DESPUÉS DEL LÍMITE
    # ========================================================================
    archive_hours = config['archive_after_hours']
    if hours_online > archive_hours:
        return (
            "ARCHIVED",
            f"Monitoreo completado ({hours_online:.1f}h > {archive_hours}h)",
            "INFO"
        )

    # ========================================================================
    # LÓGICA ESPECÍFICA PARA TECH (SEO/Goteo Paciente)
    # ========================================================================
    if profile == ChannelProfile.PROFILE_TECH:
        healthy_velocity = config['healthy_views_velocity']
        stagnant_velocity = config['stagnant_views_velocity']
        min_ctr = config['min_ctr_threshold']
        min_retention = config['min_retention_threshold']

        # CASO 1: Goteo SEO Saludable
        if vph >= healthy_velocity:
            return (
                "HEALTHY_SEO_DRIP",
                f"Goteo SEO saludable ({vph} VPH >= {healthy_velocity} VPH objetivo)",
                "SUCCESS"
            )

        # CASO 2: Video Estancado (CTR bajo + VPH bajo)
        if vph < stagnant_velocity and ctr is not None and ctr < min_ctr:
            return (
                "ALERT_STAGNANT",
                f"Video estancado: VPH {vph} < {stagnant_velocity}, CTR {ctr:.1f}% < {min_ctr}%. Considera mejorar SEO (título, tags, descripción)",
                "MEDIUM"
            )

        # CASO 3: CTR bajo pero VPH aceptable (problema de indexación)
        if ctr is not None and ctr < min_ctr and vph >= stagnant_velocity:
            return (
                "ALERT_LOW_CTR_SEO",
                f"CTR bajo ({ctr:.1f}% < {min_ctr}%) pero VPH aceptable ({vph} VPH). Optimizar título/miniatura sin urgencia",
                "MEDIUM"
            )

        # CASO 4: Retention baja (contenido malo)
        if retention is not None and retention < min_retention:
            return (
                "ALERT_LOW_RETENTION",
                f"Retention baja ({retention:.1f}% < {min_retention}%). Problema: contenido del video, no título",
                "MEDIUM"
            )

        # CASO 5: Todo bien (monitoreo continuo)
        return (
            "MONITORING_SEO",
            f"Monitoreo SEO activo: VPH {vph}, CTR {ctr:.1f}% si disponible" if ctr else f"Monitoreo SEO activo: VPH {vph}",
            "INFO"
        )

    # ========================================================================
    # LÓGICA ESPECÍFICA PARA GROWTH (Viral/Impacto Inmediato)
    # ========================================================================
    elif profile == ChannelProfile.PROFILE_GROWTH:
        healthy_velocity = config['healthy_views_velocity']
        stagnant_velocity = config['stagnant_views_velocity']
        min_ctr = config['min_ctr_threshold']
        min_retention = config['min_retention_threshold']

        # CASO 1: VIRALIDAD DETECTADA
        if vph >= healthy_velocity:
            return (
                "VIRAL_SUCCESS",
                f"🚀 VIRAL! Video explotando: {vph} VPH >= {healthy_velocity} VPH objetivo",
                "SUCCESS"
            )

        # CASO 2: CTR CRÍTICO (Título urgente)
        if ctr is not None and ctr < min_ctr and hours_online >= 6:
            return (
                "ALERT_LOW_CTR_URGENT",
                f"⚠️ CTR CRÍTICO: {ctr:.1f}% < {min_ctr}%. CAMBIAR TÍTULO YA (ventana viral cerrándose)",
                "HIGH"
            )

        # CASO 3: Clickbait Mismatch (título bueno pero video malo)
        if retention is not None and retention < min_retention and ctr is not None and ctr >= min_ctr:
            return (
                "ALERT_CLICKBAIT_MISMATCH",
                f"Título bueno (CTR {ctr:.1f}%) pero video malo (Retention {retention:.1f}% < {min_retention}%). Problema: contenido, no título",
                "HIGH"
            )

        # CASO 4: Video Estancado (VPH bajo)
        if vph < stagnant_velocity and hours_online >= 6:
            return (
                "ALERT_STAGNANT_VIRAL",
                f"Video no viral: VPH {vph} < {stagnant_velocity}. Revisar título + miniatura URGENTE",
                "HIGH"
            )

        # CASO 5: Monitoreo activo (esperando viralidad)
        return (
            "MONITORING_VIRAL",
            f"Esperando viralidad: VPH {vph}, CTR {ctr:.1f}%" if ctr else f"Esperando viralidad: VPH {vph}",
            "INFO"
        )

    # ========================================================================
    # FALLBACK (PROFILE_UNKNOWN)
    # ========================================================================
    else:
        # Usar lógica genérica (basada en TECH)
        if vph >= 20:
            return ("MONITORING_OK", f"Video estable: {vph} VPH", "SUCCESS")
        elif vph < 10:
            return ("ALERT_LOW_PERFORMANCE", f"VPH bajo: {vph}. Revisar título/miniatura", "MEDIUM")
        else:
            return ("MONITORING_NEUTRAL", f"Monitoreo activo: {vph} VPH", "INFO")

def send_email(subject, body):
    """Envia email usando SMTP"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg['From'] = os.getenv("SMTP_USER")
        msg['To'] = os.getenv("NOTIFICATION_EMAIL")
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            server.send_message(msg)

        print(f"[EMAIL] {subject}")
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo enviar email: {e}")
        return False

def save_learning_data(sb, video, analytics_data, vph, views, checkpoint):
    """
    Guarda datos de aprendizaje en user_preferences (Stage 2 Learning)
    Aprende de metricas reales de YouTube
    INCLUYE: Análisis de retention + traffic sources para determinar QUÉ falla
    INCLUYE: Métricas de evolución en checkpoints extendidos (7d, 15d, 30d)
    """
    try:
        ctr = analytics_data.get('ctr') if analytics_data else None
        retention = analytics_data.get('retention') if analytics_data else None
        traffic_sources = analytics_data.get('traffic_sources', {}) if analytics_data else {}

        # Obtener métricas históricas para checkpoints extendidos
        metrics_history = json.loads(video.get('metrics', '{}') or '{}')
        ctr_day3 = metrics_history.get('checkpoint_72h', {}).get('ctr')
        vph_day3 = metrics_history.get('checkpoint_72h', {}).get('vph')

        # ANÁLISIS INTELIGENTE: ¿Qué está fallando? (título vs miniatura)
        problem_source = "unknown"

        if ctr is not None and ctr < 5.0:
            # CTR BAJO - Determinar si problema es título o miniatura

            # HEURÍSTICA 1: Retention alta + CTR bajo = MINIATURA mala (NO título)
            if retention and retention > 40:
                problem_source = "thumbnail"
                print(f"[DIAGNOSIS] CTR bajo ({ctr:.1f}%) pero retention alta ({retention:.1f}%) → PROBLEMA: MINIATURA")
                print(f"[SKIP LEARNING] NO se aprende del título (está bien, problema es miniatura)")
                return None  # NO aprender del título

            # HEURÍSTICA 2: Traffic sources - De dónde viene el tráfico
            if traffic_sources:
                top_source = max(traffic_sources.items(), key=lambda x: x[1]['percentage'])[0]

                # YT_SEARCH = vienen de búsqueda (título es importante)
                if top_source == 'YT_SEARCH':
                    problem_source = "title"
                    print(f"[DIAGNOSIS] Tráfico principal: BÚSQUEDA → PROBLEMA: TÍTULO")

                # BROWSE_FEATURES = vienen de inicio/recomendados (miniatura es importante)
                elif top_source in ['BROWSE', 'BROWSE_FEATURES', 'RELATED_VIDEO']:
                    problem_source = "thumbnail"
                    print(f"[DIAGNOSIS] Tráfico principal: {top_source} → PROBLEMA: MINIATURA")
                    print(f"[SKIP LEARNING] NO se aprende del título")
                    return None  # NO aprender del título

            # HEURÍSTICA 3: Retention baja + CTR bajo = AMBOS malos
            if retention and retention < 30:
                problem_source = "both"
                print(f"[DIAGNOSIS] CTR bajo ({ctr:.1f}%) + retention baja ({retention:.1f}%) → PROBLEMA: TÍTULO + MINIATURA")

            # Si no hay datos suficientes para determinar, no aprender
            if problem_source == "unknown" and not retention:
                print(f"[SKIP LEARNING] CTR bajo pero no hay datos de retention/traffic para determinar causa")
                return None

        # CLASIFICAR TÍTULO basado en métricas
        user_action = None
        reason = None
        success_pattern = "immediate"  # Por defecto

        # DETECTAR EXPLOSIÓN TARDÍA en checkpoints extendidos
        if checkpoint in ["checkpoint_7d", "checkpoint_15d", "checkpoint_30d"]:
            if ctr_day3 and ctr and ctr >= ctr_day3 * 1.5:
                # CTR aumentó 50%+ desde día 3 → EXPLOSIÓN TARDÍA
                user_action = 'approved'
                reason = f'delayed_explosion_ctr_{ctr:.1f}%_from_{ctr_day3:.1f}%_{checkpoint}'
                problem_source = "none"
                success_pattern = "delayed_explosion"
                print(f"[LEARNING] EXPLOSIÓN TARDÍA detectada: CTR {ctr_day3:.1f}% → {ctr:.1f}% (+{(ctr/ctr_day3-1)*100:.0f}%)")
            elif vph_day3 and vph >= vph_day3 * 2:
                # VPH duplicó desde día 3 → EXPLOSIÓN TARDÍA
                user_action = 'approved'
                reason = f'delayed_explosion_vph_{vph}_from_{vph_day3}_{checkpoint}'
                problem_source = "none"
                success_pattern = "delayed_explosion"
                print(f"[LEARNING] EXPLOSIÓN TARDÍA detectada: VPH {vph_day3} → {vph} (+{(vph/vph_day3-1)*100:.0f}%)")

        # Si no hubo explosión tardía, evaluar normalmente
        if user_action is None:
            if ctr is not None and ctr >= 8.0:
                # CTR >= 8% = EXCELENTE (título ganador)
                user_action = 'approved'
                reason = f'ctr_excelente_{ctr:.1f}%'
                problem_source = "none"

            elif ctr is not None and ctr >= 5.0:
                # CTR 5-8% = BUENO (título aceptable)
                user_action = 'approved'
                reason = f'ctr_bueno_{ctr:.1f}%'
                problem_source = "none"

            elif ctr is not None and ctr < 5.0 and problem_source == "title":
                # CTR < 5% Y problema confirmado es el TÍTULO
                user_action = 'rejected'
                reason = f'ctr_bajo_{ctr:.1f}%_problema_titulo'

            elif ctr is not None and ctr < 5.0 and problem_source == "both":
                # CTR < 5% Y problema es TÍTULO + MINIATURA
                user_action = 'rejected'
                reason = f'ctr_bajo_{ctr:.1f}%_problema_titulo_y_miniatura'

            elif vph >= 100:
                # Sin CTR pero VPH alto = titulo probablemente bueno
                user_action = 'approved'
                reason = f'vph_alto_{vph}'
                problem_source = "none"

            elif vph < 25:
                # VPH bajo = titulo probablemente malo
                user_action = 'rejected'
                reason = f'vph_bajo_{vph}'
                problem_source = "title"
            else:
                # Neutro o problema es solo miniatura, no guardar
                return None

        # Guardar en user_preferences con diagnóstico completo + métricas de evolución
        sb.table("user_preferences").insert({
            "content_type": "titulo",
            "original_content": video['title_original'],
            "user_action": user_action,
            "metadata": {
                "ctr": ctr,
                "retention": retention,
                "vph": vph,
                "views": views,
                "checkpoint": checkpoint,
                "reason": reason,
                "problem_source": problem_source,
                "traffic_sources": traffic_sources,
                "video_id": video['video_id'],
                "published_at": video['published_at'],
                "learning_source": "stage2_metrics",
                "success_pattern": success_pattern,
                # Métricas de evolución (para checkpoints extendidos)
                "evolution": {
                    "ctr_day3": ctr_day3,
                    "ctr_current": ctr,
                    "vph_day3": vph_day3,
                    "vph_current": vph,
                    "growth_percentage_ctr": ((ctr / ctr_day3 - 1) * 100) if ctr_day3 and ctr else None,
                    "growth_percentage_vph": ((vph / vph_day3 - 1) * 100) if vph_day3 and vph else None
                } if checkpoint in ["checkpoint_7d", "checkpoint_15d", "checkpoint_30d"] else None
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        print(f"[LEARNING] {user_action.upper()}: '{video['title_original'][:50]}...' ({reason})")
        print(f"           Diagnóstico: problema_source={problem_source}")
        return user_action

    except Exception as e:
        print(f"[ERROR] Error guardando learning data: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_new_title_variants(original_title, sb):
    """
    Genera nuevas variantes de titulo usando Gemini
    CONSUMO API: ~500 tokens (input) + ~200 tokens (output) = 0.0007 unidades Gemini
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        prompt = f"""Genera 3 variantes MEJORADAS de este título de YouTube que tiene CTR bajo (<5%):

Título original: "{original_title}"

REQUISITOS:
1. Variante A (Curiosidad): Usa curiosidad, misterio, "secreto", "oculto"
2. Variante B (Beneficio): Promete beneficio claro, "cómo", resultado específico
3. Variante C (Urgencia): Usa urgencia, "AHORA", "YA", números

Formato de respuesta (EXACTO):
A: [título variante A]
B: [título variante B]
C: [título variante C]"""

        response = model.generate_content(prompt)
        text = response.text.strip()

        # Parsear respuesta
        variants = {}
        for line in text.split('\n'):
            if line.startswith('A:'):
                variants['variant_a'] = line.replace('A:', '').strip()
            elif line.startswith('B:'):
                variants['variant_b'] = line.replace('B:', '').strip()
            elif line.startswith('C:'):
                variants['variant_c'] = line.replace('C:', '').strip()

        return variants if len(variants) == 3 else {
            'variant_a': f"DESCUBRE: {original_title}",
            'variant_b': f"Cómo {original_title.lower()} (Tutorial PASO a PASO)",
            'variant_c': f"{original_title} - ¡HAZLO AHORA!"
        }

    except Exception as e:
        print(f"[ERROR] Error generando variantes: {e}")
        # Fallback a variantes simples
        return {
            'variant_a': f"El SECRETO de {original_title}",
            'variant_b': f"Cómo {original_title.lower()} FÁCIL",
            'variant_c': f"{original_title} - TUTORIAL 2025"
        }

def send_alert_email(video, analytics_data, vph, views, new_variants, problem_source="title"):
    """Envia email de ALERTA cuando CTR < 5% con diagnóstico de QUÉ falla"""
    ctr = analytics_data.get('ctr') if analytics_data else None
    retention = analytics_data.get('retention') if analytics_data else None

    subject = f"🚨 ALERTA: CTR BAJO ({ctr:.1f}%) - {video['title_original'][:40]}..."

    # Mensaje específico según qué está fallando
    if problem_source == "title":
        problem_msg = "⚠️ PROBLEMA DETECTADO: <strong>TÍTULO</strong>"
        action_msg = "Cambia el TÍTULO del video en YouTube Studio"
        color = "#dc2626"
    elif problem_source == "thumbnail":
        problem_msg = "⚠️ PROBLEMA DETECTADO: <strong>MINIATURA</strong>"
        action_msg = "Cambia la MINIATURA del video en YouTube Studio (el título está bien)"
        color = "#ea580c"
    elif problem_source == "both":
        problem_msg = "⚠️ PROBLEMA DETECTADO: <strong>TÍTULO + MINIATURA</strong>"
        action_msg = "Cambia AMBOS: título Y miniatura en YouTube Studio"
        color = "#b91c1c"
    else:
        problem_msg = "⚠️ PROBLEMA: No se pudo determinar la causa exacta"
        action_msg = "Revisa manualmente título y miniatura"
        color = "#6b7280"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <div style="background: {color}; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="margin: 0;">🚨 ALERTA: CTR CRÍTICO</h2>
            <p style="font-size: 18px; margin: 10px 0 0 0;">{problem_msg}</p>
        </div>

        <h3 style="color: #dc2626;">Título Actual (RECHAZADO):</h3>
        <p style="background: #fee2e2; padding: 15px; border-radius: 5px; border-left: 4px solid #dc2626;">
            {video['title_original']}
        </p>

        <h3 style="color: #ea580c;">Métricas Actuales:</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr style="background: #fee2e2;">
                <td style="padding: 10px; border: 1px solid #fca5a5;"><strong>CTR</strong></td>
                <td style="padding: 10px; border: 1px solid #fca5a5; color: #dc2626; font-weight: bold;">{ctr:.1f}% (< 5% es CRÍTICO)</td>
            </tr>
            {f'''<tr style="background: {'#dcfce7' if retention and retention > 40 else '#fee2e2' if retention and retention < 30 else '#f3f4f6'};">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Retention (Retención)</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold; color: {'#16a34a' if retention and retention > 40 else '#dc2626' if retention and retention < 30 else '#6b7280'};">{retention:.1f}%</td>
            </tr>''' if retention else ''}
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>VPH</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{vph:,}</td>
            </tr>
            <tr style="background: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Vistas</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{views:,}</td>
            </tr>
        </table>

        <div style="background: #fef3c7; padding: 15px; border-left: 4px solid #f59e0b; margin-bottom: 20px;">
            <p style="margin: 0;"><strong>📊 DIAGNÓSTICO AUTOMÁTICO:</strong></p>
            <p style="margin: 5px 0 0 0;">{action_msg}</p>
        </div>

        <h3 style="color: #16a34a;">Nuevos Títulos Sugeridos (A/B Testing):</h3>
        <ul style="list-style: none; padding: 0;">
            <li style="margin: 10px 0; padding: 15px; background: #fef3c7; border-radius: 5px; border-left: 4px solid #f59e0b;">
                <strong>Variante A (Curiosidad):</strong><br>
                <span style="font-size: 16px;">{new_variants['variant_a']}</span>
            </li>
            <li style="margin: 10px 0; padding: 15px; background: #dbeafe; border-radius: 5px; border-left: 4px solid #3b82f6;">
                <strong>Variante B (Beneficio):</strong><br>
                <span style="font-size: 16px;">{new_variants['variant_b']}</span>
            </li>
            <li style="margin: 10px 0; padding: 15px; background: #fce7f3; border-radius: 5px; border-left: 4px solid #ec4899;">
                <strong>Variante C (Urgencia):</strong><br>
                <span style="font-size: 16px;">{new_variants['variant_c']}</span>
            </li>
        </ul>

        <div style="background: #dcfce7; padding: 15px; border-left: 4px solid #16a34a; margin-top: 20px;">
            <p style="margin: 0;"><strong>ACCIÓN RECOMENDADA:</strong></p>
            <p style="margin: 5px 0 0 0;">Cambia el título del video en YouTube Studio con una de las variantes sugeridas AHORA para mejorar el CTR.</p>
        </div>

        <hr style="margin: 30px 0;">
        <p style="color: #6b7280; font-size: 12px;">
            Video ID: {video['video_id']}<br>
            Sistema de Aprendizaje Automático - Stage 2<br>
            Los Cerebros han aprendido que este estilo de título NO funciona
        </p>
    </body>
    </html>
    """

    send_email(subject, body)

def monitor_videos():
    """Monitorea videos en checkpoints especificos"""
    sb = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY")
    )

    # Obtener videos en monitoreo
    # MISMA LÓGICA import_daily: Procesar videos NUEVOS primero (por published_at DESC)
    videos = sb.table("video_monitoring")\
        .select("*")\
        .eq("status", "monitoring")\
        .order("published_at", desc=True)\
        .execute()

    print(f"[INFO] Videos en monitoreo: {len(videos.data)}")

    now = datetime.now(timezone.utc)

    for video in videos.data:
        published = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
        hours_since = (now - published).total_seconds() / 3600

        # NUEVO: Detectar perfil del video primero
        video_data_for_profile = {
            'title': video['title_original'],
            'channel_id': video.get('channel_id'),
            'video_id': video['video_id']
        }
        profile = get_channel_profile(video_data_for_profile)
        profile_config = get_profile_config(profile)

        # NUEVO: Checkpoints diferenciados por perfil
        evaluation_checkpoints = profile_config['evaluation_checkpoints']

        checkpoint = None
        checkpoint_name = None

        # Buscar el checkpoint más cercano según el perfil
        for target_hours in evaluation_checkpoints:
            # Ventana de tolerancia: ±30 min para checkpoints < 48h, ±2h para >= 48h
            tolerance = 0.5 if target_hours < 48 else 2.0

            if target_hours - tolerance <= hours_since <= target_hours + tolerance:
                checkpoint = f"checkpoint_{target_hours}h"

                # Nombres legibles
                if target_hours < 24:
                    checkpoint_name = f"{int(target_hours)} Horas"
                elif target_hours == 24:
                    checkpoint_name = "24 Horas"
                elif target_hours == 48:
                    checkpoint_name = "48 Horas"
                elif target_hours == 168:
                    checkpoint_name = "7 Días"
                else:
                    checkpoint_name = f"{int(target_hours)}h"
                break

        if checkpoint:
            # Verificar si ya se envio notificacion para este checkpoint
            notifications = json.loads(video.get('notifications_sent', '{}') or '{}')
            if checkpoint in notifications:
                print(f"[SKIP] {checkpoint_name} ya notificado para {video['title_original'][:50]}")
                continue

            print(f"\n[{checkpoint_name}] {video['title_original'][:50]}...")

            # Obtener metricas actuales del video
            video_data = sb.table("videos")\
                .select("view_count, like_count, comment_count")\
                .eq("video_id", video['video_id'])\
                .single()\
                .execute()

            views = video_data.data.get('view_count', 0)
            likes = video_data.data.get('like_count', 0)
            comments = video_data.data.get('comment_count', 0)

            # Calcular VPH
            vph = int(views / hours_since) if hours_since > 0 else 0

            # Obtener Analytics completo (CTR, Retention, IMPRESIONES) en todos los checkpoints
            analytics_data = None
            ctr = None
            retention = None
            impressions = None
            published_date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
            analytics_data = get_video_analytics(video['video_id'], published_date)
            if analytics_data:
                ctr = analytics_data.get('ctr')
                retention = analytics_data.get('retention')
                impressions = analytics_data.get('impressions')

            # Guardar metricas en JSONB
            current_metrics = json.loads(video.get('metrics', '{}') or '{}')
            current_metrics[checkpoint] = {
                'timestamp': now.isoformat(),
                'views': views,
                'likes': likes,
                'comments': comments,
                'vph': vph,
                'ctr': ctr,
                'retention': retention,
                'impressions': impressions,
                'hours_since': round(hours_since, 1)
            }

            # Actualizar notificaciones enviadas
            notifications[checkpoint] = now.isoformat()

            # NUEVO: MATRIZ DE DIAGNÓSTICO (Llamar a diagnose_root_cause)
            diagnosis = diagnose_root_cause(impressions, ctr, retention, views, profile, profile_config)

            print(f"  [PROFILE: {profile.value.upper()}]")
            print(f"  [DIAGNOSIS] {diagnosis['syndrome']}: Culpable → {diagnosis['culprit']}")
            print(f"  [IMPRESIONES] {impressions if impressions else 'N/A'} ({diagnosis['impressions_level']})")
            print(f"  [CTR] {ctr:.1f}%" if ctr else "  [CTR] N/A")

            # Actualizar en base de datos (con perfil, diagnosis completo)
            sb.table("video_monitoring").update({
                'metrics': json.dumps(current_metrics),
                'notifications_sent': json.dumps(notifications),
                'last_check_at': now.isoformat(),
                'monitoring_stage': checkpoint,
                'profile': profile.value,
                'diagnosis_syndrome': diagnosis['syndrome'],
                'diagnosis_culprit': diagnosis['culprit'],
                'diagnosis_reason': diagnosis['reason'],
                'diagnosis_action': diagnosis['action'],
                'impressions_level': diagnosis['impressions_level']
            }).eq('video_id', video['video_id']).execute()

            # Evaluar performance para emails basado en el diagnóstico
            if diagnosis['syndrome'] == "SUCCESS":
                nivel = "ÉXITO"
                color = "#10b981"
            elif diagnosis['syndrome'] in ["FANTASMA", "INVISIBLE", "CLICKBAIT"]:
                nivel = diagnosis['syndrome']
                color = "#ef4444"
            else:
                # Fallback basado en VPH
                nivel = "BUENO" if vph >= 20 else "NORMAL" if vph >= 10 else "BAJO"
                color = "#10b981" if vph >= 20 else "#f59e0b" if vph >= 10 else "#ef4444"

            # STAGE 2 LEARNING: Guardar en user_preferences (con diagnóstico de problema)
            learning_result = save_learning_data(sb, video, analytics_data, vph, views, checkpoint)

            # ALERTA CRÍTICA: Si CTR < 5% en checkpoint 24h, enviar alerta con nuevas variantes
            if checkpoint == "checkpoint_24h" and ctr is not None and ctr < 5.0:
                # Determinar qué está fallando
                problem_source = "unknown"

                if retention and retention > 40:
                    problem_source = "thumbnail"
                    print(f"[ALERT] CTR CRÍTICO pero problema es MINIATURA - NO se envían títulos nuevos")
                elif analytics_data and analytics_data.get('traffic_sources'):
                    top_source = max(analytics_data['traffic_sources'].items(), key=lambda x: x[1]['percentage'])[0]
                    if top_source == 'YT_SEARCH':
                        problem_source = "title"
                    elif top_source in ['BROWSE', 'BROWSE_FEATURES', 'RELATED_VIDEO']:
                        problem_source = "thumbnail"
                elif retention and retention < 30:
                    problem_source = "both"
                else:
                    problem_source = "title"  # Por defecto, asumir título

                print(f"[ALERT] CTR CRÍTICO: {ctr:.1f}% - Problema: {problem_source}")

                # Solo generar nuevos títulos si el problema es título o ambos
                if problem_source in ["title", "both", "unknown"]:
                    new_variants = generate_new_title_variants(video['title_original'], sb)
                    send_alert_email(video, analytics_data, vph, views, new_variants, problem_source)

                    # Guardar variantes sugeridas en monitoring
                    sb.table("video_monitoring").update({
                        'alert_sent_at': now.isoformat(),
                        'suggested_titles': json.dumps(new_variants),
                        'problem_diagnosed': problem_source
                    }).eq('video_id', video['video_id']).execute()
                else:
                    # Solo enviar alerta sin nuevos títulos
                    send_alert_email(video, analytics_data, vph, views, {}, problem_source)
                    sb.table("video_monitoring").update({
                        'alert_sent_at': now.isoformat(),
                        'problem_diagnosed': problem_source
                    }).eq('video_id', video['video_id']).execute()

            # Enviar notificacion con REPORTE DE DIAGNÓSTICO
            email_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2 style="color: #2563eb;">📊 REPORTE DE DIAGNÓSTICO - {checkpoint_name}</h2>

                <div style="background: #f3f4f6; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <p style="margin: 0;"><strong>Video:</strong> {video['title_original']}</p>
                    <p style="margin: 5px 0 0 0;"><strong>Perfil:</strong> {profile.value.upper()}</p>
                    <p style="margin: 5px 0 0 0;"><strong>Tiempo Online:</strong> {hours_since:.1f} horas</p>
                </div>

                <h3 style="color: #2563eb;">DATOS:</h3>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr style="background: {'#dcfce7' if diagnosis['impressions_level'] == 'Alta' else '#fee2e2' if diagnosis['impressions_level'] == 'Baja' else '#f3f4f6'};">
                        <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Impresiones</strong></td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">{impressions if impressions else 'N/A'} ({diagnosis['impressions_level']})</td>
                    </tr>
                    {"<tr style='background: " + ("#dcfce7" if ctr and ctr >= profile_config['min_ctr_threshold'] else "#fee2e2" if ctr and ctr < profile_config['min_ctr_threshold'] else "#f3f4f6") + ";'><td style='padding: 10px; border: 1px solid #e5e7eb;'><strong>CTR Actual</strong></td><td style='padding: 10px; border: 1px solid #e5e7eb; font-weight: bold; color: " + ("#16a34a" if ctr and ctr >= profile_config['min_ctr_threshold'] else "#dc2626" if ctr else "#6b7280") + ";'>" + f"{ctr:.1f}% (Meta: {profile_config['min_ctr_threshold']}%)" + "</td></tr>" if ctr is not None else ""}
                    {"<tr style='background: #f3f4f6;'><td style='padding: 10px; border: 1px solid #e5e7eb;'><strong>Retention</strong></td><td style='padding: 10px; border: 1px solid #e5e7eb;'>" + f"{retention:.1f}%" + "</td></tr>" if retention is not None else ""}
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Vistas</strong></td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{views:,}</td>
                    </tr>
                    <tr style="background: #f3f4f6;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>VPH (Vistas por Hora)</strong></td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{vph:,}</td>
                    </tr>
                </table>

                <h3 style="color: {'#16a34a' if diagnosis['syndrome'] == 'SUCCESS' else '#dc2626'};">🎯 VEREDICTO:</h3>
                <div style="background: {'#dcfce7' if diagnosis['syndrome'] == 'SUCCESS' else '#fee2e2'}; padding: 15px; border-left: 4px solid {'#16a34a' if diagnosis['syndrome'] == 'SUCCESS' else '#dc2626'}; margin-bottom: 20px;">
                    <p style="margin: 0;"><strong>Culpable Principal:</strong> {diagnosis['culprit']}</p>
                    <p style="margin: 10px 0 0 0;"><strong>Razón:</strong> {diagnosis['reason']}</p>
                </div>

                <h3 style="color: #f59e0b;">💡 ACCIÓN SUGERIDA:</h3>
                <div style="background: #fef3c7; padding: 15px; border-left: 4px solid #f59e0b; margin-bottom: 20px;">
                    <p style="margin: 0;">{diagnosis['action']}</p>
                </div>

                <hr style="margin: 30px 0;">
                <p style="color: #6b7280; font-size: 12px;">
                    Video ID: {video['video_id']}<br>
                    Checkpoint: {checkpoint_name}<br>
                    Síndrome: {diagnosis['syndrome']}<br>
                    Matriz de Diagnóstico de Causa Raíz Activada 🧠
                </p>
            </body>
            </html>
            """

            send_email(
                f"[{checkpoint_name}] {video['title_original'][:50]} - {vph} VPH ({nivel})",
                email_body
            )

            print(f"  Vistas: {views:,} | Likes: {likes:,} | VPH: {vph:,} | {nivel}")

            # Si es checkpoint_72h, decidir si continuar o cerrar monitoreo
            if checkpoint == "checkpoint_72h":
                # OPCIÓN 3: Monitoreo selectivo basado en "potencial dormido"
                # Criterios: Alta retention + Bajo CTR = Puede explotar tarde

                has_potential = False
                reason_for_extension = None

                if retention and retention >= 50 and ctr and ctr < 8:
                    # POTENCIAL DORMIDO: Contenido excelente pero no está siendo visto
                    has_potential = True
                    reason_for_extension = f"high_retention_{retention:.1f}%_low_ctr_{ctr:.1f}%"
                    print(f"  [POTENCIAL DORMIDO] Retention={retention:.1f}% + CTR={ctr:.1f}%")
                    print(f"  [EXTENDED] Monitoreo extendido activado (7d, 15d, 30d)")
                elif vph < 20 and retention and retention >= 45:
                    # Bajo VPH pero buena retention - puede mejorar
                    has_potential = True
                    reason_for_extension = f"low_vph_{vph}_good_retention_{retention:.1f}%"
                    print(f"  [POTENCIAL DORMIDO] VPH bajo pero retention buena")
                    print(f"  [EXTENDED] Monitoreo extendido activado (7d, 15d, 30d)")

                if has_potential:
                    # Continuar monitoreo (status sigue siendo "monitoring")
                    sb.table("video_monitoring").update({
                        'long_term_watch': True,
                        'long_term_reason': reason_for_extension,
                        'extended_monitoring_started_at': now.isoformat()
                    }).eq('video_id', video['video_id']).execute()
                else:
                    # Video exitoso o sin potencial - Cerrar monitoreo
                    sb.table("video_monitoring").update({
                        'status': 'completed',
                        'completed_at': now.isoformat(),
                        'completion_reason': 'normal_72h_completion'
                    }).eq('video_id', video['video_id']).execute()
                    print(f"  [COMPLETADO] Monitoreo finalizado (no requiere extensión)")

            # Si es checkpoint_30d, siempre cerrar (fin definitivo)
            if checkpoint == "checkpoint_30d":
                # Detectar si hubo explosión tardía
                metrics_all = json.loads(video.get('metrics', '{}') or '{}')
                ctr_day3 = metrics_all.get('checkpoint_72h', {}).get('ctr')
                ctr_day30 = ctr

                explosion_detected = False
                if ctr_day3 and ctr_day30 and ctr_day30 >= ctr_day3 * 1.5:
                    explosion_detected = True
                    print(f"  [SLEEPER HIT] CTR aumentó de {ctr_day3:.1f}% a {ctr_day30:.1f}% (+{(ctr_day30/ctr_day3-1)*100:.0f}%)")

                sb.table("video_monitoring").update({
                    'status': 'completed',
                    'completed_at': now.isoformat(),
                    'explosion_detected': explosion_detected,
                    'completion_reason': 'extended_30d_completion'
                }).eq('video_id', video['video_id']).execute()
                print(f"  [COMPLETADO] Monitoreo extendido finalizado (30 días)")

if __name__ == "__main__":
    monitor_videos()
