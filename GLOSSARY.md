# Toxinator 3

Contexto de Toxinator 3, la consola personal de juegos 3D en Python, sus mandos y el primer vertical slice de bolos. Los términos canónicos están en español; el código usa el identificador en inglés entre paréntesis.

## Productos

**Toxinator 3 (Toxinator)**:
La consola; el nombre público incluye el `3`, mientras que el paquete e import son `toxinator`.
_Avoid_: Toxinator sin 3 (para el nombre público), wiIAsports (nombre viejo del repo)

**Maldito Pino, hijo de pu&#42;&#42;**:
El primer juego, de bolos. El título canónico es `Maldito Pino, hijo de pu**` y se mantiene en español en ambas locales; “Maldito Pino” es la forma corta. Paquete `maldito-pino`, import `maldito_pino`.
_Avoid_: Pleno (nombre descartado)

## Plataforma

**Consola (Console)**:
El runtime que descubre, lanza y ejecuta juegos, y provee input, audio, assets, ajustes, save, i18n y viewports. No es un juego.
_Avoid_: plataforma, sistema, engine

**Launcher**:
La pantalla de inicio fullscreen desde la que se eligen juegos, se asignan jugadores y mandos, y se cambian ajustes.
_Avoid_: menú principal, home

**Core de plataforma (Platform core)**:
El conjunto de servicios que la consola ofrece a todos los juegos. No incluye reglas ni contenido de juego.
_Avoid_: framework, engine

**Juego (Game)**:
Un plugin de Python con manifest y ciclo de vida que implementa el contrato de juego y contiene uno o más modos.
_Avoid_: app, título

**Contrato de juego (Game contract)**:
La interfaz `Game` y el `GameContext` que un juego implementa y consume; define lifecycle, servicios y límites.
_Avoid_: plugin API, SDK

**Contexto de juego (GameContext)**:
El paquete explícito de escena, viewports y servicios que la consola entrega a un juego.
_Avoid_: environment, globals

**Host de juego (GameHost)**:
El adaptador del runtime que descubre, carga, ejecuta y descarga juegos; in-process ahora, subprocess después.
_Avoid_: loader, runner

**API de la consola (Console API)**:
La versión semver del contrato que un juego declara en `requires_api`.
_Avoid_: SDK version, engine version

**Frontera de API (API boundary)**:
La regla de que `toxinator.api` es el único módulo del runtime que un juego puede importar.
_Avoid_: internal API, public API (ambiguo)

**Servicio de plataforma (Platform service)**:
Una capacidad que la consola ofrece a los juegos a través del contexto: input, audio, assets, settings, save, i18n o logging.
_Avoid_: singleton, global

**Escena (Scene)**:
Un estado o pantalla del juego con update/render/input que el juego empuja o popea en el stack de la consola.
_Avoid_: screen, state (en docs; `Scene` en código)

**Manifiesto de juego (Game manifest)**:
La metadata que declara id, nombre, versión, `requires_api`, jugadores, capacidades, modos, icono y descripción de un juego.
_Avoid_: config, descriptor

**Modo (Mode)**:
Una variante jugable dentro de un juego, como un deporte o un minijuego; el manifest puede declararla como modo lanzable.
_Avoid_: minijuego (cuando es solo una variante), nivel

**Pausa de sistema (System pause)**:
El overlay de la consola para desconexión, pérdida de foco o errores; suspende el juego.
_Avoid_: pause menu, game pause

**Pausa de juego (Game pause)**:
El menú del propio juego para reanudar, reiniciar, ajustar o volver al menú.
_Avoid_: system pause

**Overlay de plataforma (Platform overlay)**:
La UI de la consola que se dibuja sobre un juego para pausa, errores o desconexión de mandos.
_Avoid_: HUD (el HUD es del juego)

## i18n

**Servicio de i18n (I18nService)**:
El servicio de la consola que carga catálogos por dominio y locale, resuelve textos, formatea números/fechas y emite el cambio de idioma.
_Avoid_: translator, localization manager

**Catálogo de textos (Text catalog)**:
El archivo `.po`/`.mo` de un dominio y locale; contiene las traducciones de sus claves.
_Avoid_: diccionario, translations file

**Dominio de traducción (Translation domain)**:
El ámbito de claves de un paquete: `toxinator` para la consola y el id del juego para cada juego.
_Avoid_: namespace, scope

**Clave de texto (Text key)**:
El identificador semántico y estable de un texto (`launcher.featured.play`), independiente del idioma.
_Avoid_: msgid (en docs), label

**Locale**:
El idioma normalizado de la consola (`es`, `en`); las variantes regionales se mapean a la base.
_Avoid_: idioma (para el código), language tag

**Idioma efectivo (Effective locale)**:
El locale que un dominio usa después del fallback; si el juego no soporta el activo, es su `default_locale`.
_Avoid_: idioma final, resolved locale

**Pseudo-locale (qps)**:
Un locale de prueba generado desde `en` con texto expandido y acentuado para detectar strings hardcodeados y truncamiento; no se shipea.
_Avoid_: fake locale, test language

**Placeholder**:
Un hueco con nombre en un texto (`{name}`, `{count}`) que el servicio reemplaza al formatear.
_Avoid_: variable, token

**Asset localizado (Localized asset)**:
Un asset con texto o voz que tiene una versión por locale bajo `assets/<locale>/`, con fallback a `assets/common/`.
_Avoid_: recurso traducido, asset i18n

## Distribución

**Paquete de juego (Game package)**:
La distribución instalable de un juego, con su manifest, versión y punto de entrada.
_Avoid_: repo, plugin (el plugin es el objeto que corre; el paquete es la distribución)

**Repositorio de juegos (Game registry)**:
El índice que lista paquetes de juego, versiones y compatibilidad con la API de la consola.
_Avoid_: store (el repositorio no implica pago), market

**Juego instalado (Installed game)**:
Un paquete de juego descubierto por la consola y listo para lanzar.
_Avoid_: biblioteca, library

**Hot reload**:
La recarga en caliente de un juego local en desarrollo, sin reiniciar la consola.
_Avoid_: live reload, hot swap

**Corte vertical (Vertical slice)**:
Una rebanada fina que atraviesa todas las capas (input → juego → render → launcher) y valida el camino completo antes de ampliar.
_Avoid_: MVP (puede ser más amplio), demo

**Corte phone-only (Phone-only slice)**:
El primer corte vertical, con el celular Android como único mando y una escena 3D mínima; el Wiimote llega después.
_Avoid_: mobile-first (demasiado amplio), phone demo

## Sesión

**Partida (Match)**:
Una sesión de juego con sus reglas (10 turnos de bolos, 3 vueltas de kart). No es el software.
_Avoid_: juego, sesión

**Hot-seat**:
Modo local por turnos en el que los jugadores comparten pantalla y, opcionalmente, un mando.
_Avoid_: pass-and-play (en docs), local versus

**Mando compartido (Shared controller)**:
Un solo mando que se pasa entre jugadores en hot-seat; el hub lo reasigna al slot activo.
_Avoid_: pass-the-controller (en docs), shared pad

**Perfil local (Local profile)**:
Una identidad de jugador guardada en la consola: nombre, color/avatar y mando preferido. No hay cuenta ni nube.
_Avoid_: cuenta, usuario

**Save de juego (Game save)**:
Los datos que un juego persiste (récords, desbloqueos). La consola provee el almacenamiento, no el significado.
_Avoid_: progreso, estado

**Ajustes globales (Global settings)**:
Los ajustes de la consola (idioma, audio, gráficos, accesibilidad) que aplican a todos los juegos.
_Avoid_: configuración, preferencias

## Input

**Hub de input (InputHub)**:
El servicio de la consola que reúne las fuentes de mandos, normaliza sus datos y publica un `InputState` por frame.
_Avoid_: input manager, device manager

**Mando (Controller)**:
Un dispositivo físico o virtual que produce `ControllerFrame`s: Wiimote, celular Android, gamepad o teclado/mouse.
_Avoid_: controlador, control, dispositivo

**Controlador web (Controller web)**:
La PWA Android que la consola sirve por LAN para que el celular actúe como mando; recibe input, estado y el idioma activo.
_Avoid_: phone app, web controller, app del celular

**Descriptor de mando (ControllerInfo)**:
La identidad y las capacidades de un mando conectado, separadas del estado instantáneo: id, source, capabilities, slot, conexión y batería.
_Avoid_: device, controller config

**Slot de jugador (Player slot)**:
Un asiento lógico de 1 a 4 al que se asigna un mando durante una partida; conserva el mando durante la gracia de desconexión.
_Avoid_: player index, jugador

**ControllerFrame**:
Una muestra inmutable y normalizada del estado de un mando en un instante: botones físicos, ejes, aceleración, gyro, orientación, pointer y touch, con timestamp.
_Avoid_: frame, paquete, estado

**Estado de input (InputState)**:
El snapshot inmutable de todos los mandos y slots que el juego lee al inicio de cada frame.
_Avoid_: snapshot, world state

**Evento de input (InputEvent)**:
Un cambio de ciclo de vida (join, leave, asignación, desconexión o calibración) que el hub entrega además del estado.
_Avoid_: callback, signal

**Capacidad (Capability)**:
Una característica que un mando o un juego declara: `buttons`, `axes`, `motion`, `gyro`, `pointer`, `touch`, `haptics`, `screen` o `battery`; el launcher negocia las requeridas y opcionales.
_Avoid_: feature, flag

**Acción (Action)**:
Una intención semántica del juego (`throw`, `gas`, `brake`) producida por el mapeo de input, distinta de un botón físico.
_Avoid_: comando, input

**Mapeo de input (InputMap)**:
La configuración por juego y jugador que traduce botones y ejes a acciones, con deadzone, sensibilidad, inversión y hold/toggle.
_Avoid_: keybinding, controls

**Gesto (Gesture)**:
Un patrón de movimiento reconocido a partir de `ControllerFrame`s, como swing, throw, tilt o aim; se emite como evento con fase, dirección y confianza.
_Avoid_: acción, movimiento

**Pose neutra (Neutral pose)**:
La orientación de referencia que el jugador adopta al empezar; base de la calibración y de los gestos relativos.
_Avoid_: zero pose, rest pose

**Calibración (Calibration)**:
El ajuste de los sensores de un mando (offset/escala de accel, bias de gyro, homografía de pointer) para que sus datos sean consistentes.
_Avoid_: setup, configuración

**Pointer**:
Una coordenada de apuntado normalizada de 0 a 1, válida solo si el mando tiene pointer calibrado (IR o touch/gyro).
_Avoid_: cursor, mouse position

**Eje (Axis)**:
Un valor analógico normalizado de un stick o gatillo; los sticks van de -1 a 1 y los gatillos de 0 a 1.
_Avoid_: stick, trigger (cuando se habla del valor)

**Traza de input (Input trace)**:
Una secuencia grabada de `ControllerFrame`s y eventos usada para tests, replay o depuración.
_Avoid_: log, grabación

**Simulador de mandos (Controller simulator)**:
Un mando falso controlado por teclado, mouse o gamepad que produce `ControllerFrame`s para desarrollar y testear sin hardware.
_Avoid_: emulador, fake controller

## Física

**PhysicsWorld (Mundo físico)**:
El servicio de plataforma que envuelve Bullet, corre a paso fijo y expone cuerpos, materiales y queries.
_Avoid_: physics engine, world manager

**Cuerpo rígido (Rigid body)**:
Un cuerpo con masa que Bullet integra; puede ser dinámico o estático.
_Avoid_: body (en docs), objeto físico

**Cuerpo kinemático (Kinematic body)**:
Un cuerpo de masa infinita que se mueve por transform y empuja a los dinámicos.
_Avoid_: static body, animated collider

**Material físico (Physics material)**:
La combinación de fricción y restitución que se aplica a un cuerpo o superficie.
_Avoid_: surface, material (ambiguo)

**Paso fijo (Fixed step)**:
El intervalo constante de simulación (1/120 s) independiente del framerate.
_Avoid_: tick, frame step

**CCD (Continuous Collision Detection)**:
La detección de colisiones entre pasos para cuerpos rápidos; usa una swept sphere.
_Avoid_: tunneling fix, sweep

**Escala de tiempo (Time scale)**:
El multiplicador de tiempo de la simulación; 0.25 para slow-motion y 0 para pausa.
_Avoid_: slow motion factor, time dilation

**Interpolación (Interpolation)**:
El suavizado de transforms entre pasos físicos para renderizar a 60 FPS.
_Avoid_: smoothing, lerp

**Pino caído (Knocked pin)**:
Un pino cuya orientación o posición supera el umbral de caída; se usa para el scoring.
_Avoid_: fallen pin, down pin

## Render y UI

**Viewport**:
La región de pantalla que renderiza la cámara de un jugador; en split-screen hay una por jugador.
_Avoid_: cámara, panel

**Split-screen**:
La división de una pantalla en varios viewports para multijugador local.
_Avoid_: pantalla dividida (en código), multi-view

**HUD**:
La información 2D que un juego muestra a un jugador sobre la escena (puntos, vueltas, indicadores).
_Avoid_: overlay (el overlay es de plataforma)

## Deportes y kart

**Pista de bolos (Lane)**:
La superficie por la que rueda la bola hacia los pinos.
_Avoid_: pista (sin calificar)

**Turno de bolos (Bowling frame)**:
Uno de los 10 turnos de una partida de bolos. Se evita "frame" para no confundirlo con `ControllerFrame`.
_Avoid_: frame

**Tiro de bolos (Delivery)**:
El lanzamiento de la bola en un turno de bolos.
_Avoid_: tiro (sin calificar)

**Pino (Pin)**:
Cada uno de los 10 objetivos del bolos; el slice no tiene otros tipos de pinos.
_Avoid_: bolo (para el objeto), target

**Bola (Ball)**:
La bola única que se lanza en el slice; no hay selección de bolas.
_Avoid_: balón, pelota

**Pocket**:
La abertura entre el pino 1 y el 3 (o el 1 y el 2) donde entra la bola para maximizar el pleno.
_Avoid_: bolsa, bolsillo

**Pleno (Strike)**:
Derribar los 10 pinos con el primer tiro de un turno.
_Avoid_: strike (en docs), full

**Spare**:
Derribar los pinos restantes con el segundo tiro de un turno.
_Avoid_: medio pleno, semipleno

**Turno abierto (Open frame)**:
Un turno que termina sin pleno ni spare.
_Avoid_: frame abierto, open

**Canaleta (Gutter)**:
El canal lateral de la pista; una bola que cae ahí cuenta 0 pinos.
_Avoid_: gutter (en docs), cuneta

**Efecto (Spin)**:
La rotación aplicada a la bola que curva su trayectoria.
_Avoid_: spin (en docs), curva (la curva es la trayectoria resultante)

**Suelta (Release)**:
El momento en que la bola sale de la mano; en el juego, soltar B al final del swing.
_Avoid_: release (en docs), lanzamiento (el lanzamiento incluye el swing)

**Apuntado (Aim)**:
El ajuste de posición/ángulo antes del tiro.
_Avoid_: aim (en docs), puntería

**Marcador (Scoreboard)**:
La tarjeta de 10 turnos con los totales y los símbolos de pleno/spare.
_Avoid_: score, tabla de puntos

**Práctica (Practice)**:
El modo sin puntaje, con tiros ilimitados y reset de pinos por tiro.
_Avoid_: entrenamiento, training

**Ronda de desempate (Tie-breaker roll)**:
Un tiro extra por jugador para desempatar una partida; se repite hasta que haya un ganador.
_Avoid_: tie-break, muerte súbita (en docs; se usa como explicación)

**Golpe (Stroke)**:
El movimiento de raqueta que impacta la pelota en tenis.
_Avoid_: tiro

**Circuito (Track)**:
El recorrido de una carrera de kart.
_Avoid_: pista (sin calificar)
