# Bowling physics prototype

Prototipo standalone para el ticket
[#16](https://github.com/skalanux/toxinator/issues/16). Una pista, diez pinos y
una bola en Panda3D/Bullet; sin juego, sin UI y sin runtime de la consola.

El informe con parámetros, mediciones y hallazgos está en
[`../bowling-physics.md`](../bowling-physics.md).

## Cómo correrlo

Requiere Python 3.14 y `uv`; Panda3D se instala en un entorno efímero:

```bash
uv run --with panda3d==1.10.16 python prototype/bowling-physics/sim.py all \
  --out prototype/bowling-physics/results \
  --video prototype/bowling-physics/media/bowling-physics.mp4
```

Comandos:

```bash
# 31 tiros base: 28 normales + 3 de alta velocidad para tunneling
uv run --with panda3d==1.10.16 python sim.py batch --out results

# sweep de 5 configuraciones x 16 tiros
uv run --with panda3d==1.10.16 python sim.py sweep --out results

# jitter en reposo (5 s)
uv run --with panda3d==1.10.16 python sim.py jitter --out results

# FPS offscreen 1280x720
uv run --with panda3d==1.10.16 python sim.py fps --frames 300 --out results

# clip de 204 frames a 60 FPS
uv run --with panda3d==1.10.16 python sim.py video \
  --video media/bowling-physics.mp4 --out results
```

`all` corre todo. Los comandos de render (`fps`, `video`) usan `ShowBase` con
`windowType="offscreen"`; en Linux necesitan un display/XWayland. El batch y el
jitter corren sin ventana.

## Qué mide

- **Tiros**: velocidad, posición inicial, objetivo y efecto (side roll).
- **Pinos**: caídos, de pie, contactos bola-pino y pino-pino.
- **Tunneling**: tiros a 12/14/16 m/s y distancia mínima a los pinos.
- **Jitter**: desplazamiento, inclinación y velocidad angular en reposo.
- **FPS**: tiempo de frame del render offscreen.

## Archivos

```text
sim.py                 # escena, física, mediciones y render
results/summary.json   # baseline + jitter + fps + video
results/throws.csv     # un row por tiro
results/sweep.json     # 5 configuraciones
results/jitter.json    # reposo
results/fps.json       # render
media/bowling-physics.mp4
media/still-*.png
```

## Límites

Es un prototipo de física, no el juego. No valida el mapeo real de Wiimote o
celular, el patrón de aceite de la pista, la deformación de pinos, el scoring de
10 turnos ni el rendimiento de la escena completa. Ver el informe para los
hallazgos y lo que queda para la implementación.
