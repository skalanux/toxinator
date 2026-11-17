# Prototype: launcher UX

Prototipo throwaway para **#11**. No es el launcher final; sirve para elegir
estructura, jerarquía, identidad y navegación antes de implementar la versión
Panda3D.

> **Dirección elegida: LIGA · Noche.** El Día queda como alternativa de tema.

## Cómo abrirlo

Desde la raíz del repo:

```bash
python3 -m http.server 8080
```

Abrí:

```text
http://localhost:8080/prototype/launcher/?variant=D&theme=liga&palette=noche
```

También podés abrir `index.html` directo, pero el Gamepad API funciona mejor por
`localhost`.

## Concepto: LIGA

La consola es la mesa de una **liga de barrio de héroes raros**. Cada juego es un
**desafío**, cada jugador es un **contendiente** y los mandos son el **plantel**.
El primer desafío, **Maldito Pino**, es el rival de la fecha: un pin con vincha,
estrella y mala leche. No hay IP de Marvel ni de anime; la liga, el escudo y los
personajes son propios.

- **Paleta**: la identidad se reduce a **crimson + oro + jade + hueso/navy**.
  - **Noche**: fondo navy `#0E1726`, paneles hueso `#F2E9DA`, crimson `#B02F42`,
    oro `#E3B341`, jade `#3E8E7E`.
  - **Día**: fondo `#F2F1EC`, paneles blancos, tinta `#151A20`, crimson
    `#B02F42`, oro `#D6A23A`, jade `#2E7D6E`.
  La barra de prototipo cambia **Noche/Día**, o usá `?palette=noche` / `?palette=dia`.
- **Tipografía**: Archivo Black para carteles y titulares; IBM Plex Sans para la
  interfaz; IBM Plex Mono solo para ranks, récords y datos. Los stacks del
  prototipo usan Nimbus Sans Narrow / Liberation Sans como placeholders.
- **Layout**: ficha del contendiente destacado, escalera de próximos desafíos,
  plantel abajo y ficha de combate para el detalle.
- **Marca**: escudo + wordmark LIGA + tagline **LA LIGA DE LOS JUEGOS**; el pin
  héroe es la mascota/contendiente.
- **Principios**: equipo antes que catálogo; una pieza valiente (la ficha del
  contendiente); estructura de liga, no grilla de cards; etiquetas funcionales
  claras; cero neón/glass/gradientes suaves.

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

La barra inferior cambia variante (`V`) y tema (`T`): **Liga**, **Cómic** y
**Neón**. Cómic y Neón quedan para comparar; Feria se archivó. Actualiza
`?variant=` / `?theme=`.

## Estados para revisar

Agregá `&screen=` a la URL:

```text
?screen=detail
?screen=players
?screen=settings
?screen=connecting
?screen=error
?screen=empty
?screen=help
?screen=launching      (&ready=1 para el estado listo)
```

## Controles

- `← ↑ → ↓` / WASD: navegar.
- `Enter` / `A`: seleccionar.
- `Esc` / `B`: volver.
- `S` / `Start`: ajustes.
- `P`: plantel y mandos.
- `C`: sumar celular (QR mock).
- `E`: error de capacidades.
- `0`: liga vacía.
- `Q`: apagar.
- `L`: idioma ES/EN.
- `H`: ayuda y estado actual.
- `J`: simular join de un mando.
- `V`: cambiar variante.
- `T`: cambiar tema.
- Gamepad estándar: D-pad/stick, A, B, Start.

## Capturas

**Liga · Noche**

- [Home](screenshots/liga-noche-home.png)
- [Plantel](screenshots/liga-noche-players.png)
- [Ajustes](screenshots/liga-noche-settings.png)
- [Ficha del desafío](screenshots/liga-noche-detail.png)
- [Sumar celular](screenshots/liga-noche-connecting.png)
- [Partido suspendido](screenshots/liga-noche-error.png)
- [Liga vacía](screenshots/liga-noche-empty.png)
- [Entrando a la cancha](screenshots/liga-noche-launching.png)

**Liga · Día**

- [Home](screenshots/liga-dia-home.png)
- [Plantel](screenshots/liga-dia-players.png)
- [Ficha del desafío](screenshots/liga-dia-detail.png)

**Comparación**

- [Cómic de barrio](screenshots/theme-comic.png)
- [Neón, el estado anterior](screenshots/theme-neon-before.png)

## Qué evaluar

- ¿LIGA se siente una consola propia y no un dashboard gamer?
- ¿La ficha del contendiente, la escalera y el plantel se entienden?
- ¿Noche o Día? ¿La paleta crimson/oro/jade/hueso funciona para Marvel/anime sin
  ser una copia?
- ¿El pin héroe y el escudo son una marca creíble?
- ¿La tipografía condensada/italic va en esa dirección?
- ¿Qué partes de Cómic o Neón todavía querés conservar?
- ¿La navegación y los estados se entienden?

Las tipografías son stacks del sistema; cuando la dirección cierre, propongo
familias reales para licenciar/empaquetar. No se mergea a `main`; es un prototipo
para reaccionar.
