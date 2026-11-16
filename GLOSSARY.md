# Consola 3D multijuego

Contexto de la consola personal de juegos 3D en Python, sus mandos y el primer vertical slice de bolos. Los términos canónicos están en español; el código usa el identificador en inglés entre paréntesis.

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
Un plugin de Python con metadata y ciclo de vida que la consola carga; contiene uno o más modos.
_Avoid_: app, título

**Manifiesto de juego (Game manifest)**:
La metadata que declara id, nombre, versión, jugadores y capacidades requeridas/opcionales de un juego.
_Avoid_: config, descriptor

**Modo (Mode)**:
Una variante jugable dentro de un juego, como un deporte o un minijuego de una colección.
_Avoid_: minijuego (cuando es solo una variante), nivel

**Overlay de plataforma (Platform overlay)**:
La UI de la consola que se dibuja sobre un juego para pausa, errores o desconexión de mandos.
_Avoid_: HUD (el HUD es del juego)

## Sesión

**Partida (Match)**:
Una sesión de juego con sus reglas (10 turnos de bolos, 3 vueltas de kart). No es el software.
_Avoid_: juego, sesión

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

**Mando (Controller)**:
Un dispositivo físico o virtual que produce `ControllerFrame`s: Wiimote, celular Android, gamepad o teclado/mouse.
_Avoid_: controlador, control, dispositivo

**Slot de jugador (Player slot)**:
Un asiento lógico de 1 a 4 al que se asigna un mando durante una partida.
_Avoid_: player index, jugador

**ControllerFrame**:
Una muestra normalizada del estado de un mando en un instante: botones, movimiento, puntero y touch, con timestamp.
_Avoid_: frame, paquete, estado

**Capacidad (Capability)**:
Una característica que un mando o un juego declara, como `motion`, `pointer`, `buttons`, `touch`, `haptics` o `screen`; el launcher negocia las requeridas y opcionales.
_Avoid_: feature, flag

**Gesto (Gesture)**:
Un patrón de movimiento reconocido a partir de `ControllerFrame`s, como swing, throw, tilt o aim.
_Avoid_: acción, movimiento

**Calibración (Calibration)**:
El ajuste de los sensores de un mando para que sus datos tengan una orientación y escala consistentes.
_Avoid_: setup, configuración

**Traza de input (Input trace)**:
Una secuencia grabada de `ControllerFrame`s usada para tests, replay o depuración.
_Avoid_: log, grabación

**Simulador de mandos (Controller simulator)**:
Un mando falso controlado por teclado, mouse o gamepad que produce `ControllerFrame`s para desarrollar y testear sin hardware.
_Avoid_: emulador, fake controller

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

**Golpe (Stroke)**:
El movimiento de raqueta que impacta la pelota en tenis.
_Avoid_: tiro

**Circuito (Track)**:
El recorrido de una carrera de kart.
_Avoid_: pista (sin calificar)
