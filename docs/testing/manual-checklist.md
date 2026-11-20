# Checklist manual de pruebas

Validación con hardware real, GPU y performance. No corre en CI. Es gate de
release: cada ítem se marca **pass**, **fail** o **blocked** con commit, fecha y
hardware.

## Cómo registrar una corrida

Copiá esta tabla al issue de release o al PR de validación:

| Campo | Valor |
|---|---|
| Commit | |
| Fecha | |
| Máquina / distro | |
| GPU / driver | |
| Android | modelo, versión, Chrome |
| Teclado / mouse | layout, modelo |
| Resultado global | pass / fail / blocked |

Para cada ítem: **pasos → esperado → resultado → evidencia** (log, captura o
video corto). Un `blocked` no es un `pass`.

## Celular / PWA

- [ ] **QR y pairing**: escanear el QR de `toxinator dev phone`.
      *Esperado*: la PWA abre, se vincula y aparece como `phone` con token.
- [ ] **HTTPS**: aceptar el certificado local una vez.
      *Esperado*: carga sin errores; sensores y cámara piden permiso.
- [ ] **Layout vertical**: abrir en vertical.
      *Esperado*: × ○ □ △, `options`, L1/R1, stick y zona táctil visibles; nada
      tapado por notch; sin scroll.
- [ ] **Layout landscape**: girar a horizontal.
      *Esperado*: misma paridad funcional, sin botones cortados; el giro no
      corta la conexión ni deja botones apretados.
- [ ] **Orientación por juego**: lanzar un juego con `orientation = "portrait"` o
      `"landscape"` y girar el teléfono al revés.
      *Esperado*: aparece "Girá el teléfono"; al girar desaparece.
- [ ] **Candado**: bloquear la orientación desde ajustes y girar.
      *Esperado*: el layout queda fijo; "LIBERAR" vuelve a auto.
- [ ] **Stick**: arrastrar desde el centro en las cuatro direcciones.
      *Esperado*: `move_x`/`move_y` llegan al juego; deadzone; al soltar vuelve
      al centro y no queda pegado.
- [ ] **Zona táctil**: tocar y arrastrar.
      *Esperado*: `pointer` absoluto, sin coordenadas invertidas; el dot sigue
      el dedo; al soltar se limpia.
- [ ] **Botones**: × ○ □ △, `options`, L1, R1.
      *Esperado*: cada uno llega como nombre canónico; ×/○ también emiten los
      alias `A`/`B`. Sin dobles pulsaciones.
- [ ] **Sensores**: inclinar/rotar el teléfono.
      *Esperado*: `accel`, `gyro` y orientación a 60 Hz; fallback a stick/touch
      si no hay permisos.
- [ ] **Calibración**: adoptar pose neutra y calibrar.
      *Esperado*: la lectura β/γ vuelve a 0 y el juego recibe orientación
      relativa; repetible.
- [ ] **Feedback**: entrar a un juego y tocar el aviso.
      *Esperado*: suena el tono y vibra (Android Chrome/Samsung); sin bloquear
      si el navegador no lo soporta. iPhone no vibra desde la web.
- [ ] **Panel**: lanzar un juego con `[controller.panel]`.
      *Esperado*: la imagen aparece sobre el mando, se expande/colapsa y no
      captura input. `ctx.phone.panel()`/`clear_panel()` la cambian.
- [ ] **Cámara**: lanzar un juego con `camera = true` sobre HTTPS.
      *Esperado*: aparece el botón de foto, la cámara frontal abre, la captura
      se sube a `/api/photo` y la consola la recibe. Sobre HTTP el botón avisa
      que hace falta HTTPS.
- [ ] **Latencia**: medir ping/eventos y percepción del gesto.
      *Esperado*: <50 ms típico en LAN 5 GHz; anotar 2.4 GHz y distancia.
- [ ] **Background/foreground**: bloquear el teléfono y volver.
      *Esperado*: reconexión o pausa; el input no queda pegado.
- [ ] **Wi-Fi drop**: alejarse del AP o desactivar Wi-Fi.
      *Esperado*: aviso de desconexión, gracia 30 s, reconexión.
- [ ] **Dos teléfonos**: 2 jugadores.
      *Esperado*: tokens distintos, slots distintos, sin cruce.
- [ ] **PWA install**: agregar a pantalla de inicio y abrir standalone.
      *Esperado*: misma funcionalidad; sin barra del navegador.
- [ ] **Protocolo**: abrir un cliente con `protocol: 1`.
      *Esperado*: la consola responde `bad-protocol` y cierra; la PWA muestra el
      aviso de recargar.

## Teclado y mouse

- [ ] **Launcher sin celular**: abrir `toxinator`.
      *Esperado*: el QR aparece, pero flechas/Enter/mouse funcionan; el resumen
      muestra `TECLADO`.
- [ ] **Navegación**: flechas y mouse.
      *Esperado*: el foco se mueve por filas/columnas; el puntero del mouse
      también navega; sin repetición con el mouse quieto en el centro.
- [ ] **Atajos**: `S` ajustes, `C` celular, `D` ficha.
      *Esperado*: no chocan con WASD (el launcher desactiva WASD en el hub).
- [ ] **Juego sin celular**: `toxinator play maldito-pino`.
      *Esperado*: WASD/flechas mueven o apuntan, Enter/J tira, Esc/K vuelve;
      `primary_frame()` usa el teclado.
- [ ] **Slot**: `--keyboard-slot 6` y `--no-keyboard`.
      *Esperado*: el simulador usa otro slot o desaparece sin romper el launcher.
- [ ] **Prioridad**: con celular y teclado conectados.
      *Esperado*: `primary_frame()` prefiere el celular; el teclado no roba P1.

## Launcher

- [ ] **Inicio**: abrir el launcher en 1080p.
      *Esperado*: sin texto cortado, foco visible.
- [ ] **Mandos**: conectar 1–4 celulares; asignar y liberar slots.
      *Esperado*: estados online/offline/warn correctos; gracia 30 s.
- [ ] **Join/leave**: sumar y sacar un mando en caliente.
      *Esperado*: el slot se actualiza sin reiniciar.
- [ ] **Mando por juego**: lanzar un juego con `[controller]`.
      *Esperado*: layout, orientación, labels, panel y cámara del celular
      cambian; al volver al launcher se resetean.
- [ ] **Feedback**: golpe/punto en Maldito Pino.
      *Esperado*: al entrar al juego aparece **ACTIVAR SONIDO Y VIBRACIÓN**; al
      tocarlo suena un tono y vibra Android. Sin bloquear si no lo soporta.
- [ ] **HTTPS sin CA**: `uv run toxinator --cloudflare`.
      *Esperado*: con `cloudflared` instalado, el QR usa
      `https://...trycloudflare.com` y Chrome habilita sensores/cámara.
- [ ] **Lanzar/salir**: entrar a Maldito Pino y volver.
      *Esperado*: sin parpadeo de ventana; el launcher queda igual.
- [ ] **4 mandos**: teléfonos + teclado a la vez.
      *Esperado*: 4 slots de teléfono, sin conflictos; el teclado no ocupa un
      chip de P1–P4.

## Maldito Pino

- [ ] **Partida con celular**: 10 turnos, 1 jugador.
      *Esperado*: scoring de pleno/spare/abierto correcto; apuntar con pointer,
      cargar con × y soltar para tirar.
- [ ] **Partida con teclado/mouse**: sin celular.
      *Esperado*: misma partida; mouse apunta, Enter/J carga y suelta, Esc/K
      vuelve.
- [ ] **10º turno**: pleno/spare con 3 tiros.
      *Esperado*: bonificaciones correctas.
- [ ] **Desempate**: empate al final.
      *Esperado*: ronda súbita hasta ganador.
- [ ] **Hot-seat**: 2–4 jugadores con mando compartido.
      *Esperado*: el turno activo se reasigna; el marcador no se mezcla.
- [ ] **Práctica**: tiros ilimitados y reset por tiro.
      *Esperado*: sin puntaje persistente.
- [ ] **Física**: bola 7 kg, pinos 1.5 kg, CCD.
      *Esperado*: sin tunneling; pinos caídos estables; sin jitter visible.
- [ ] **Desconexión**: sacar el mando en el turno.
      *Esperado*: pausa/aviso; reconexión continúa la partida.

## Performance

- [ ] **60 FPS a 1080p** en la escena de bolos, 1 jugador.
      *Esperado*: frametime estable; sin stutter al lanzar.
- [ ] **4 jugadores**: split-screen o hot-seat según el modo.
      *Esperado*: 60 FPS o degradación explícita.
- [ ] **Input <50 ms**: medir con overlay/stats y video.
      *Esperado*: dentro del target; anotar outliers.
- [ ] **Arranque**: de launcher a juego.
      *Esperado*: <3 s en el hardware de referencia.
- [ ] **Memoria**: 30 min de partida.
      *Esperado*: sin crecimiento sostenido.

## i18n

- [ ] **Español default**: primer arranque sin ajuste.
      *Esperado*: todo en español; fechas/números con formato `es`.
- [ ] **Inglés**: cambiar a `en`.
      *Esperado*: launcher y juego en inglés; sin claves crudas.
- [ ] **Fallback**: juego sin `en` en el manifest.
      *Esperado*: cae a `es` con aviso no bloqueante.
- [ ] **Controlador**: idioma del PWA.
      *Esperado*: arranca con `lang` del QR; cambia por WebSocket.
- [ ] **Pseudo-locale** (dev): `TOXINATOR_LANG=qps`.
      *Esperado*: texto expandido; sin strings hardcodeados visibles.

## Blockers conocidos

- **Android**: disponible; el mando v2 es la referencia.
- **Wiimote**: descartado ([ADR-0007](../adr/0007-phone-controller-v2.md)).
- **Avatares**: la captura de foto existe; el editor llega en el milestone 2.
- **Playwright**: no se automatiza la PWA en este esfuerzo; el checklist es
  manual.
