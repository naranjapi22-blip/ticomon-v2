# Instrucciones para Codex

## Identidad del proyecto

TicoMon es un motor de juego cuya primera interfaz es Discord. Discord es una
interfaz, no parte del dominio. El Core debe poder probarse sin Discord,
Railway ni PostgreSQL.

## Arquitectura y dependencias

- `core/`: reglas y objetos del dominio del juego. No importa Discord ni
  detalles de persistencia o infraestructura externa.
- `application/`: orquesta casos de uso y coordina servicios del Core con
  repositorios o puertos.
- `infrastructure/`: implementa persistencia y servicios externos, incluidos
  PostgreSQL/Neon y sus mapeadores.
- `interfaces/discord/`: cogs, vistas, botones y adaptadores de interacción;
  convierte entradas de Discord en llamadas a Application/Core y presenta sus
  resultados.
- `rendering/`: renderizadores y recursos visuales de presentación; no debe
  asumir reglas de negocio.
- `test/`: pruebas organizadas por capa, con dobles y fakes para evitar
  dependencias externas en las pruebas unitarias.

Las dependencias de adaptación apuntan hacia el Core. Application puede
orquestar el Core; Infrastructure implementa los contratos usados por la
aplicación; Discord depende de Application/Core para interactuar con el juego.
No introduzcas imports inversos desde Core hacia Discord, Infrastructure o
detalles de base de datos.

El Core devuelve objetos y resultados del dominio, nunca embeds, vistas ni
componentes de Discord. Cada dato debe tener una sola fuente de verdad y las
reglas de negocio no deben duplicarse entre capas.

Spawn normal y Safari son sistemas separados. Las formas regionales son
exclusivas de Safari. Reutiliza los resolvers y catálogos existentes para
variantes y especies; no mantengas listas paralelas.

## Filosofía de implementación

- Resuelve el problema actual, no escenarios futuros hipotéticos.
- Evita sobreprogramación, abstracciones prematuras y refactors no solicitados.
- Prefiere cambios pequeños, directos y verificables.
- Reutiliza patrones existentes cuando sean adecuados.
- No introduzcas capas, servicios, tablas, configuraciones o dependencias sin
  necesidad demostrada.
- No modifiques módulos fuera del alcance salvo que sea indispensable.
- No añadas funcionalidades que el usuario no pidió.
- Prefiere claridad antes que código ingenioso.
- Antes de agregar una responsabilidad, determina qué módulo debe ser dueño de
  ese conocimiento.
- No cambies pesos, captura, datos persistidos o balance fuera del alcance
  explícito de la tarea.

## Pruebas y validación

El proyecto usa Python 3.11 y Poetry. El bootstrap confirmado por el proyecto
y por CI es:

```powershell
poetry install --no-interaction
```

Comandos de validación:

```powershell
poetry run pytest -q path/to/test_file.py
poetry run ruff check .
poetry run black --check .
git diff --check
pre-commit run --files <archivos-cambiados>
```

Para la suite completa local se usa:

```powershell
poetry run pytest -q
```

El script `python scripts/check_all.py` ejecuta ese mismo comando:

```powershell
python scripts/check_all.py
```

La validación de unidad que usa CI, sin pruebas Neon, es:

```powershell
poetry run pytest -q -m "not neon_db"
```

Con `NEON_DATABASE_URL` disponible, las pruebas de Neon se ejecutan así:

```powershell
poetry run pytest -q -m neon_db
```

CI está definido en `.github/workflows/ci.yml`. Usa Python 3.11, instala con
Poetry, ejecuta Ruff y Black en `lint`, la suite `not neon_db` en `unit-tests`,
y `neon_db` condicionalmente en `neon-tests`. Pre-commit es una validación
local adicional, no un job separado de CI.

Orden recomendado: inspeccionar el estado, ejecutar pruebas focalizadas,
Ruff, Black, `git diff --check`, pre-commit y después la suite completa. Si una
herramienta reformatea archivos, revisa el diff, conserva solo cambios
intencionados y repite las validaciones. Nunca ocultes, ignores ni desactives
pruebas fallidas.

La configuración vigente está en `pyproject.toml` y
`.pre-commit-config.yaml`: Black y Ruff usan longitud 88 y objetivo Python
3.11; pytest descubre pruebas bajo `test/` y define el marcador `neon_db`.

## Reglas para tests

- Todo cambio de comportamiento debe tener pruebas.
- Prefiere pruebas unitarias del Core.
- No dependas de Discord, Railway ni servicios externos para validar reglas
  del dominio.
- Ejecuta primero los tests específicos del módulo cambiado y después la
  suite completa.
- No alteres tests solo para hacer pasar una implementación incorrecta.

## Flujo de trabajo con Git

- Inspecciona el estado inicial con Git antes de modificar archivos.
- No sobrescribas cambios ajenos.
- Mantén el diff limitado al alcance aprobado y revísalo antes del commit.
- Ejecuta todas las validaciones necesarias.
- Cuando el cambio solicitado esté terminado y validado, crea el commit
  directamente sin pedir permiso adicional.
- Usa un mensaje de commit convencional y descriptivo.
- Detente después del commit.
- No hagas push salvo instrucción explícita.
- Informa hash, mensaje, archivos incluidos, validaciones y estado final del
  working tree.

## Conducta ante ambigüedad

- Inspecciona primero código, pruebas y documentación existentes.
- Escoge la solución más pequeña compatible con el diseño actual.
- No conviertas una tarea limitada en un rediseño.
- Menciona los supuestos relevantes en el resumen final.
- Detente y explica el conflicto cuando una solicitud contradiga una regla del
  dominio o implique pérdida de datos.
