"""Convierte una lista de noticias en 5-8 propuestas de contenido para el
calendario editorial de QuantumSec.

Si existe la variable de entorno ANTHROPIC_API_KEY, usa la API de Claude para
redactar propuestas priorizadas y bien escritas. Si no existe (o falla la
llamada), cae a un modo simple sin IA que igualmente produce una lista
utilizable, para que el proyecto nunca dependa por completo de tener una
clave de pago configurada.
"""
import os
import re

import requests

FORMATS = ["LinkedIn post", "Carrusel", "Vídeo animado corto"]


SPANISH_SOURCES = ("incibe",)


RELEVANCE_KEYWORDS = [
    "ransomware", "phishing", "malware", "vulnerab", "breach", "hack",
    "exploit", "attack", "ataque", "spyware", "rootkit", "backdoor",
    "botnet", "ddos", "zero-day", "zero day", "cve-", "leak", "leaked",
    "fuga de datos", "cyberattack", "cyber attack", "trojan", "troyano",
    "spoofing", "suplantaci", "ciberseguridad", "cibersegur", "cyber",
    "security", "seguridad", "brecha", "estafa", "fraude", "phish",
    "privilege escalation", "remote code execution", "unauthorized access",
    "root access", "data breach", "secuestro de datos", "extorsion",
    "extorsión", "amenaza", "threat actor", "apt ", "credential",
]

PROMPT_TEMPLATE = """Eres el/la responsable de contenido de QuantumSec, una empresa \
de ciberseguridad centrada en pymes españolas.

A partir de esta lista de noticias de ciberseguridad de los últimos 30 días, \
propón entre 5 y 8 ideas de contenido para el calendario editorial semanal. \
Prioriza noticias con impacto real para pymes (ransomware, phishing/BEC, \
vulnerabilidades explotadas activamente, brechas de datos, normativa) y casos \
de España si los hay.

Para cada idea da:
- Tema/título
- Formato sugerido (uno de: LinkedIn post, Carrusel, Vídeo animado corto)
- Descripción breve (2-3 líneas) explicando el ángulo y por qué le interesa a \
una pyme
- La fuente en la que se basa, con enlace

Devuelve el resultado en Markdown, como una lista numerada, lista para pegar \
directamente en un issue de GitHub. No añadas explicaciones fuera de la lista. \
Escribe absolutamente todo (títulos, formatos, descripciones) en español, \
aunque la noticia original esté en inglés.

Noticias disponibles:
{articles}
"""


def build_proposal(articles, max_articles: int = 40) -> str:
    if not articles:
        return (
            "No se encontraron noticias de ciberseguridad en los últimos 30 días "
            "en los feeds configurados. Revisa `src/fetch_news.py` por si alguna "
            "URL ha caducado."
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return _build_with_claude(articles[:max_articles], api_key)
        except Exception as exc:
            print(f"[warn] fallo al generar con la API de Claude, uso el modo simple: {exc}")

    return _build_simple(articles)


def _is_relevant(article) -> bool:
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    return any(keyword in text for keyword in RELEVANCE_KEYWORDS)


def _translate_to_spanish(text: str, source: str = "") -> str:
    """Traduce `text` al español con la API pública y gratuita de MyMemory
    (sin clave). Si el texto está vacío, ya viene en español (según la
    fuente) o la traducción falla por cualquier motivo, devuelve el texto
    original tal cual — nunca rompe el resto del pipeline por esto.
    """
    text = (text or "").strip()
    if not text or any(s in source.lower() for s in SPANISH_SOURCES):
        return text

    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": "en|es"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        translated = data.get("responseData", {}).get("translatedText")
      
        if translated and "MYMEMORY WARNING" not in translated.upper():
            return translated
    except Exception as exc:
        print(f"[warn] no se pudo traducir un resumen, se deja en el idioma original: {exc}")

    return text


def _build_with_claude(articles, api_key: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    articles_text = "\n".join(
        f"- ({a['source']}) {a['title']} — {a['summary']} [{a['link']}]" for a in articles
    )
    prompt = PROMPT_TEMPLATE.format(articles=articles_text)

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _build_simple(articles, count: int = 8) -> str:
    """Fallback sin IA: filtra por relevancia (palabras clave de
    ciberseguridad) y ordena las noticias más recientes en una lista simple,
    rotando el formato sugerido. Si el filtro deja la lista vacía, usa las
    noticias sin filtrar para no devolver nada en blanco.
    """
    relevant = [a for a in articles if _is_relevant(a)]
    candidates = relevant or articles
    discarded = len(articles) - len(candidates)

    lines = ["## Propuesta de contenido semanal (modo simple, sin IA)\n"]
    for i, article in enumerate(candidates[:count], start=1):
        formato = FORMATS[i % len(FORMATS)]
        resumen_es = _translate_to_spanish(article["summary"], article["source"])
        lines.append(
            f"{i}. **{article['title']}** — formato sugerido: {formato}\n"
            f"   - Fuente: {article['source']} ({article['link']})\n"
            f"   - Resumen: {resumen_es}\n"
        )
    filtro_nota = (
        f" Se descartaron {discarded} resultados sin relación aparente con "
        "ciberseguridad (filtro por palabras clave, no siempre perfecto)."
        if discarded
        else ""
    )
    lines.append(
        "\n_Nota: esta propuesta se generó sin la API de Claude (no hay "
        "`ANTHROPIC_API_KEY` configurada como secreto del repo). Añádela para "
        "obtener propuestas redactadas y priorizadas automáticamente en vez de "
        f"esta lista simple.{filtro_nota}_"
    )
    return "\n".join(lines)