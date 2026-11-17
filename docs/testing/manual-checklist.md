# Checklist manual de pruebas

Validación con hardware real, GPU y performance. No corre en CI. Es gate de
release: cada ítem se marca **pass**, **fail** o **blocked** con commit, fecha y
hardware. Los ítems asumen que el runtime y el launcher ya existen; hoy el repo
todavía no tiene código ejecutable.

## Cómo registrar una corrida

Copiá esta tabla al issue de release o al PR de validación:

| Campo | Valor |
|---|---|
| Commit | |
| Fecha | |
| Máquina / distro | |
| GPU / driver | |
| Wiimote | modelo, batería |
| Android | modelo, versión, Chrome |
| Gamepad | modelo |
| Resultado global | pass / fail / blocked |

Para cada ítem: **pasos → esperado → resultado → evidencia** (log, captura o
video corto). Un `blocked` no es un `pass`.

## Wiimote

- [ ] **Pairing**: mantener 1+2 o el botón rojo; el Wiimote aparece en BlueZ y
      el hub lo lista como `wiimote` con `buttons`, `motion` y `battery`.
      *Esperado*: pairing sin `bluetoothctl` manual; reconexión tras dormir.
- [ ] **Botones**: A, B, 1, 2, +, -, Home, D-pad y cruces.
      *Esperado*: cada botón llega al `ControllerFrame` correcto.
- [ ] **Acelerómetro**: inclinar el mando; `accel` cambia en los tres ejes.
      *Esperado*: valores estables, sin saltos; calibración de pose neutra.
- [ ] **Swing/throw**: swing de bolos con B; el gesto detecta fases y release.
      *Esperado*: el tiro sale con potencia/efecto coherentes; repetible.
- [ ] **Desconexión**: apagar el Wiimote en partida.
      *Esperado*: el slot queda en gracia 30 s, aviso de plataforma, reconexión
      al mismo slot.
- [ ] **Batería**: leer nivel y avisar bajo.
      *Esperado*: nivel plausible; sin polling agresivo.
- [ ] **Rumble**: vibración binaria en un evento de prueba.
      *Esperado*: on/off; no bloquea el game loop.
- [ ] **IR/pointer** (opcional): si hay IR bar DIY, apuntar y calibrar.
      *Esperado*: pointer normalizado; si no hay bar, el celular cubre pointer.
- [ ] **Dos Wiimotes**: 2 mandos en slots distintos.
      *Esperado*: sin cruce de frames; 4 slots siguen disponibles.

## Android

- [ ] **QR y pairing**: escanear el QR de `toxinator dev phone`.
      *Esperado*: el celular abre la PWA y aparece como `phone` con token.
- [ ] **HTTPS**: aceptar el certificado local una vez.
      *Esperado*: la PWA carga sin errores de certificado; los sensores piden
      permiso.
- [ ] **Sensores**: inclinar/rotar el teléfono; `accel`, `gyro` y orientación
      llegan a 60 Hz.
      *Esperado*: sin permisos denegados; fallback touch si no hay sensores.
- [ ] **Calibración**: adoptar pose neutra y calibrar.
      *Esperado*: el eje de la pista coincide con el gesto; repetible.
- [ ] **Touch**: tocar la pantalla; pointer/touch llegan al juego.
      *Esperado*: multitouch si el juego lo usa; sin coordenadas invertidas.
- [ ] **Latencia**: medir ping/eventos y percepción en el swing.
      *Esperado*: <50 ms típico en LAN 5 GHz; anotar 2.4 GHz y distancia.
- [ ] **Background/foreground**: bloquear el teléfono y volver.
      *Esperado*: reconexión o pausa; el input no queda pegado.
- [ ] **Wi-Fi drop**: alejarse del AP o desactivar Wi-Fi.
      *Esperado*: aviso de desconexión, gracia 30 s, reconexión.
- [ ] **Dos teléfonos**: 2 jugadores.
      *Esperado*: tokens distintos, slots distintos, sin cruce.
- [ ] **Idioma**: cambiar `es`/`en` en la consola con el celular conectado.
      *Esperado*: el PWA recibe `language` y actualiza sus textos.
- [ ] **PWA install**: agregar a pantalla de inicio y abrir standalone.
      *Esperado*: misma funcionalidad; sin barra del navegador.

## Gamepad y teclado

- [ ] **Gamepad real**: conectar un gamepad estándar.
      *Esperado*: D-pad/stick, A, B, Start; aparece como `gamepad`.
- [ ] **Simulador**: `toxinator --sim --sim-preset bowling`.
      *Esperado*: botones/ejes/motion responden; `F1` muestra el estado.
- [ ] **Preset del juego**: el manifest carga el preset del juego.
      *Esperado*: el preset correcto aparece en el overlay; fallback a `default`.

## Launcher

- [ ] **Inicio**: abrir el launcher en 1080p.
      *Esperado*: LIGA · Noche, sin texto cortado, foco visible.
- [ ] **Plantel**: conectar 1–4 mandos; asignar y liberar slots.
      *Esperado*: estados online/offline/warn correctos; gracia 30 s.
- [ ] **Join/leave**: sumar y sacar un mando en caliente.
      *Esperado*: el slot se actualiza sin reiniciar.
- [ ] **Idioma**: cambiar `es`/`en` en ajustes.
      *Esperado*: todo el launcher se re-renderiza al instante.
- [ ] **Ficha**: abrir detalle, cambiar formato y volver.
      *Esperado*: foco y estado consistentes.
- [ ] **Lanzar/salir**: entrar a Maldito Pino y volver.
      *Esperado*: sin parpadeo de ventana; el launcher queda igual.
- [ ] **Estados**: error de capacidades, liga vacía, sumar celular, apagar.
      *Esperado*: copy correcto, navegación con mando/teclado.
- [ ] **4 mandos**: Wiimote + teléfonos + gamepad a la vez.
      *Esperado*: 4 slots, sin conflictos.

## Maldito Pino

- [ ] **Partida completa**: 10 turnos, 1 jugador.
      *Esperado*: scoring de pleno/spare/abierto correcto.
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
- [ ] **Pausa**: pausa de sistema y de juego.
      *Esperado*: el juego se congela; el overlay de plataforma responde.
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

- **Wiimote**: sin pilas; los ítems de Wiimote quedan `blocked` hasta tenerlas.
- **Android**: disponible; falta la PWA y el runtime.
- **Performance**: falta la escena de bolos; se mide en el primer corte jugable.
- **Playwright**: no se automatiza el PWA en este esfuerzo; el checklist es
  manual.
