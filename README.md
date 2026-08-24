# QuantumSec Content Bot

Bot que cada domingo busca noticias de ciberseguridad de los últimos 30 días
y abre un **Issue** en este repositorio con 5-8 propuestas de contenido
(tema, formato sugerido, descripción y fuente) para el calendario editorial
de QuantumSec. Alguien del equipo revisa el issue y copia lo que le interese
al calendario — el bot nunca escribe contenido directamente, solo propone.

## Cómo funciona

1. `src/fetch_news.py` reúne noticias y menciones de ciberseguridad de tres
   tipos de fuentes, todas gratuitas y sin necesidad de login ni clave de
   API:
   - **RSS**: The Hacker News, BleepingComputer, Krebs on Security, Dark
     Reading, We Live Security, INCIBE-CERT.
   - **Hacker News**: vía la API pública de Algolia, buscando historias
     recientes sobre ransomware, phishing, vulnerabilidades, malware, etc.
   - **Reddit**: publicaciones nuevas de r/cybersecurity, r/netsec e
     r/InfoSecNews, vía el endpoint JSON público (sin autenticación).

   Se queda con lo publicado en los últimos 30 días y elimina duplicados.
2. `src/generate_proposal.py` convierte esas noticias en propuestas de
   contenido:
   - **Con** la variable `ANTHROPIC_API_KEY` configurada: usa la API de
     Claude para redactar y priorizar las propuestas.
   - **Sin** esa clave: genera igualmente una lista útil (modo simple, sin
     IA), rotando los formatos sugeridos.
3. `src/main.py` orquesta los dos pasos anteriores y escribe el resultado en
   `output/proposal.md`.
4. `.github/workflows/weekly-proposal.yml` ejecuta todo lo anterior cada
   domingo (vía GitHub Actions, sin necesidad de ningún servidor propio) y
   abre un Issue con el contenido de `output/proposal.md`.

No hace falta pagar ni mantener ningún servidor: todo corre en los runners
gratuitos de GitHub Actions (2.000 minutos/mes incluidos en repos privados,
ilimitados en repos públicos).

## Puesta en marcha

1. **Activar Actions**: en un fork o al importar este repo, ve a la pestaña
   *Actions* de GitHub y actívalas si no lo están ya.
2. **(Opcional) Añadir la clave de Claude**: en *Settings → Secrets and
   variables → Actions → New repository secret*, añade `ANTHROPIC_API_KEY`
   con una clave de la [consola de Anthropic](https://console.anthropic.com).
   Sin esta clave el bot sigue funcionando en modo simple.
3. **Probarlo manualmente**: en la pestaña *Actions*, elige el workflow
   "Propuesta semanal de contenido" y pulsa *Run workflow* para lanzarlo sin
   esperar al domingo.
4. Cada domingo a las 20:00 (hora de Madrid en verano; ajustar el `cron` en
   `.github/workflows/weekly-proposal.yml` si cambia el horario) se abrirá
   un nuevo Issue automáticamente.

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate  # o .venv\Scripts\activate en Windows
pip install -r requirements.txt
cp .env.example .env       # opcional, para probar con la API de Claude
export $(cat .env | xargs) # o carga las variables como prefieras
python src/main.py
cat output/proposal.md
```

## Ajustar las fuentes

En `src/fetch_news.py`:
- `FEEDS` — lista de feeds RSS. Añade, quita o sustituye entradas según
  interese.
- `HN_QUERIES` — términos de búsqueda en Hacker News.
- `REDDIT_SUBREDDITS` — subreddits a consultar.

Si una fuente falla o una URL deja de funcionar, el resto se siguen
procesando con normalidad (se imprime un aviso en los logs de Actions, no
corta la ejecución).

**Nota sobre Reddit**: el endpoint JSON público que se usa no requiere
autenticación, pero Reddit puede aplicar límites de peticiones más estrictos
a IPs sin identificar (como las de los runners de GitHub Actions) según el
momento. Si empieza a devolver errores 403/429 de forma persistente, la
alternativa es crear una app en
[reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) y usar
`PRAW` con credenciales OAuth en vez del endpoint público.

## Entregado por

Proyecto creado durante las prácticas de Marta en QuantumSec España como
herramienta para automatizar la propuesta de temas del calendario editorial.
Pensado para poder transferirse a la cuenta/organización de GitHub de
QuantumSec sin dependencias externas más allá de una clave de Anthropic
opcional.
