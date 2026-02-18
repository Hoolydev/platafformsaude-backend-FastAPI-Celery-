"""
Celery Beat Schedules
"""

from celery.schedules import crontab

BEAT_SCHEDULE = {
    # Lembretes 24h — a cada 60 minutos
    "verificar-lembretes-24h": {
        "task": "app.workers.reminders.verificar_lembretes_24h",
        "schedule": 60 * 60,  # 3600 segundos
    },
    # Lembretes 2h — a cada 15 minutos
    "verificar-lembretes-2h": {
        "task": "app.workers.reminders.verificar_lembretes_2h",
        "schedule": 15 * 60,  # 900 segundos
    },
    # Recuperação de leads — a cada 30 minutos
    "verificar-recuperacao": {
        "task": "app.workers.lead_recovery.verificar_recuperacao",
        "schedule": 30 * 60,  # 1800 segundos
    },
    # Verificar ausências — todo dia às 10h (America/Sao_Paulo)
    "verificar-ausencias": {
        "task": "app.workers.reminders.verificar_ausencias",
        "schedule": crontab(hour=10, minute=0),
    },
}
