"""Planifica la semana y mantiene docs/data/calendar.json.

Estructura fija de la semana:
- Lunes a viernes: una pieza de contenido cada día, rotando el formato
  (vídeo animado corto / carrusel / LinkedIn post) para no repetir el mismo
  formato dos días seguidos.
- Sábado: un recopilatorio con los temas tratados esa semana.
- Domingo: libre, sin contenido.

Cada ejecución del bot sustituye lo que hubiera para esa misma semana en
`calendar.json` — así relanzar el workflow no duplica entradas.
"""
import json
from datetime import date, timedelta
from pathlib import Path

CALENDAR_PATH = Path(__file__).resolve().parent.parent / "docs" / "data" / "calendar.json"
WEEKDAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


CONTENT_FORMATS = ["Reel", "Carrusel", "LinkedIn post"]
RECAP_FORMAT = "Recopilatorio semanal"


def next_monday(from_date=None) -> date:
    """El lunes de la semana siguiente a `from_date` (por defecto, hoy)."""
    from_date = from_date or date.today()
    days_ahead = (7 - from_date.weekday()) % 7
    days_ahead = days_ahead or 7
    return from_date + timedelta(days=days_ahead)


def schedule_week(items, week_start=None):
    """Reparte hasta 5 propuestas de lunes a viernes (rotando el formato) y
    añade un recopilatorio el sábado con los temas de la semana. El domingo
    se deja libre. Devuelve la lista ordenada de entradas ya planificadas
    (con 'date', 'weekday' y 'format').
    """
    week_start = week_start or next_monday()

    weekday_items = items[:5]
    if len(items) > 5:
        print(
            f"[info] se generaron {len(items)} propuestas; se usan las 5 primeras "
            "para lunes-viernes y el resto no se usa esta semana."
        )

    scheduled = []
    for i, item in enumerate(weekday_items):
        item_date = week_start + timedelta(days=i)
        scheduled.append(
            {
                "title": item["title"],
                "summary": item["summary"],
                "source_name": item["source_name"],
                "source_url": item["source_url"],
                "format": CONTENT_FORMATS[i % len(CONTENT_FORMATS)],
                "date": item_date.isoformat(),
                "weekday": WEEKDAY_NAMES[i],
            }
        )

    if weekday_items:
        recap_date = week_start + timedelta(days=5)  
        temas = "; ".join(it["title"] for it in weekday_items)
        scheduled.append(
            {
                "title": "Recopilatorio semanal de ciberseguridad",
                "summary": f"Repaso de lo publicado esta semana: {temas}.",
                "source_name": "Resumen interno",
                "source_url": "",
                "format": RECAP_FORMAT,
                "date": recap_date.isoformat(),
                "weekday": WEEKDAY_NAMES[5],
            }
        )

    return scheduled


def update_calendar(scheduled_items, week_start=None):
    """Añade/sustituye las entradas de la semana `week_start` (lunes) en
    docs/data/calendar.json y devuelve la lista completa resultante.
    `scheduled_items` debe venir ya de `schedule_week()` (con 'date').
    """
    week_start = week_start or next_monday()
    week_start_iso = week_start.isoformat()
    week_end_iso = (week_start + timedelta(days=6)).isoformat()

    CALENDAR_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if CALENDAR_PATH.exists():
        try:
            existing = json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[warn] no se pudo leer el calendario existente, se reescribe: {exc}")
            existing = []

   
    kept = [e for e in existing if not (week_start_iso <= e.get("date", "") <= week_end_iso)]

    combined = sorted(kept + scheduled_items, key=lambda e: e["date"])

    CALENDAR_PATH.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Calendario actualizado: {len(scheduled_items)} piezas para la semana del {week_start_iso}")
    return combined
