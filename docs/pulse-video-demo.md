# PULSE CRM: demo local para video

Esta base contiene solo personajes, empresas y mensajes ficticios. Funciona con el proyecto Docker Compose `pulse-crm-demo`, la base `pulse_demo`, el proveedor de WhatsApp `fake` y almacenamiento local de adjuntos. No usa credenciales, webhooks ni URLs de Meta o Railway.

## Acceso

- URL: http://127.0.0.1:15173/login
- Supervisor: `demo@pulse.test` / `PulseVideoLocal2026!`
- Vendedores: `tomas@pulse-demo.invalid` y `sofia@pulse-demo.invalid`, con la misma contraseña local.
- Para reemplazar la contraseña en un seed nuevo: `PULSE_DEMO_PASSWORD='otra-clave-demo-larga' ./scripts/seed-pulse-video-demo.sh --reset`.

La contraseña predeterminada es deliberadamente local y ficticia. No reutilizarla en producción.

## Encender, poblar y repetir

Desde la rama `demo/pulse-video`:

```sh
./scripts/pulse-demo.sh up -d --build
./scripts/seed-pulse-video-demo.sh --reset
./scripts/seed-pulse-video-demo.sh
```

La segunda ejecución detecta el conjunto completo y no escribe nada. `--reset` acepta únicamente raíces reconocidas como datos propios de esta demo; rechaza datos ajenos. El seed verifica rama, URL de base, entorno de desarrollo, proveedor falso, almacenamiento local y ausencia de variables de Railway/Meta antes de escribir. No ejecutar `docker compose down -v`: eliminaría el volumen aislado sin necesidad.

## Escenas sugeridas

1. **Resumen comercial:** filtro “Este mes” muestra actividad, oportunidades activas y distribución por origen/provincia; “Últimos 3 meses” enseña el recorrido completo.
2. **Pipeline:** 3 nuevas, 3 cotizadas, 2 en negociación. NovaTech tiene consulta web, cotización, historial y nota fijada; Grupo Prisma tiene contexto de venta.
3. **Ganadas y pérdidas:** cinco ganadas y tres perdidas con responsables, productos y causas distintas.
4. **WhatsApp:** Nexo Solutions muestra el intercambio comercial; Delta Digital tiene dos imágenes y un PDF; Urbania tiene audio Ogg; Estudio Norte está cerca de las 24 horas; Vértice tiene la ventana vencida.
5. **Notificaciones:** seis eventos repartidos entre pendientes y leídos.

## Contenido y límites del modelo

El seed crea 3 usuarios, 16 clientes, 6 productos, 16 oportunidades (8 activas, 5 ganadas, 3 perdidas), 5 conversaciones, 6 notificaciones y 4 adjuntos locales. Las fechas abarcan cerca de 80 días. Todos los nombres, correos `.invalid`, teléfonos y mensajes son inventados.

El CRM conserva la etiqueta de unidad **kg** en las cotizaciones y los gráficos aunque los productos de la demo son planes y servicios; el seed usa cantidad `1` para cada cotización. Se mantuvo la lógica actual de negocio sin cambiar el frontend para esta tarea. La app admite notificaciones de “nuevo lead” y “oportunidad sin movimiento”; las seis escenas usan esos tipos existentes. El archivo de audio es un tono sintético breve para demostrar el reproductor, sin voz real.
