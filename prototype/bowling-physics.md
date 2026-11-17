# Prototipo: física de pinos y tuning de bolos

Prototipo del ticket [#16](https://github.com/skalanux/toxinator/issues/16).
Branch: `prototype/bowling-physics`. Código y resultados en
[`bowling-physics/`](bowling-physics/).

## Veredicto

**Sí, los parámetros de #10 son utilizables**: los pinos caen, no hay jitter
relevante en reposo y el CCD de la bola evita el tunneling en tiros de hasta
16 m/s. La acción de pinos es **conservadora**: 7.2 pinos promedio y 2 plenos en
31 tiros; los corner pins (4 y 10) quedan de pie con frecuencia. Para el juego,
mantener el convex hull y sumar un boost de pin action (1.1–1.2) o aceptar que el
pleno sea difícil.

## Escena

- Pista de 1.05 × 20 m, pista y pin deck a `z = 0`.
- Pinos a 12 in (0.3048 m) entre centros, filas a `0.264 m`.
- Bola de 7 kg y 0.108 m de radio.
- Pinos de 1.5 kg, altura 0.38 m, perfil de bolos (base 0.028 m, panza 0.060 m,
  cuello 0.028 m, cabeza 0.036 m), centro de masa a 0.15 m.
- Gravedad `-9.81 m/s²`, paso fijo `1/120 s`, `BulletWorld` de Panda3D.
- CCD en la bola (`motion_threshold=0.005`, `swept_radius=0.103`) y en los pinos
  (`0.005` / `0.03`) para que no atraviesen el piso del pit.
- Sin juego, sin UI, sin mando: el objetivo es aislar la física.

## Método

- **31 tiros base**: 28 normales con velocidad 6–10 m/s, posición inicial
  `-0.05…0.10 m`, objetivo el pocket y side roll `-3…3 rad/s`; 3 tiros de
  tunneling a 12, 14 y 16 m/s apuntados al pino 1.
- **Sweep**: 5 configuraciones × 16 tiros (7–8.5 m/s, dos líneas, side roll
  ±3 rad/s): baseline, pin friction 0.10, pin restitution 0.25, ball friction
  0.10 y pin mass 1.3 kg.
- **Jitter**: 5 s con los 10 pinos en reposo, sin bola.
- **FPS**: 300 frames offscreen a 1280×720, 2 pasos de física por frame.
- **Clip**: 204 frames a 60 FPS de un pleno con bola a 7.0 m/s, línea 0.08 m.

Comando:

```bash
uv run --with panda3d==1.10.16 python prototype/bowling-physics/sim.py all \
  --out prototype/bowling-physics/results \
  --video prototype/bowling-physics/media/bowling-physics.mp4
```

## Resultados

### Baseline

| Métrica | Valor |
|---|---:|
| Tiros | 31 |
| Plenos | 2 |
| Strike rate | 6.5% |
| Pinos caídos promedio | 7.16 |
| Mediana | 7 |
| Mínimo / máximo | 4 / 10 |

Histograma de pinos caídos: `4:2, 5:4, 6:4, 7:7, 8:7, 9:5, 10:2`.

Los 28 tiros normales: 2 plenos, 7.18 pinos promedio, rango 4–10. Los 3 tiros de
tunneling: 0 plenos, 7 pinos promedio, rango 6–8, **sin flags de tunneling**: la
bola contactó 5, 6 y 6 pinos, y cayeron 6–8 pinos.

### Sweep

| Configuración | Plenos | Strike rate | Promedio | Rango |
|---|---:|---:|---:|---:|
| baseline (ball friction 0.05) | 2/16 | 12.5% | 7.31 | 4–10 |
| pin friction 0.10 | 1/16 | 6.2% | 7.19 | 4–10 |
| pin restitution 0.25 | 2/16 | 12.5% | 7.25 | 4–10 |
| ball friction 0.10 | 0/16 | 0% | 6.31 | 4–8 |
| pin mass 1.3 kg | 0/16 | 0% | 7.00 | 4–9 |

La variable que más mueve la aguja es la fricción de la bola: **0.05 (pista
aceitada) rinde mejor que 0.10**. Fricción/restitución/masa del pino cambian poco
la acción en este rango.

### Jitter en reposo

| Métrica | Valor |
|---|---:|
| Desplazamiento máximo | 2.72 mm |
| Deriva después de 0.5 s | 2.51 mm |
| Inclinación máxima | 0.50° |
| Velocidad angular máxima | 0.31 rad/s |
| Pinos caídos | 0 |

Aceptable para el prototipo. Si en el juego se ve deriva, subir damping o sleep
threshold de los pinos; no es un problema de estabilidad grave.

### FPS

| Métrica | Valor |
|---|---:|
| Frames | 300 |
| Resolución | 1280×720 |
| Frame promedio | 0.59 ms |
| FPS promedio (sin vsync) | 1687 |
| p50 / p95 | 0.52 / 1.12 ms |
| Peor frame | 5.01 ms |

El target de 60 FPS queda lejísimos: la escena es simple y el costo está en el
render, no en Bullet. No es representativo de la escena completa del juego, pero
descarta que la física sea el cuello de botella.

### Tunneling

Los tiros de 12, 14 y 16 m/s impactaron 5, 6 y 6 pinos, y no dispararon el flag
de tunneling. La bola con CCD no atraviesa el cluster. A 16 m/s los pinos salen
despedidos hasta 5–6 m de lado; en una pista real los contienen las canaletas y
el ball return. El prototipo usa un piso de captura ancho para que no caigan al
vacío; **el juego necesita paredes laterales/pit**.

## Hallazgos

1. **La fricción de la bola es el knob principal**: 0.05 (pista aceitada) da
   mejor carry que 0.10. El resto de los parámetros del pino es insensible en el
   rango probado.
2. **El giro yaw puro no hace hook**: un `spin_z` (eje vertical) no genera fuerza
   lateral porque el punto de contacto está sobre el eje. Para curvar hay que
   inclinar el eje (side roll, `spin_y`). Con `±3 rad/s` la línea cambia; con
   `±20 rad/s` la bola se va de la pista. El mapeo del throw debe usar un eje
   inclinado, no solo yaw.
3. **La forma de colisión del pino manda**: con el convex hull los corner pins
   quedan de pie con frecuencia; una cápsula o multi-esfera da plenos casi
   automáticos (100% en la prueba); un cilindro de 0.055 m da 4/28. El convex
   hull es la opción estable y creíble; si el juego quiere “pin action generosa”,
   sumar un boost de impulso o aceptar un pleno difícil.
4. **Panda3D no expone las iteraciones del solver**: `BulletWorld` no tiene
   `setSolverNumIterations`; el prototipo usa el default de Bullet (10). El rango
   10–20 de #10 no se puede tunear por la API pública de Panda3D; si hace falta
   20, el juego puede usar Bullet directo (ya previsto en #10).
5. **Estabilidad**: 2.7 mm de deriva máxima y 0.5° de inclinación en 5 s; no hay
   jitter visible.
6. **El CCD funciona** para la bola y para los pinos contra el piso del pit; los
   pinos de 16 m/s necesitan un mundo con paredes, no solo un piso.

## Parámetros finales

| Elemento | Valor |
|---|---|
| Bola: masa / radio | 7.0 kg / 0.108 m |
| Bola: fricción / restitución | **0.05** / 0.10 |
| Bola: damping lineal / angular | 0.01 / 0.01 |
| Bola: CCD | on (`0.005` / `0.103`) |
| Pino: masa | 1.5 kg |
| Pino: colisión | convex hull del perfil; base 0.028, panza 0.060, alto 0.38, COM 0.15 |
| Pino: fricción / restitución | 0.20 / 0.10 |
| Pino: damping lineal / angular | 0.05 / 0.05 |
| Pino: CCD | on (`0.005` / `0.03`) |
| Pista: fricción / restitución | 0.20 / 0.0 |
| Mundo | `-9.81 m/s²`, paso fijo `1/120`, solver default 10 |
| Pin action | boost 1.1–1.2 pendiente de tuning en el juego |

## Qué no valida

- El mapeo real de Wiimote/celular a velocidad, dirección y efecto; solo se
  valida el eje físico del efecto.
- El patrón de aceite, la deformación de pinos, el sonido y la física de la bola
  real.
- El scoring de 10 turnos, el hot-seat, la pausa y el game loop.
- La escena completa del juego, 4 jugadores y la performance con arte real.
- La reproducibilidad bit-a-bit entre builds/plataformas; los tests del juego
  usan tolerancia.

## Evidencia

- [Resumen](bowling-physics/results/summary.json)
- [Tiros](bowling-physics/results/throws.csv)
- [Sweep](bowling-physics/results/sweep.json)
- [Jitter](bowling-physics/results/jitter.json)
- [FPS](bowling-physics/results/fps.json)
- [Clip](bowling-physics/media/bowling-physics.mp4)
- [Still 1](bowling-physics/media/still-0000.png) ·
  [Still 2](bowling-physics/media/still-0068.png) ·
  [Impacto](bowling-physics/media/still-0136.png) ·
  [Final](bowling-physics/media/still-0203.png)

## Próximos pasos

1. Cerrar #16 con estos parámetros y el hallazgo del solver.
2. En la implementación, crear `PhysicsWorld` con el paso fijo y los materiales
   de este informe; sumar paredes/pit al pin deck.
3. Tunear `pin_action` en el juego (1.1–1.2) y validar con el mapeo real del
   throw.
4. Cuando haya arte, repetir el FPS con la escena completa y 4 jugadores.
