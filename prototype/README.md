# Prototype: phone-first bowling throw

Este es el prototipo de **#15**: valida el esquema de tiro con el celular Android
antes de meter el juego completo. No es la consola final.

## Qué hace

- Sirve una PWA de controlador desde `controller-web/`.
- Levanta un servidor HTTP/WebSocket en `127.0.0.1:8443`.
- Muestra un QR y una escena 3D mínima: una paleta que se inclina con el teléfono.
- Mantenés **THROW**, hacés el swing y al soltar calcula velocidad, dirección y efecto.
- Graba las muestras crudas en `~/.local/share/toxinator/traces/phone-*.jsonl`.

## Probar con Android por USB (recomendado para el primer intento)

Requisitos: `adb` con el teléfono autorizado, Chrome Android, `uv`.

```bash
uv sync
adb reverse tcp:8443 tcp:8443
uv run toxinator dev phone
```

1. Escaneá el QR de la ventana, o abrí la URL que imprime la consola.
2. Tocá **Empezar** y aceptá el permiso de movimiento si aparece.
3. Mové el teléfono: la paleta debería inclinarse.
4. Mantené **THROW**, hacé el swing y soltá. La consola muestra `speed`, `spin` y `conf`.

`localhost` es un contexto seguro, así que los sensores funcionan por `adb reverse`
sin certificados.

## Probar por LAN (HTTPS)

Los sensores necesitan un contexto seguro. Servir por `http://192.168.x.x` no alcanza.

```bash
uv run toxinator dev phone \
  --host 0.0.0.0 \
  --url https://192.168.1.50:8443 \
  --tls-cert cert.pem \
  --tls-key key.pem
```

El certificado tiene que ser confiado por Android (CA local tipo `mkcert` o un
dominio público con Let's Encrypt DNS-01). Si no, Chrome bloquea los sensores.

## Qué mirar

- ¿La paleta sigue el tilt sin saltos?
- ¿La dirección del `throw` coincide con el swing?
- ¿La potencia distingue un swing suave de uno fuerte?
- ¿El efecto (`spin`) tiene sentido o está dominado por ruido?
- ¿Hay latencia noticeable entre el movimiento y la paleta?

Anotá 10–20 tiros con cada variante y adjuntá el `.jsonl` o un clip al ticket #15.

## Limitaciones

- Todavía no hay adaptador de Wiimote; el primer corte es phone-only.
- El token es una protección mínima, no autenticación fuerte.
- No hay TLS automático ni PWA instalable completa.
- El detector de `throw` es deliberadamente simple; los umbrales se ajustan después.
