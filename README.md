# YouTube ML & A/B Testing Pipeline

Sistema de Machine Learning y A/B Testing para optimización de contenido de YouTube.

## 📋 Descripción

Este repositorio contiene los workflows de:
- **A/B Testing System**: Detección y monitoreo de nuevos videos
- **ML System**: Entrenamiento y predicciones de viralidad
- **GUI Evaluator**: Evaluación automática de guiones
- **Análisis Estratégico**: Orquestación de decisiones ML

## 🔧 Workflows

| Workflow | Frecuencia | Tiempo | Descripción |
|----------|-----------|--------|-------------|
| `ab_testing_system.yml` | Cada 6h | 40min | Detecta videos nuevos y monitorea métricas |
| `ml_system.yml` | Diario | 2min | Predicciones de viralidad |
| `gui_weekly_training.yml` | Semanal | 5min | Entrena modelo de evaluación de guiones |
| `gui_evaluator_auto.yml` | Semanal | 5min | Evalúa guiones automáticamente |
| `analisis_ml_semanal.yml` | Semanal | 2min | Análisis de anti-patrones |
| `cerebro5_estrategico_semanal.yml` | Semanal | 2min | Orquestación estratégica |
| `ml_monthly_training.yml` | Mensual | 2min | Entrenamiento completo del modelo |

**Total:** 1,081 min/mes ✅

## 🔐 GitHub Secrets Requeridos

```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJxxx...
YT_CLIENT_ID=xxx.apps.googleusercontent.com
YT_CLIENT_SECRET=GOCSPX-xxx
YT_REFRESH_TOKEN=1//xxx
GEMINI_API_KEY=AIzaxxx
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu@email.com
SMTP_PASSWORD=xxx
NOTIFICATION_EMAIL=notificaciones@email.com
```

## 📦 Estructura

```
.
├── .github/
│   └── workflows/          # Workflows de GitHub Actions
├── scripts/                # Scripts Python
│   ├── detect_new_videos.py
│   ├── monitor_video_metrics.py
│   ├── predict_video.py
│   ├── save_training_snapshot.py
│   └── train_user_preferences.py
├── requirements.txt        # Dependencias Python
└── README.md
```

## 🚀 Setup

1. Configurar GitHub Secrets (ver sección de arriba)
2. Los workflows se ejecutarán automáticamente según su schedule
3. Monitorear logs en Actions tab

## 📊 Conexión con Cuenta Principal

Este repositorio trabaja en conjunto con `yt-pipeline-cron` (cuenta principal):
- **Cuenta Principal (bK777741)**: Captura de datos diarios, trending, analytics
- **Cuenta ML (Pika77777)**: Machine Learning y A/B Testing

Ambas cuentas acceden a la misma base de datos Supabase.

## ⚡ Powered by

- GitHub Actions (2,000 min/mes gratis)
- Supabase (PostgreSQL)
- Python 3.12
- Google YouTube Data API v3
- Google Gemini AI

---

**Nota**: Este es un repositorio secundario para distribuir carga de GitHub Actions.
