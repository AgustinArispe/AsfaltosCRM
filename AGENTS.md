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

## Reglas de negocio conocidas

Estas reglas son requisitos de referencia para implementaciones futuras; no habilitan funcionalidades no solicitadas en la tarea actual.

### Clientes y oportunidades

- El CRM gestiona consultas comerciales de FAA.
- Un cliente puede tener múltiples consultas u oportunidades y cada oportunidad pertenece a un cliente.
- Los datos iniciales de cliente son nombre, empresa, email y teléfono. La provincia está prevista para incorporarse.
- Debe poder distinguirse entre clientes nuevos y antiguos.

### Pipeline y cotizaciones

- Las etapas principales son `NUEVA`, `COTIZADA`, `NEGOCIACION` y `GANADA`.
- Las oportunidades perdidas se almacenan y se consultan mediante búsqueda o filtros; no forman una columna principal del pipeline.
- Al mover una oportunidad de `NUEVA` a `COTIZADA`, es obligatorio registrar uno o más productos cotizados y la cantidad en kilogramos de cada uno.
- FAA cargará inicialmente aproximadamente diez productos. El CRM registra productos y cantidades cotizados, pero no genera presupuestos.
- Al marcar una oportunidad como perdida, conservar la información de cotización y registrar un motivo de pérdida categorizado de manera sencilla.
- El modelo debe registrar cuándo una oportunidad ingresó en su etapa actual, para permitir recordatorios futuros de oportunidades sin avance durante aproximadamente catorce días.
- Las métricas futuras incluyen kilogramos cotizados, ganados y perdidos; productos más consultados y vendidos; y tasa de conversión.

### Origen de leads, recordatorios y usuarios

- Registrar el origen de cada consulta. Orígenes iniciales: `WEB` y `WHATSAPP`; `META` queda previsto para el futuro.
- El CRM no es una bandeja de mensajería y no se implementan conversaciones internas.
- Los recordatorios por email se implementarán más adelante.
- Roles iniciales: `ADMIN` / `SUPERVISOR` y `VENDEDOR`.
- El supervisor podrá administrar usuarios, crear usuarios, eliminar clientes y editar productos.
- La visibilidad de oportunidades por vendedor todavía no está definida. No inventar ni implementar esa regla.

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
- Antes de terminar una tarea, verificar TypeScript, el build del frontend, el backend, los tests existentes, las migraciones cuando corresponda y Docker Compose.
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
