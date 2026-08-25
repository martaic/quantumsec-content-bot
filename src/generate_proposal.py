"""Convierte una lista de noticias en 5 propuestas de contenido (una por
cada día de lunes a viernes) para el calendario editorial de QuantumSec.

Si existe la variable de entorno ANTHROPIC_API_KEY, usa la API de Claude para
redactar propuestas priorizadas y bien escritas. Si no existe (o falla la
llamada), cae a un modo simple sin IA que igualmente produce una lista
utilizable, para que el proyecto nunca dependa por completo de tener una
clave de pago configurada.

Este módulo solo decide QUÉ se propone (título, resumen, fuente). El día de
la semana y el formato (reel / carrusel / post) los asigna
`calendar_data.schedule_week()`, no este módulo — así el ritmo de publicación
es consistente cada semana, sin depender de qué tipo de formato "encajaría
mejor" con cada noticia.
"""
import os

import requests

WEEKLY_COUNT = 5  

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

PROPOSAL_TOOL = {
    "name": "proponer_contenido",
    "description": (
        "Devuelve la lista de propuestas de contenido para el calendario "
        "editorial de QuantumSec."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Tema/título de la pieza, en español"},
                        "summary": {
                            "type": "string",
                            "description": "Descripción breve (2-3 líneas) en español: el ángulo y por qué le interesa a una pyme",
                        },
                        "source_name": {"type": "string"},
                        "source_url": {"type": "string"},
                    },
                    "required": ["title", "summary", "source_name", "source_url"],
                },
            }
        },
        "required": ["items"],
    },
}

PROMPT_TEMPLATE = """Eres el/la responsable de contenido de QuantumSec, una empresa \
de ciberseguridad centrada en pymes españolas.

A partir de esta lista de noticias de ciberseguridad de los últimos 30 días, \
propón exactamente 5 ideas de contenido para el calendario editorial de la \
semana que viene (una para cada día, de lunes a viernes), usando la \
herramienta `proponer_contenido`. Prioriza noticias con impacto real para \
pymes (ransomware, phishing/BEC, vulnerabilidades explotadas activamente, \
brechas de datos, normativa) y casos de España si los hay.

Escribe absolutamente todo (title, summary) en español, aunque la noticia \
original esté en inglés. `source_name` y `source_url` deben corresponder a \
la noticia real en la que se basa cada propuesta. No incluyas el formato \
(reel/carrusel/post): eso se asigna aparte, según el día de la semana.

Noticias disponibles:
{articles}
"""


def build_proposal(articles, max_articles: int = 40) -> dict:
    """Devuelve {"items": [...], "ai_mode": bool, "discarded": int}.

    `items` trae como mucho `WEEKLY_COUNT` propuestas (título, resumen,
    fuente), sin día ni formato asignados todavía — eso lo hace
    `calendar_data.schedule_week()`.
    """
    if not articles:
        return {"items": [], "ai_mode": False, "discarded": 0}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            items = _build_items_with_claude(articles[:max_articles], api_key)
            return {"items": items, "ai_mode": True, "discarded": 0}
        except Exception as exc:
            print(f"[warn] fallo al generar con la API de Claude, uso el modo simple: {exc}")

    items, discarded = _build_items_simple(articles)
    return {"items": items, "ai_mode": False, "discarded": discarded}


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


def _build_items_with_claude(articles, api_key: str):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    articles_text = "\n".join(
        f"- ({a['source']}) {a['title']} — {a['summary']} [{a['link']}]" for a in articles
    )
    prompt = PROMPT_TEMPLATE.format(articles=articles_text)

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        tools=[PROPOSAL_TOOL],
        tool_choice={"type": "tool", "name": "proponer_contenido"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "proponer_contenido":
            return block.input.get("items", [])[:WEEKLY_COUNT]

    raise ValueError("Claude no devolvió la herramienta esperada")


def _build_items_simple(articles, count: int = WEEKLY_COUNT):
    """Fallback sin IA: filtra por relevancia (palabras clave de
    ciberseguridad) y traduce el resumen al español, quedándose con las
    `count` noticias más recientes. Si el filtro deja la lista vacía, usa
    las noticias sin filtrar para no devolver nada en blanco. Devuelve
    (items, num_descartados).
    """
    relevant = [a for a in articles if _is_relevant(a)]
    candidates = relevant or articles
    discarded = len(articles) - len(candidates)

    items = []
    for article in candidates[:count]:
        items.append(
            {
                "title": article["title"],
                "summary": _translate_to_spanish(article["summary"], article["source"]),
                "source_name": article["source"],
                "source_url": article["link"],
            }
        )
    return items, discarded


def render_markdown(scheduled_items, ai_mode: bool = False, discarded: int = 0) -> str:
    """Recibe los items YA planificados (con 'weekday', 'date' y 'format'
    asignados por calendar_data.schedule_week) y los presenta en Markdown
    para el Issue de GitHub, en el mismo orden y con el mismo
    día/formato/resumen que se ve en el calendario visual.
    """
    if not scheduled_items:
        return (
            "No se encontraron noticias de ciberseguridad en los últimos 30 días "
            "en los feeds configurados. Revisa `src/fetch_news.py` por si alguna "
            "URL ha caducado."
        )

    header = (
        "## Calendario de la semana\n"
        if ai_mode
        else "## Calendario de la semana (modo simple, sin IA)\n"
    )
    lines = [header]
    for item in scheduled_items:
        dia = item.get("weekday", "")
        lines.append(
            f"**{dia}** — {item['title']} _({item['format']})_\n"
            f"   - Fuente: {item['source_name']} ({item['source_url']})\n"
            f"   - Resumen: {item['summary']}\n"
        )

    if not ai_mode:
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
