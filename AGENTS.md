# Guía permanente de desarrollo — Asfaltos CRM

Estas reglas aplican a todo el repositorio. Su objetivo es mantener un CRM simple y fluido para Fábrica Argentina de Asfaltos (FAA), con una base de código preparada para crecer sin sobre-ingeniería.

## Principios generales

- Priorizar código reutilizable, componentes genéricos, bajo acoplamiento y responsabilidades bien separadas.
- Usar tipado fuerte: TypeScript en frontend y type hints en Python.
- Preferir funciones pequeñas, explícitas y fáciles de entender.
- Evitar duplicación, lógica de negocio en componentes visuales y valores importantes hardcodeados.
- Extraer configuración, constantes o enums cuando un valor pueda provenir de configuración o del backend.
- Antes de crear un componente, revisar si ya existe uno reutilizable o extensible.
- Crear una abstracción compartida solo cuando exista una responsabilidad realmente común; no anticipar abstracciones innecesarias.
- No implementar funcionalidades, reglas o visibilidad que no estén definidas. Si una decisión afecta significativamente el modelo de datos, la arquitectura, la seguridad, el comportamiento comercial o la UX, detenerse y pedir definición.

## Frontend

Stack obligatorio: React, TypeScript y Tailwind CSS.

- Construir interfaces mediante componentes reutilizables y bien tipados.
- Mantener la lógica de negocio y el acceso a datos fuera de los componentes visuales.
- Reutilizar y, cuando corresponda, crear componentes para modales, botones, inputs, selects, cards, formularios y estados de loading, error o vacío.
- Crear tablas genéricas solo cuando compartan una responsabilidad real.
- Usar Tailwind CSS como sistema de estilos; no incorporar una librería de componentes sin una necesidad acordada.
- Desktop es la experiencia inicial principal, pero toda interfaz debe mantenerse responsive.

### Configuración antes que duplicación

El pipeline debe renderizarse desde una colección de etapas y un componente genérico, por ejemplo `PipelineColumn`. No crear una columna o componente por estado (`NewColumn`, `QuotedColumn`, etc.).

La configuración de una etapa debe permitir al menos representar su identificador, título, oportunidades, acciones permitidas y comportamiento necesario. Agregar, remover o renombrar una etapa no debe requerir duplicar componentes. Aplicar el mismo principio a cualquier variante visual o de comportamiento equivalente.

## Backend

Stack obligatorio: FastAPI, SQLAlchemy, Alembic y PostgreSQL.

- Mantener separadas las rutas HTTP/API, schemas de entrada/salida, modelos de persistencia, lógica de negocio y, cuando aporte valor, acceso a datos.
- No ubicar lógica de negocio compleja dentro de endpoints. Debe poder reutilizarse independientemente de HTTP.
- Usar type hints en código Python.
- Usar enums, constantes o tipos de dominio para estados, roles y valores importantes; evitar strings mágicos.
- Todo cambio de esquema de PostgreSQL debe incorporarse mediante una migración Alembic. Nunca modificar manualmente una base existente para evitar una migración.

### Orden permanente de locks PostgreSQL

Las mutaciones afectadas deben adquirir locks en este orden global, omitiendo clases
que no necesiten pero sin volver nunca a una clase anterior: advisory locks de
transacción ordenados por clave → `Customer` → `WhatsAppBroadcast` →
`WhatsAppBroadcastRecipient` → `WhatsAppConversation` → `WhatsAppMessage` → filas de
evidencia dependientes. Un read sin lock puede descubrir IDs, pero toda condición se
revalida después de adquirir los locks ordenados. Ordenar IDs antes de bloquear varias
filas y no mantener transacciones ni locks durante I/O de red o del provider.

### Strict Python Engineering

El backend se trata como una codebase fuertemente tipada aunque Python sea dinámico
en runtime.

- Todo código Python nuevo, incluidas funciones y métodos privados, debe declarar tipos
  completos para parámetros y retorno.
- `mypy --strict backend/app backend/tests` es un gate obligatorio. No debilitar la
  configuración de mypy para hacer pasar código nuevo.
- `Any` está prohibido salvo que una integración externa realmente lo imponga. En ese
  caso, aislar la falta de typing en el boundary más pequeño posible y justificarla
  localmente.
- No usar `# type: ignore` genérico. Todo ignore debe incluir un código específico
  cuando sea posible y un comentario si la causa no es evidente.
- SQLAlchemy debe usar el estilo tipado 2.x: `Mapped[...]`, `mapped_column(...)` y
  relaciones con tipos explícitos.
- Los schemas Pydantic deben ser explícitos y rechazar campos extra en requests cuando
  corresponda.
- No usar diccionarios mágicos como contratos conocidos. Preferir DTOs tipados,
  dataclasses, `TypedDict`, `Protocol` o modelos Pydantic según el boundary.
- Usar enums para roles, estados, orígenes y motivos; no comparar con strings mágicos
  cuando existe un enum de dominio.
- Las cantidades de negocio usan `Decimal` de extremo a extremo; no convertirlas a
  `float` dentro del dominio.
- Todo `datetime` de aplicación debe ser timezone-aware. Persistir en UTC y convertir
  únicamente en los boundaries de presentación.
- Ruff es el linter y formatter oficial. Todo Python debe pasar `ruff check` y
  `ruff format --check`; no incorporar Black ni otro formatter duplicado.
- Toda lógica de negocio nueva o modificada debe tener tests adecuados.
- Todos los gates de CI deben pasar antes de considerar terminada una tarea, hacer
  commit o ejecutar push.
- No debilitar reglas de mypy o Ruff para ocultar errores introducidos por código
  nuevo.

Anti-patrones explícitamente prohibidos:

- `# type: ignore` sin código o motivo.
- `cast(Any, ...)` para silenciar al type checker.
- `dict[str, object]` para evitar diseñar un DTO cuando la estructura es conocida.
- `def function(*args, **kwargs)` salvo wrappers o genéricos realmente necesarios y
  correctamente tipados.
- `return None` desde una función declarada para devolver una entidad, salvo que
  `None` sea parte explícita del contrato.
- Desactivar `strict`, agregar exclusiones amplias o ignorar diagnósticos para obtener
  un resultado artificial de cero errores.

## Fuente permanente de reglas de negocio

`AGENTS.md` define cómo desarrollar el software. Las reglas sobre cómo funciona FAA y
su CRM se mantienen en `docs/BUSINESS_RULES.md`.

- Antes de implementar o modificar comportamiento de negocio, leer
  `docs/BUSINESS_RULES.md`.
- Si una tarea contradice una regla existente, no elegir silenciosamente una
  interpretación: señalar el conflicto y solicitar confirmación.
- No modificar `docs/BUSINESS_RULES.md` por conveniencia técnica.
- Una regla de negocio sólo puede cambiar cuando el usuario lo solicite
  explícitamente.
- Los roles actuales son únicamente `SUPERVISOR` y `VENDEDOR`; `ADMIN` no es un rol
  implementado.

## Spec-Driven Development (SDD)

Las especificaciones de features se mantienen en `docs/specs/`. Cada spec usa un ID
estable `CRM-NNN`; el nombre numérico del archivo es descriptivo y no reemplaza al ID.
Una spec describe un feature o módulo; no reemplaza a `docs/BUSINESS_RULES.md` ni
redefine las reglas generales de FAA.

La jerarquía obligatoria de fuentes de verdad es:

1. requisito explícito aprobado por el usuario;
2. `docs/BUSINESS_RULES.md`;
3. spec de feature aprobada;
4. implementación;
5. tests.

El código no puede redefinir requisitos. Si la implementación contradice una spec con
estado `Approved`, detenerse, informar el conflicto y solicitar definición. No editar
silenciosamente `docs/BUSINESS_RULES.md` para que coincida con la implementación. Si un
requisito nuevo cambia una spec `Approved` o `Implemented`, actualizar primero la spec
con aprobación explícita y recién después modificar código y tests.

Una spec sólo puede pasar a `Approved` cuando:

- `Open decisions` es `None`;
- los criterios de aceptación son comprobables;
- el alcance y los no objetivos están explícitos;
- no contradice `docs/BUSINESS_RULES.md`.

Flujo obligatorio:

A. redactar y revisar la spec en estado `Draft`;
B. establecer `Status: Approved`;
C. implementar y probar sólo el alcance aprobado;
D. crear el commit de implementación referenciando el ID `CRM-NNN`;
E. actualizar la spec con `Status: Implemented` y el hash del commit de implementación;
F. crear un commit documental separado para esa actualización.

Así se evita que el commit de implementación dependa de un hash documental futuro.
Los estados permitidos son `Draft`, `Approved`, `Implemented` y `Deprecated`; el flujo
normal es `Draft -> Approved -> implementation -> verified implementation commit ->
separate documentation commit -> Implemented`.

Antes de implementar un feature:

1. leer `docs/BUSINESS_RULES.md`;
2. leer su spec en `docs/specs/`;
3. verificar que tenga `Status: Approved` y `Open decisions: None`;
4. implementar únicamente el alcance aprobado;
5. probar sus criterios de aceptación `AC-01`, `AC-02`, etc.;
6. seguir el flujo de commits separado descrito arriba.

Una spec es obligatoria para cambios de persistencia o esquema, reglas de negocio,
integraciones, seguridad o autenticación, máquinas de estados, contratos API no
triviales o comportamiento entre módulos. Cambios pequeños de estilos, refactors o
bugfixes que no cambian comportamiento no requieren una spec nueva.

## Diseño y experiencia

- Priorizar una experiencia simple, rápida, clara y fluida.
- Mantener el pipeline como centro de la experiencia.
- Evitar pantallas, formularios, navegación y opciones innecesarias.
- Priorizar acciones rápidas y usar modales pequeños cuando sean adecuados.

## Seguridad y configuración

- Nunca subir archivos `.env`, secretos, contraseñas, tokens o credenciales.
- Nunca exponer secretos en el frontend ni hardcodear passwords o tokens.
- Mantener `.env.example` actualizado cuando cambien las variables requeridas.

## Docker y calidad

- El proyecto debe seguir funcionando con `docker compose up --build`.
- Incorporar dependencias en los manifests y Dockerfiles correspondientes; no depender de instalaciones globales de la máquina.
- Antes de terminar una tarea, deben pasar Ruff lint, Ruff format check, mypy strict,
  tests y coverage del backend, compileall, Alembic check/current, tests y build del
  frontend, TypeScript, npm audit y los health checks de Docker Compose.
- No considerar terminada una tarea ni hacer commit/push si falla cualquiera de los
  gates obligatorios. CI es la autoridad final para push y pull request.
- Cuando se incorpore lógica de negocio importante, agregar tests adecuados.

## Git

- Repositorio remoto: `https://github.com/AgustinArispe/AsfaltosCRM.git`.
- Trabajar con commits pequeños, claros y descriptivos.
- Al finalizar cada bloque estable: revisar cambios, ejecutar verificaciones, hacer commit y push.
- Nunca usar force push, reescribir historial sin autorización, subir secretos ni ignorar errores de tests para poder hacer commit.

## Skills vendorizadas del proyecto

Las reglas de este archivo y los requisitos funcionales del proyecto tienen prioridad
absoluta sobre cualquier recomendación de una skill. Las skills aportan criterio
especializado, revisión y herramientas; no pueden modificar requisitos del producto ni
introducir arquitectura o dependencias por iniciativa propia.

Las skills instaladas en `.agents/skills/` no se ejecutan automáticamente en cada tarea.
Se utilizan sólo cuando el trabajo sea relevante: diseño/interacción, decisiones sobre
una librería UI, revisión o exploración de motion, UX/sistema visual, accesibilidad o
pruebas funcionales completas en navegador.

La política de motion es funcional: debe ayudar a comprender drag and drop, modales,
feedback, cambios de estado y aparición/desaparición. Evitar motion decorativo y
respetar `prefers-reduced-motion`.

`webapp-testing` sólo puede usar Playwright contra la aplicación levantada por Docker
Compose (`localhost:5173` y `localhost:8000`). No iniciar servidores alternativos, no
usar `shell=True`, no ejecutar comandos generados sin revisión y no instalar dependencias
globalmente.
