# Gestos de mando: reconocedor de plataforma y catálogo declarativo

Los gestos dejan de ser código suelto dentro de cada juego. La consola corre un
reconocedor en Python sobre los frames normalizados, antes del `InputHub`, y
expone dos formas estables: **posturas** (`tilt`, `steer`, `aim`) que llegan por
`ControllerFrame.axes`/`pointer`, y **eventos** (`flick`, `swing`, `twist`,
`shake`, `flip`) que llegan por `InputState.gestures` con nombre, dirección,
intensidad y timestamp. Cada juego declara en su manifest qué gestos usa
(`[controller] gestures`), el perfil que viaja al celular lleva los labels para
mostrar el hint, y el `InputHub` filtra los eventos al conjunto declarado. El
reconocedor es uno solo para celular, teclado/mouse y replay de trazas. El
simulador emite gestos sintéticos con teclas canónicas y el mouse sigue
apuntando.

Se eligió frente a reconocer en la PWA, frente a dejar la librería de gestos como
código opcional de cada juego y frente a un clasificador de ML. En la PWA habría
que duplicar la lógica para el simulador y las trazas, y no se podría testear
desde pytest; los gestos por juego son exactamente el problema actual (Maldito
Pino ya tiene umbrales propios en `game.py` que nadie más reusa); un clasificador
necesita datos etiquetados que todavía no existen y no es auditable cuando falla.
El costo es un frame extra de latencia (~16 ms) y mantener un catálogo con
umbrales versionados; el beneficio es un vocabulario compartido, testeable sin
hardware y con una sola implementación.

**Status**: accepted

**Consequences**: `API_VERSION` sube a `0.4`; `ControllerFrame` gana
`screen_angle` y `linear_accel`; `SourceUpdate` gana `gestures`;
`InputState.gestures` entrega los eventos acumulados desde el poll anterior, así
un frame pisado no pierde un gesto; `ControllerSource` puede alimentar gestos,
por lo que `KeyboardMouseSource` y un futuro `ReplaySource` los sintetizan con
las mismas teclas; el protocolo WebSocket sigue en `2` y suma campos opcionales
(`linear`, `screen`, `aim_sensitivity`); el manifest agrega `controller.gestures`
y el perfil del celular una lista `gestures` con labels; la PWA suma la banda de
gestos y el chip de recentrar; las trazas suman `screen_angle`/`linear_accel`
opcionales. El retiro de los alias `A`/`B`, comprometido para `0.4` en
ADR-0007, se corre a `0.5` para no mezclar un cambio incompatible con una
feature aditiva. El Wiimote queda fuera: los gestos son del celular y del
simulador. Ver [`docs/design/gestures.md`](../design/gestures.md).
