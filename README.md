# QuantumSec Content Bot

Bot que cada domingo busca noticias de ciberseguridad de los últimos 30 días
y genera 5-8 propuestas de contenido (tema, formato sugerido, resumen y
fuente) de dos formas:

- Abre un **Issue** en este repositorio con la propuesta en texto, para que
  quede como histórico.
- Actualiza un **calendario visual** (`docs/index.html`, publicado con
  GitHub Pages) que reparte esas propuestas entre los días de la semana
  siguiente — sin que nadie tenga que teclear nada a mano.

Son **propuestas para revisar**, no contenido aprobado: alguien del equipo
decide qué se usa de verdad. El bot nunca publica en redes ni toca el
calendario de producción — solo investiga y sugiere.

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
3. `src/main.py` orquesta los pasos anteriores: escribe `output/proposal.md`
   (para el Issue) y llama a `src/calendar_data.py`, que reparte las
   propuestas entre los días de la semana siguiente y actualiza
   `docs/data/calendar.json`. Si se relanza en la misma semana, sustituye
   esas entradas en vez de duplicarlas.
4. `docs/index.html` es una página estática (sin dependencias, sin build)
   que lee `docs/data/calendar.json` y lo pinta como un calendario: una
   columna por día, con título, resumen, formato sugerido y fuente de cada
   propuesta.
5. `.github/workflows/weekly-proposal.yml` ejecuta todo lo anterior cada
   domingo (vía GitHub Actions, sin necesidad de ningún servidor propio),
   abre el Issue y hace commit del `calendar.json` actualizado.

No hace falta pagar ni mantener ningún servidor: todo corre en los runners
gratuitos de GitHub Actions (2.000 minutos/mes incluidos en repos privados,
ilimitados en repos públicos) y se publica gratis con GitHub Pages.

## Puesta en marcha

1. **Activar Actions**: en un fork o al importar este repo, ve a la pestaña
   *Actions* de GitHub y actívalas si no lo están ya.
2. **(Opcional) Añadir la clave de Claude**: en *Settings → Secrets and
   variables → Actions → New repository secret*, añade `ANTHROPIC_API_KEY`
   con una clave de la [consola de Anthropic](https://console.anthropic.com).
   Sin esta clave el bot sigue funcionando en modo simple.
3. **Activar el calendario visual (GitHub Pages)**: en *Settings → Pages*,
   en "Build and deployment" elige *Source: Deploy from a branch*, rama
   `main`, carpeta `/docs`, y guarda. En uno o dos minutos el calendario
   estará en `https://<usuario-o-org>.github.io/<repo>/`.
4. **Probarlo manualmente**: en la pestaña *Actions*, elige el workflow
   "Propuesta semanal de contenido" y pulsa *Run workflow* para lanzarlo sin
   esperar al domingo.
5. Cada domingo a las 20:00 (hora de Madrid en verano; ajustar el `cron` en
   `.github/workflows/weekly-proposal.yml` si cambia el horario) se abrirá
   un nuevo Issue y se actualizará el calendario automáticamente.

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate  
pip install -r requirements.txt
cp .env.example .env       
export $(cat .env | xargs) 
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

## Relación con el calendario editorial existente

Este calendario (`docs/index.html`) es independiente del dashboard de
producción en `martaic/Calendario-editorial`: aquí solo se ven las
**propuestas automáticas** de la semana (investigación + sugerencia), sin
estados de aprobación ni de producción. Si una propuesta se decide usar de
verdad, se sigue pasando manualmente al calendario de producción como hasta
ahora. Son dos herramientas con propósitos distintos: una investiga y
sugiere, la otra hace seguimiento del trabajo real.

## Si se transfiere el repo a QuantumSec

Al cambiar de cuenta/organización de GitHub, actualiza el enlace a "Issues"
que hay al principio de `docs/index.html` (está escrito como
`martaic/quantumsec-content-bot`) para que apunte al repo en su nueva
ubicación.

## Entregado por

Proyecto creado durante las prácticas de Marta en QuantumSec España como
herramienta para automatizar la propuesta de temas del calendario editorial.
Pensado para poder transferirse a la cuenta/organización de GitHub de
QuantumSec sin dependencias externas más allá de una clave de Anthropic
opcional.
