# Prototype: launcher UX

Prototipo throwaway para **#11**. No es el launcher final; sirve para elegir
estructura, jerarquía y navegación antes de implementar la versión Panda3D.

## Cómo abrirlo

Desde la raíz del repo:

```bash
python3 -m http.server 8080
```

Abrí:

```text
http://localhost:8080/prototype/launcher/?variant=C&theme=toxica
```

También podés abrir `index.html` directo, pero el Gamepad API funciona mejor por
`localhost`.

## Tres variantes

- **A · Carousel**: tarjetas horizontales grandes, detalle abajo, tira de mandos.
  Consola clásica.
- **B · Biblioteca**: sidebar vertical de juegos, hero grande y panel de mandos.
  Más denso, más “PC”.
- **C · Mosaico**: grilla full-screen, sin topbar pesada, bottom sheet de detalle.
  Más TV, más visual.

La barra flotante inferior cambia de variante (`V`) y de tema (`T`), y actualiza
`?variant=` / `?theme=`.

## Tres direcciones visuales

La variante C ahora tiene tres identidades deliberadamente distintas. La cuarta
opción, **Neón**, queda como referencia del estado anterior.

- **Tóxica**: hueso, asfalto, naranja de seguridad y amarillo ácido. Condensada,
  filos duros, cinta de peligro y placa estampada. La consola como equipo de una
  liga de bolos tóxica.
- **Cómic**: papel de diario, tinta, magenta, amarillo y cian. Halftone, paneles
  gruesos y títulos en itálica negra. La consola como tapa de un cómic de barrio.
- **Bolera 78**: palta, oro cosecha, naranja quemado y nogal. Alfombra de bolera,
  aro de liga y tipografía condensada; nada de crema + serif + terracota.
- **Neón**: la versión anterior, para comparar.

### Paletas y tipos

- **Tóxica**: hueso `#E9E2D0`, asfalto `#151412`, naranja `#F05A28`, ácido
  `#D8F23A`. Nimbus Sans Narrow; placa estampada, cinta de peligro.
- **Cómic**: papel `#EFE7D5`, tinta `#17130F`, magenta `#F23B7A`, amarillo
  `#FFD400`, cian `#00A6C8`. Liberation Sans Black Italic; halftone, panel,
  rótulo de tapa.
- **Bolera 78**: crema `#EFE0C3`, nogal `#4A2E1F`, oro `#D9A441`, naranja
  `#C65A2E`, palta `#6E7B3A`. Nimbus Sans Narrow; madera, alfombra y aro de liga.

Las tipografías del prototipo son stacks del sistema; la identidad final puede
usar una familia licenciada. La barra flotante muestra el tema activo.

Para abrir un estado directo:

```text
?screen=detail
?screen=players
?screen=settings
?screen=connecting
?screen=error
?screen=empty
?screen=help
```

## Controles

- `← ↑ → ↓` / WASD: navegar.
- `Enter` / `A`: seleccionar.
- `Esc` / `B`: volver.
- `S` / `Start`: ajustes.
- `P`: jugadores y mandos.
- `C`: conectar teléfono (QR mock).
- `E`: error de capacidades.
- `0`: biblioteca vacía.
- `Q`: apagar.
- `L`: idioma ES/EN.
- `H`: ayuda y estado actual.
- `J`: simular join de un mando.
- `V`: cambiar variante.
- `T`: cambiar tema.
- Gamepad estándar: D-pad/stick, A, B, Start.

## Capturas

**Layouts (tema Neón, el anterior)**

- [Variante A](screenshots/home-a.png)
- [Variante B](screenshots/home-b.png)
- [Variante C](screenshots/home-c.png)

**Direcciones visuales (variante C)**

- [Tóxica](screenshots/theme-toxica.png)
- [Cómic](screenshots/theme-comic.png)
- [Bolera 78](screenshots/theme-bolera78.png)
- [Neón, para comparar](screenshots/theme-neon-before.png)

**Estados con tema**

- [Jugadores · Bolera 78](screenshots/players-bolera78.png)
- [Ajustes · Tóxica](screenshots/settings-toxica.png)
- [Detalle · Neón](screenshots/detail.png)
- [Jugadores · Neón](screenshots/players.png)
- [Ajustes · Neón](screenshots/settings.png)
- [Conectar teléfono · Neón](screenshots/connecting.png)
- [Error de capacidades · Neón](screenshots/error.png)
- [Ayuda · Neón](screenshots/help.png)

## Qué evaluar

- ¿Qué dirección visual se siente propia de Toxinator 3 y no de cualquier app?
- ¿Tóxica, Cómic o Bolera 78? ¿Qué partes querés mezclar?
- ¿La marca (wordmark, tagline, pin) funciona en la variante C?
- ¿Qué variante de layout se siente más “consola” sin sobrecargar?
- ¿La tira de mandos se entiende? ¿P1 teléfono, P2 Wiimote sin pilas, P3 gamepad
  que no cumple motion?
- ¿El flujo Home → detalle → iniciar es claro?
- ¿Ajustes y jugadores deberían ser overlays o pantallas?
- ¿La biblioteca vacía y el error de capacidades se entienden?
- ¿El idioma cambia bien sin traducir nombres propios?
- ¿La navegación con gamepad se siente bien?

Anotá qué partes de qué variante querés mezclar. El arte es placeholder; el
launcher final va a usar assets propios y Panda3D/DirectGUI.
