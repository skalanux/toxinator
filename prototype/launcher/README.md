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
http://localhost:8080/prototype/launcher/?variant=A
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

La barra flotante inferior cambia de variante y actualiza `?variant=`. También
con `V`.

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
- Gamepad estándar: D-pad/stick, A, B, Start.

## Capturas

- [Variante A](screenshots/home-a.png)
- [Variante B](screenshots/home-b.png)
- [Variante C](screenshots/home-c.png)
- [Detalle](screenshots/detail.png)
- [Jugadores](screenshots/players.png)
- [Ajustes](screenshots/settings.png)
- [Conectar teléfono](screenshots/connecting.png)
- [Error de capacidades](screenshots/error.png)
- [Ayuda](screenshots/help.png)

## Qué evaluar

- ¿Qué variante se siente más “consola” sin sobrecargar?
- ¿La tira de mandos se entiende? ¿P1 teléfono, P2 Wiimote sin pilas, P3 gamepad
  que no cumple motion?
- ¿El flujo Home → detalle → iniciar es claro?
- ¿Ajustes y jugadores deberían ser overlays o pantallas?
- ¿La biblioteca vacía y el error de capacidades se entienden?
- ¿El idioma cambia bien sin traducir nombres propios?
- ¿La navegación con gamepad se siente bien?

Anotá qué partes de qué variante querés mezclar. El arte es placeholder; el
launcher final va a usar assets propios y Panda3D/DirectGUI.
