"""Orquestador: busca noticias recientes, decide qué proponer, planifica la
semana (lunes-viernes + recopilatorio del sábado) y deja el resultado en dos
sitios:
- output/proposal.md → para el Issue de GitHub
- docs/data/calendar.json → para el calendario visual en docs/index.html

Ambos se generan a partir de la MISMA lista ya planificada, para que el
Issue y el calendario siempre coincidan.
"""
from datetime import date
from pathlib import Path

from calendar_data import schedule_week, update_calendar
from fetch_news import fetch_recent_articles
from generate_proposal import build_proposal, render_markdown


def main():
    articles = fetch_recent_articles(days=30)
    result = build_proposal(articles)

    scheduled = schedule_week(result["items"])
    markdown = render_markdown(scheduled, ai_mode=result["ai_mode"], discarded=result["discarded"])

    today = date.today().isoformat()
    body = f"# Propuesta de contenido — semana del {today}\n\n{markdown}\n"

    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "proposal.md").write_text(body, encoding="utf-8")

    if scheduled:
        update_calendar(scheduled)
    else:
        print("Sin propuestas esta semana: no se actualiza el calendario.")

    print(
        f"Propuesta generada ({len(articles)} noticias encontradas, "
        f"{len(scheduled)} piezas planificadas) en {output_dir / 'proposal.md'}"
    )


if __name__ == "__main__":
    main()
