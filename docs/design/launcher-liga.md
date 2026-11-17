# Launcher: dirección LIGA

Identidad y estructura del launcher de **Toxinator 3**. Documenta la decisión
tomada en [#11](https://github.com/skalanux/toxinator/issues/11); el prototipo
navegable vive en el branch `prototype/launcher-ux` (no se mergea a `main`).

> **Estado**: dirección elegida. **LIGA** es el nombre de trabajo de la pantalla
> de inicio; el naming público de la consola sigue abierto. La implementación en
> Panda3D todavía no empezó.

## Concepto

La consola es la mesa de una **liga de barrio de héroes raros**. Cada juego es un
**desafío**, cada jugador un **contendiente** y los mandos el **plantel**. El
launcher no es una biblioteca de apps ni una grilla de cards: es la cartelera de
una fecha, con un rival destacado, una escalera de próximos desafíos y el equipo
que va a jugar.

El primer desafío, **Maldito Pino**, es el rival de la fecha: un pino con vincha,
estrella y mala leche. La liga, el escudo y los contendientes son originales; no
hay IP de Marvel, anime ni Nintendo.

**Principios**

- Equipo antes que catálogo: el jugador ve quién juega y contra qué.
- Una sola pieza valiente: la ficha del contendiente destacado. El resto es
  estructura de liga, no decoración.
- Deporte de barrio con energía de anime: cartel, rank, récord, rivalidad.
- Etiquetas funcionales y legibles; cero glassmorphism, neón ni gradientes
  suaves.
- La identidad se banca en blanco y negro; el color es jerarquía, no muleta.

## Marca

- **Escudo**: geometría simple de escudo con una estrella de cinco puntas.
- **Wordmark**: `LIGA` en display pesada, mayúsculas, tracking cerrado.
- **Tagline**: **LA LIGA DE LOS JUEGOS**.
- **Mascota/contendiente**: pin héroe con vincha y estrella; funciona como icono
  del primer juego y como personaje de la marca.
- **Tono**: provocador, de barrio, con humor. “Partido suspendido”, “Entrando a
  la cancha”, “La liga se juega en casa”.

## Paleta: Liga · Noche

Dirección elegida. El **Día** queda como tema alternativo, no como default.

| Token | Valor | Uso |
|---|---|---|
| `bg` | `#0E1726` | Fondo navy de la consola |
| `panel` | `#F2E9DA` | Paneles y superficies principales (hueso) |
| `line` | `#0A111C` | Bordes, sombras duras y texto sobre hueso |
| `text` | `#F2E9DA` | Texto sobre navy |
| `accent` | `#B02F42` | Héroe crimson: ficha destacada, foco, acción |
| `warm` | `#E3B341` | Oro: rank, récord, botón primario |
| `green` | `#3E8E7E` | Jade: conexión, estado online |
| `red` | `#E06A6A` | Error y advertencia |
| `muted` | `#5B6475` | Texto secundario sobre hueso |
| `surface-2` | `#F0E3D2` | Filas y slots sobre hueso |
| `line-soft` | `#D8C7B2` | Separadores suaves |

Reglas de color:

- **Crimson es el héroe**, no el fondo: se usa en la ficha del contendiente y en
  el foco.
- **Oro es el rank y la acción primaria**: no se usa para texto largo.
- **Jade es estado**, no decoración.
- El resto es navy/hueso/tinta. Si una pantalla necesita un cuarto acento, el
  diseño está mal.
- Sombras duras de 2–6 px, sin blur. Bordes de 2 px. Radios de 4 px (o pill en
  botones).

### Alternativa: Liga · Día

Fondo `#F2F1EC`, paneles blancos, tinta `#151A20`, crimson `#B02F42`, oro
`#D6A23A`, jade `#2E7D6E`. Sirve para living room de día; no es el default.

## Tipografía

| Rol | Familia objetivo | Placeholder del prototipo |
|---|---|---|
| Display (marca, titulares, rank) | **Archivo Black** | Nimbus Sans Narrow / Liberation Sans |
| UI (texto, botones, labels) | **IBM Plex Sans** | Liberation Sans |
| Datos (rank, récord, contadores) | **IBM Plex Mono** | Liberation Mono |

- Display en mayúsculas, itálica y tracking negativo para los titulares.
- UI en sentence case; los labels de sistema en mayúsculas con tracking amplio.
- Mono solo para datos y códigos, nunca para párrafos.

## Layout

```text
┌────────────────────────────────────────────────────────────┐
│ [ESCUDO] LIGA   TEMPORADA 01 · FECHA 03     [2/4] [AJUSTES]│
├──────────────────────────────────┬─────────────────────────┤
│  CONTENDIENTE DESTACADO          │  PRÓXIMOS DESAFÍOS      │
│  MALDITO PINO                    │  KART        RANK C     │
│  [pin héroe]                     │  TENIS       RANK C     │
│  RANK A · 1–4 JUGADORES          │  + SUMAR DESAFÍO        │
│  [ JUGAR ] [ FICHA ]             │                         │
├──────────────────────────────────┴─────────────────────────┤
│  PLANTEL   [P1 LISTO] [P2 ESPERA] [P3 ...] [P4 ...]        │
└────────────────────────────────────────────────────────────┘
```

- **Topbar**: marca, temporada/fecha, idioma, plantel y ajustes.
- **Ficha del contendiente**: el juego seleccionado. Rank, evento, título,
  subtítulo, descripción, jugadores, formatos, récord y acciones.
- **Escalera**: los otros desafíos como filas con rank y estado (`ABIERTO` /
  `PRONTO`), más “sumar desafío”.
- **Plantel**: cuatro slots con número, nombre, estado y capacidad. Marca en
  rojo al mando que no cumple los requisitos del desafío.
- **Hints**: teclas y acciones disponibles.

Responsive: a menos de 1100 px la escalera pasa debajo de la ficha; a menos de
900 px la ficha se apila y el plantel va a dos columnas; a menos de 620 px todo
va a una columna.

## Componentes y estados

- **Ficha del desafío** (`detail`): arte, descripción, requisitos, formatos,
  récord y acción de jugar. Es la “ficha de combate”.
- **Plantel** (`players`): asignación de mandos, sumar celular por QR, simular
  join y liberar slots.
- **Ajustes** (`settings`): idioma, audio, gráficos y accesibilidad.
- **Sumar celular** (`connecting`): QR + estado de conexión. Si el plantel está
  vacío, se abre automáticamente y se cierra al conectar el primer mando.
- **Partido suspendido** (`error`): el mando no cumple las capacidades
  requeridas; explica qué falta y cómo resolverlo.
- **Liga vacía** (`empty`): no hay juegos instalados.
- **Entrando a la cancha** (`launching`): transición al juego.
- **Apagar** (`off`): confirmación de cierre de la consola.

Copy de UI en `es`/`en`, español por defecto. Los identificadores y claves van en
inglés (`players`, `launching`, `error`); el copy visible se traduce.

## Navegación

- `← ↑ → ↓` / WASD: navegar.
- `Enter` / `A`: seleccionar.
- `Esc` / `B`: volver.
- `S` / `Start`: ajustes.
- `P`: plantel y mandos.
- `C`: sumar celular.
- `L`: idioma.
- `H`: ayuda.
- `V`: variante del prototipo (solo prototipo).
- `T`: tema del prototipo (solo prototipo).
- Gamepad estándar: D-pad/stick, `A`, `B`, `Start`.

## Prototipo

- Branch: `prototype/launcher-ux`
- Commits: `dc039f9` (estructura LIGA), `f9bdd66` (paleta Noche/Día),
  `41c0106` (Noche elegida)
- URL local:

```text
http://localhost:8080/prototype/launcher/?variant=D&theme=liga&palette=noche
```

- Código: `prototype/launcher/` (`index.html`, `app.js`, `styles.css`).
- Capturas: `prototype/launcher/screenshots/liga-noche-*.png`.
- Guía del prototipo: [`prototype/launcher/README.md`](../../prototype/launcher/README.md).

El prototipo es HTML/CSS/JS throwaway: sirve para fijar estructura, jerarquía,
identidad y navegación antes de reimplementar en Panda3D. No se mergea a `main`.

## Implementación en Panda3D (pendiente)

Cuando arranque la implementación:

- Una sola escena de launcher con capas 2D (`DirectGui` o UI propia sobre
  `OnscreenImage`/`OnscreenText`); no recompilar el prototipo web.
- El launcher consume el mismo `InputState` que los juegos; los mandos se asignan
  a slots desde el plantel.
- Los datos de juegos vienen del manifest (`Game manifest`), no hardcodeados.
- i18n con las mismas claves `es`/`en`.
- Las tipografías se empaquetan con la consola (Archivo Black, IBM Plex Sans,
  IBM Plex Mono) y se cargan desde assets, no del sistema.
- Estados de error y conexión comparten los componentes de overlay de la consola.

## Preguntas abiertas

- Naming público final de la consola; **LIGA** es nombre de trabajo.
- Licencia y empaquetado de las tipografías.
- Arte final del escudo, el pin héroe y los iconos de desafíos.
- Si el tema Día se ofrece como ajuste o se descarta.
- Cómo se representa la temporada/fecha cuando haya más de tres juegos.
