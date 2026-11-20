# Launcher: pantalla de inicio de Toxinator

Pantalla principal de **Toxinator 3**: una home de consola con catálogo
navegable, arte por juego, paleta Tokyo Night y estado de los mandos siempre
visible.

> **Estado**: implementado en Panda3D (`toxinator` / `toxinator launcher`).

## Concepto

La consola se abre como una sala de juegos: un rail lateral con la identidad de
Toxinator, un juego destacado con arte propio y una fila de juegos para seguir
explorando. El catálogo completo vive a un golpe de flecha, sin perder de vista
el estado de los controles.

- El juego es el protagonista; la interfaz lo enmarca.
- Un solo gesto valiente por pantalla: el arte del juego destacado.
- El rail es estructura, no decoración: navegación, hora, fecha y mandos.
- Todo se puede manejar con flechas + Enter, con el celular o con mouse.
- La paleta Tokyo Night se usa en toda la consola.

## Paleta

Una sola paleta: **Tokyo Night**.

| Rol | Valor |
|---|---|
| Fondo | `#1A1B26` |
| Panel | `#16161E` |
| Superficie | `#292E42` |
| Texto | `#C0CAF5` |
| Acento | `#7AA2F7` |
| Estado | `#9ECE6A` |

Reglas:

- **Acento** es acción y foco: botón primario, filtro activo, borde de foco.
- **Estado** es conexión: mandos listos y juego instalado.
- **Muted** es información secundaria, nunca acciones.
- Los juegos usan paletas de arte propias dentro de la familia Tokyo Night
  (azul, violeta, cian, verde, ámbar y coral).

## Tipografía

| Rol | Familia | Uso |
|---|---|---|
| Display | **Archivo Black** | Marca, títulos de juego, reloj, títulos de overlay |
| UI | **IBM Plex Sans** | Descripciones y copy |
| UI bold | **IBM Plex Sans SemiBold** | Navegación, botones, nombres de mando |
| Datos | **IBM Plex Mono** | Hora/fecha secundaria, metadatos, estados, hints |

El display va en mayúsculas para los títulos de juego. El resto usa sentence
case. Los datos y labels de sistema van en mono.

## Layout

Referencia 16:9. El rail ocupa ~19% del ancho; el contenido usa el resto.

```text
┌───────────────┬──────────────────────────────────────────────┐
│ TOXINATOR     │  ┌────────────────────────────────────────┐  │
│ CONSOLA · 3   │  │ LISTO PARA JUGAR                       │  │
│               │  │ MALDITO PINO              [arte clave] │  │
│ Inicio        │  │ descripción breve           [diorama]  │  │
│ Catálogo      │  │ [1 JUGADOR] [1 FORMATO] [INSTALADO]   │  │
│ Mandos        │  │ [Jugar] [Ficha]                        │  │
│ Ajustes       │  └────────────────────────────────────────┘  │
│               │  Tus juegos                    Ver catálogo   │
│               │  [juego] [juego] [juego] [juego] [catálogo]  │
│ 21:59         │                                               │
│ fecha         │  Flechas mover · Enter elegir · S ajustes     │
│ MANDOS 1/4    │                                               │
│ P1 P2 P3 P4   │                                               │
└───────────────┴──────────────────────────────────────────────┘
```

- El rail es fijo. La marca arriba, navegación debajo, reloj y mandos al pie.
- El héroe cambia cuando el foco entra en una tarjeta de **Tus juegos**.
- La fila de juegos muestra instalados primero y luego el resto del catálogo.
- El catálogo usa 4 columnas y página de 8 juegos.
- Los overlays (ficha, mandos, ajustes, QR, apagado) comparten panel, tipografía
  y foco; no hay pantallas con lenguajes distintos.

## Componentes

- **Rail**: marca, cuatro destinos, reloj, fecha, resumen y chips P1–P4. El chip
  cambia a verde cuando el mando está listo, ámbar en gracia y muted si está
  libre.
- **Héroe**: arte procedural del juego, estado, título, subtítulo, descripción,
  jugadores, formatos y estado de instalación. Acciones **Jugar** y **Ficha**.
- **Tus juegos**: tarjetas con arte, título, género y punto de estado. La
  tarjeta final abre el catálogo.
- **Catálogo**: filtros *Todos*, *Instalados*, *Para varios* y *Próximamente*;
  grilla 4×2 con paginación.
- **Ficha**: arte grande, descripción, jugadores, formatos, id y estado.
- **Mandos**: P1–P4 con nombre, estado y botón **Vincular celular**. El mando
  del celular recibe el layout, las etiquetas y la skin del juego al lanzarlo.
  Los juegos pueden usar `ctx.phone` para vibrar y reproducir tonos.
- **Ajustes**: preview de Tokyo Night, idioma, estado de mandos y salida.
- **QR**: panel de vinculación con QR, URL y estado de espera.
- **Apagado**: confirmación de cierre.
- **Abriendo**: transición a pantalla completa con el nombre del juego.

## Arte de juego

Cada juego recibe un **diorama isométrico** generado por código:

- Plataforma flotante con grilla y cubos en tres tonos.
- Un prop según el juego: pino, bandera, paleta, pong, estrella, corazón,
  moneda o cubo. El prop se elige con `[art] motif` en el manifest (`auto` lo
  deriva del id).
- Acentos de HUD: barra segmentada, crosshair, vidas y pickups flotantes.
- Fondo con gradiente, diagonales, píxeles y scanlines.

No hay discos ni anillos oversized. Las texturas se dibujan con Pillow, se
convierten a `Texture` y se cachean por juego, variante y tamaño. Las variantes
son `hero` (16:9 ancho), `card` (sala) y `portrait` (catálogo/ficha).

## Navegación

- `← ↑ ↓ →`: mover el foco.
- `Enter`: activar (jugar, abrir ficha).
- `D`: ficha del juego destacado.
- `S`: ajustes.
- `C`: vincular celular / ver QR.
- `Esc`: cerrar overlay, volver del catálogo o abrir apagado.
- Touchpad del celular: joystick con repetición.
- `A` del celular: confirmar.
- `B` del celular: volver.
- Mouse: rail, tarjetas, filtros y botones.

El foco se mueve por geometría: desde el centro del ítem actual busca el ítem
más cercano en la dirección pedida. El borde de foco usa el acento de Tokyo
Night.

## Implementación

| Archivo | Responsabilidad |
|---|---|
| `launcher/app.py` | Pantallas, overlays, foco, lifecycle y transición a juegos |
| `launcher/theme.py` | Paleta Tokyo Night y carga de fuentes |
| `launcher/art.py` | Texturas procedurales: fondos, arte de juego, tarjetas |
| `launcher/ui.py` | Rect, textos, paneles redondeados, botones, pills e iconos |

El arte no depende de imágenes externas: se generan dioramas, props y acentos de
HUD una sola vez y se cachean. Los textos y el arte del héroe se actualizan al
mover el foco; las tarjetas se mantienen estáticas.

Los juegos siguen viniendo del catálogo (`core/games.py` + juegos externos) y el
launcher solo muestra `name`, `description`, `players` y `modes`. Los mandos
salen del mismo `InputState` que usan los juegos.

## Capturas

- [Home](screenshots/launcher-home.png)
- [Catálogo](screenshots/launcher-catalog.png)
- [Ajustes](screenshots/launcher-settings.png)
- [Mandos](screenshots/launcher-controllers.png)
