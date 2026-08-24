"""Orquestador: busca noticias recientes, genera la propuesta de contenido y
la escribe en output/proposal.md para que el workflow de GitHub Actions la
publique como Issue.
"""
from datetime import date
from pathlib import Path

from fetch_news import fetch_recent_articles
from generate_proposal import build_proposal


def main():
    articles = fetch_recent_articles(days=30)
    proposal = build_proposal(articles)

    today = date.today().isoformat()
    body = f"# Propuesta de contenido — semana del {today}\n\n{proposal}\n"

    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "proposal.md"
    output_path.write_text(body, encoding="utf-8")

    print(f"Propuesta generada en {output_path} ({len(articles)} noticias encontradas)")


if __name__ == "__main__":
    main()
