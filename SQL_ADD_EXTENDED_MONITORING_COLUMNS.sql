-- ============================================================================
-- SQL PARA AGREGAR COLUMNAS DE MONITOREO EXTENDIDO
-- ============================================================================
-- Ejecutar en Supabase SQL Editor
--
-- NUEVAS FUNCIONALIDADES:
-- 1. Detectar "potencial dormido" (retention alta + CTR bajo)
-- 2. Monitoreo extendido: 7d, 15d, 30d
-- 3. Detectar "sleeper hits" (videos que explotan tarde)
-- ============================================================================

-- Agregar columna: long_term_watch (indica si video está en monitoreo extendido)
ALTER TABLE video_monitoring
ADD COLUMN IF NOT EXISTS long_term_watch BOOLEAN DEFAULT FALSE;

-- Agregar columna: long_term_reason (razón del monitoreo extendido)
ALTER TABLE video_monitoring
ADD COLUMN IF NOT EXISTS long_term_reason TEXT;

-- Agregar columna: extended_monitoring_started_at (cuando inició monitoreo extendido)
ALTER TABLE video_monitoring
ADD COLUMN IF NOT EXISTS extended_monitoring_started_at TIMESTAMPTZ;

-- Agregar columna: explosion_detected (si hubo explosión tardía)
ALTER TABLE video_monitoring
ADD COLUMN IF NOT EXISTS explosion_detected BOOLEAN DEFAULT FALSE;

-- Agregar columna: completion_reason (razón de cierre)
ALTER TABLE video_monitoring
ADD COLUMN IF NOT EXISTS completion_reason TEXT;

-- Crear índice para búsquedas eficientes de videos en monitoreo extendido
CREATE INDEX IF NOT EXISTS idx_video_monitoring_long_term
ON video_monitoring(long_term_watch, status)
WHERE long_term_watch = TRUE AND status = 'monitoring';

-- Crear índice para videos con explosión tardía (para análisis)
CREATE INDEX IF NOT EXISTS idx_video_monitoring_explosion
ON video_monitoring(explosion_detected, completed_at)
WHERE explosion_detected = TRUE;

-- ============================================================================
-- COMENTARIOS EN LAS COLUMNAS
-- ============================================================================

COMMENT ON COLUMN video_monitoring.long_term_watch IS
'TRUE si el video está en monitoreo extendido (7d, 15d, 30d) porque tiene potencial dormido';

COMMENT ON COLUMN video_monitoring.long_term_reason IS
'Razón del monitoreo extendido. Ejemplos: "high_retention_50.2%_low_ctr_3.8%", "low_vph_12_good_retention_48.5%"';

COMMENT ON COLUMN video_monitoring.extended_monitoring_started_at IS
'Timestamp cuando inició el monitoreo extendido (en checkpoint_72h)';

COMMENT ON COLUMN video_monitoring.explosion_detected IS
'TRUE si el video experimentó explosión tardía (CTR aumentó 50%+ después del día 3)';

COMMENT ON COLUMN video_monitoring.completion_reason IS
'Razón de cierre del monitoreo. Valores: "normal_72h_completion", "extended_30d_completion"';

-- ============================================================================
-- VISTA PARA ANÁLISIS DE SLEEPER HITS
-- ============================================================================

CREATE OR REPLACE VIEW sleeper_hits_analysis AS
SELECT
    vm.video_id,
    vm.title_original,
    vm.published_at,
    vm.long_term_reason,
    vm.extended_monitoring_started_at,
    vm.completed_at,
    vm.metrics,
    -- Extraer métricas de día 3 y día 30
    (vm.metrics::jsonb->'checkpoint_72h'->>'ctr')::float AS ctr_day3,
    (vm.metrics::jsonb->'checkpoint_30d'->>'ctr')::float AS ctr_day30,
    (vm.metrics::jsonb->'checkpoint_72h'->>'vph')::int AS vph_day3,
    (vm.metrics::jsonb->'checkpoint_30d'->>'vph')::int AS vph_day30,
    -- Calcular crecimiento
    CASE
        WHEN (vm.metrics::jsonb->'checkpoint_72h'->>'ctr')::float > 0
        THEN ROUND(
            (((vm.metrics::jsonb->'checkpoint_30d'->>'ctr')::float /
              (vm.metrics::jsonb->'checkpoint_72h'->>'ctr')::float - 1) * 100)::numeric,
            1
        )
        ELSE NULL
    END AS ctr_growth_percent,
    CASE
        WHEN (vm.metrics::jsonb->'checkpoint_72h'->>'vph')::int > 0
        THEN ROUND(
            (((vm.metrics::jsonb->'checkpoint_30d'->>'vph')::int::float /
              (vm.metrics::jsonb->'checkpoint_72h'->>'vph')::int::float - 1) * 100)::numeric,
            1
        )
        ELSE NULL
    END AS vph_growth_percent
FROM video_monitoring vm
WHERE vm.explosion_detected = TRUE
ORDER BY vm.completed_at DESC;

COMMENT ON VIEW sleeper_hits_analysis IS
'Vista de análisis de "sleeper hits" - Videos que explotaron tarde (después del día 3)';

-- ============================================================================
-- QUERY DE EJEMPLO: Ver videos en monitoreo extendido
-- ============================================================================

/*
SELECT
    video_id,
    title_original,
    long_term_reason,
    DATE_PART('day', NOW() - extended_monitoring_started_at::timestamp) AS days_in_extended_monitoring,
    metrics::jsonb->'checkpoint_72h'->>'ctr' AS ctr_day3,
    metrics::jsonb->'checkpoint_72h'->>'retention' AS retention_day3
FROM video_monitoring
WHERE long_term_watch = TRUE
  AND status = 'monitoring'
ORDER BY extended_monitoring_started_at DESC;
*/

-- ============================================================================
-- QUERY DE EJEMPLO: Ver sleeper hits detectados
-- ============================================================================

/*
SELECT
    video_id,
    title_original,
    ctr_day3,
    ctr_day30,
    ctr_growth_percent,
    vph_day3,
    vph_day30,
    vph_growth_percent
FROM sleeper_hits_analysis
WHERE ctr_growth_percent > 50  -- Videos con crecimiento de CTR > 50%
ORDER BY ctr_growth_percent DESC
LIMIT 10;
*/

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
