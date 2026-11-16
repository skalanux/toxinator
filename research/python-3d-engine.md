# Motor 3D en Python para la consola: ¿Panda3D o alternativa?

- **Ticket:** [#3](https://github.com/skalanux/wiIAsports/issues/3) — `wayfinder:research`
- **Branch:** `research/python-3d-engine`
- **Fecha:** 2026-11-16
- **Pregunta:** ¿Panda3D es la mejor base para una consola 3D general en Python en Linux/Wayland/Iris Xe, o conviene otra opción?
- **Método:** fuentes primarias (PyPI, repos, release notes, docs oficiales) + pruebas ejecutadas en esta máquina (marcadas `[M]`). Cada afirmación significativa lleva cita numerada; la lista está al final.

---

## Veredicto

**Confirmar Panda3D 1.10.16 como base y fijar Python 3.14 (`>=3.14,<3.15`).** Es la única base directa del comparativo (Ursina la hereda) que hoy entrega, con wheels para Python 3.14 y sin compilar nada: escena 3D con grafo de escena, glTF/GLB, shaders GLSL, física 3D Bullet (incluido `BulletVehicle` para kart), audio 3D posicional OpenAL, UI DirectGUI, gamepads por evdev y herramientas de empaquetado, bajo licencia BSD. Medido en la Iris Xe a 1080p: 427–446 fps con 300 cubos iluminados, 233 fps con shadow map, 111 fps con 2000 cubos + sombras y 102–109 fps con un glTF PBR completo con sombras y tonemapping `[M]`. El presupuesto de 60 fps queda holgado para bolos y alcanza para kart con batching.

Las alternativas no compiten como **base de consola**, aunque dos sirven como aceleradores:

| Opción | ¿Base de consola? | Por qué |
|---|---|---|
| **Panda3D 1.10.16** | **Sí — recomendada** | Motor completo; wheels cp314; Bullet; OpenAL 3D; glTF; DirectGUI; BSD `[1][2][9][12][14][22]` |
| Ursina 8.3.0 | No como base; sí para prototipar | Es una capa sobre Panda3D (misma ventana, mismo Bullet), MIT, pero release de PyPI con ~1 año de atraso, API 8.x cambiada y dependencias raras `[24][25][26][27]` |
| pygame-ce + moderngl/PyOpenGL | No | Solo ventana + GL; sin grafo de escena, carga de modelos, física 3D, audio 3D ni UI: habría que escribir el motor `[28][29][31][33]` |
| raylib (bindings Python) | No | Rápido y con Wayland nativo, pero API inmediata sin grafo de escena, sin física 3D, sin audio 3D, sin pipeline de assets (conversión/caché) y bindings EPL-2.0 `[34][35][36][37][38]` |

**Versión de Python a fijar: 3.14** (probado con 3.14.8 y 3.14.10). **No** 3.15: Panda3D 1.10.16 no publica wheels cp315 y tampoco publica sdist; en 3.15 `uv`/`pip` no pueden instalar Panda3D `[1][40]`. Detalle en la sección 8.

---

## 1. Soporte de Python, mantenimiento e instalación

### 1.1 Tabla de paquetes

Datos de PyPI y repos al 2026-11-16. "cp314" = wheel binario para CPython 3.14.

| Paquete | Última versión | Fecha | cp314 | Requiere Python | Licencia | Wheel (Linux x86_64) |
|---|---|---|---|---|---|---|
| panda3d | 1.10.16 | 2025-12-25 | Sí (y cp314t) | sin `Requires-Python` | Modified BSD `[22]` | 54.0 MB `[1]` |
| ursina | 8.3.0 | 2025-12-06 | py3-none-any | `>=3.12` | MIT `[24]` | 4.3 MB |
| pygame | 2.6.1 | 2024-09-29 | **No** (hasta cp313) | `>=3.6` | LGPL `[28]` | — |
| pygame-ce | 2.5.8 | 2026-08-09 | Sí (y cp315) | `>=3.10` | LGPL-2.1 `[29]` | 12.2 MB |
| moderngl | 5.13.0 | 2026-10-07 | Sí (y cp315) | `>=3.7` | MIT `[32]` | 0.3 MB |
| PyOpenGL | 3.1.10 | 2025-08-18 | py3-none-any | — | BSD `[33]` | 3.2 MB |
| raylib | 6.2.0.0 | 2026-10-26 | Sí (y cp315) | sin `Requires-Python` | EPL-2.0 (bindings) `[35]` | 2.4 MB |
| panda3d-gltf | 1.3.0 | 2025-03-16 | py3-none-any | `>=3.8` | BSD-3 `[10]` | 0.03 MB |
| panda3d-simplepbr | 0.13.1 | 2025-03-30 | py3-none-any | `>=3.9` | BSD-3 `[11]` | 2.5 MB |

### 1.2 Panda3D

- **Soporte de 3.14:** la release 1.10.16 publica wheels `cp314-cp314` y `cp314-cp314t` (free-threaded) para `manylinux2014_x86_64` `[1]`. El `setup.cfg` del tag incluye el classifier `Programming Language :: Python :: 3.14` `[4]` y hay un commit explícito "Add Python 3.14 to setup.cfg" del mismo día de la release `[5]`. **Matiz:** las release notes de 1.10.16 no anuncian 3.14 con una frase propia (sí lo hicieron 1.10.15 con 3.13 y 1.10.14 con 3.12) `[3]`; la evidencia de soporte es el wheel + classifier + matriz de tests, no una proclama en las notas.
- **Historial de soporte:** 1.10.14 (2024-01-09) agregó 3.12; 1.10.15 (2024-11-08) agregó 3.13 y wheels cp313/cp313t; 1.10.16 (2025-12-25) trae cp314/cp314t `[1][3]`.
- **Mantenimiento:** releases 1.10.14 → 1.10.15 → 1.10.16, aproximadamente una por año `[2]`. El repo sigue activo (último push 2026-07-28; 5.3k estrellas, 386 issues/PRs abiertos) `[2]`. Cadencia lenta pero con mantenimiento real; no está abandonado.
- **Instalación real:** `uv add panda3d==1.10.16` en un proyecto Python 3.14 descargó el wheel manylinux (51.5 MiB) y lo instaló en ~2 s, sin compilador ni dependencias del sistema más allá de libGL/X11/ALSA `[M]`. Verificado también con 3.14.10 `[M]`.
- **Documentación de instalación desactualizada:** la página oficial "Installing Panda3D in Linux" solo documenta RPM/DEB o compilar desde fuentes; no menciona `pip`/`uv` `[23]`. El camino real es PyPI, que funciona; conviene no seguir esa página al pie de la letra.
- **Sin sdist:** PyPI no publica `.tar.gz` para 1.10.15 ni 1.10.16 `[1]`. Si no hay wheel para tu Python, no hay `pip install` posible: hay que compilar a mano desde GitHub (build C++ con makepanda). Esto es determinante para la versión de Python (sección 8).

### 1.3 Ursina

- Requiere Python `>=3.12` y depende de `panda3d>=1.10.15`, `panda3d-gltf>=1.3.0`, `pillow`, `pyperclip`, `screeninfo` y `sswg==4.3.0` `[24]`. `sswg` es un generador de sitios estáticos: una dependencia rara para un motor de juegos, señal de higiene de packaging mejorable.
- Instalación con `uv` en 3.14: OK; resolvió panda3d 1.10.16, panda3d-gltf 1.3.0, simplepbr 0.13.1, Pillow 13.0.0 `[M]`.
- **Madurez:** el repo está activo (commit 2026-11-16, 57 contribuidores), pero el último release de PyPI es 8.3.0 (2025-12-06) y el `pyproject.toml` del repo ya declara 8.4.0: desarrollo y releases no van sincronizados `[24][25][27]`.
- **API inestable:** en 8.3.0 ya no existen `app.window` ni `app.base` (hay que usar `window` y `application.base`); tutoriales viejos fallan. Lo comprobamos al escribir el smoke test `[M]`.
- **Qué aporta:** entidades de alto nivel, UI propia, `Entity` con colliders y raycast sobre Bullet `[26]`. Es una capa de conveniencia sobre Panda3D, no un motor independiente: no resuelve los límites de Panda3D (por ejemplo, Wayland nativo) ni aporta un pipeline PBR propio.

### 1.4 pygame + PyOpenGL/moderngl

- **pygame upstream está estancado:** 2.6.1 es de 2024-09-29 y no tiene wheels cp314 `[28]`. El fork mantenido es **pygame-ce**, 2.5.8 de 2026-08-09, con cp314 y cp315 `[29]`; el repo commitea a diario `[30]`. Para Python 3.14 hay que usar `pygame-ce`, no `pygame`.
- **moderngl** es un wrapper de OpenGL Core (0.3 MB): no trae ventana, carga de modelos, escena, física, audio ni UI; la ventana la pone SDL/pygame y el resto lo escribís vos `[31][32]`.
- **PyOpenGL** son bindings GL puros (3.2 MB, `py3-none-any`): API de bajo nivel, sin utilidades de motor `[33]`.
- Stack verificado: pygame-ce 2.5.8 + moderngl 5.13.0 crean contexto GL 4.6 sobre SDL 2.32.10 en Wayland y renderizan a 1080p `[M]`. Funciona, pero es un stack de render, no un motor.

### 1.5 raylib (bindings Python)

- `raylib` 6.2.0.0 (2026-10-26) trae wheels cp310–cp315 para Linux x86_64 y depende solo de `cffi>=1.15.1` `[34]`. Instala en 3.14 con `uv` sin problemas `[M]`.
- Empaqueta raylib 6.2 + raymath + raygui + rlgl + physac + GLFW 3.5.1 `[35]`. Licencia de los bindings: **EPL-2.0** (copyleft débil, a nivel archivo); raylib C es **zlib** `[35]`.
- API inmediata estilo C; el binding crudo expone nombres `CamelCase` y structs CFFI (`ffi`), y hay un wrapper `pyray` en snake_case `[35][M]`. No hay grafo de escena ni pipeline de assets.

---

## 2. Wayland, ventana, fullscreen, input y audio

### 2.1 Lo que se midió

| Motor | Backend en esta sesión (Hyprland/Wayland) | Fullscreen 1920x1080 | Notas |
|---|---|---|---|
| Panda3D 1.10.16 | **XWayland**: `glxGraphicsPipe`, `libGL`/`libX11`/`libGLX` | Sí (`is_fullscreen=True`) `[M]` | Sin backend Wayland nativo `[6][8]` |
| Ursina 8.3.0 | XWayland (hereda Panda3D) | No probado | Ventana abierta y render OK `[M]` |
| pygame-ce 2.5.8 | **Wayland nativo** si `SDL_VIDEODRIVER=wayland`; por defecto `x11` | No probado | `get_driver()` = `wayland` `[M]` |
| raylib 6.2.0.0 | **Wayland nativo** (GLFW 3.5.1) | No probado | `memfd:wayland-cursor`, avisos "Wayland:" de GLFW `[M]` |

### 2.2 Panda3D y Wayland

- **No hay backend Wayland.** El issue oficial "Wayland support" (#1579) está abierto desde 2023-12-03 (última actualización 2024-10-17), sin implementación; el propio texto dice que hoy se pasa por XWayland y que un backend nativo "sería relativamente poco trabajo" `[6]`. El árbol de fuentes de 1.10.16 (y también `master`) tiene módulos `glxdisplay`, `x11display`, `egldisplay`, `wgldisplay`… pero **ninguno de Wayland** `[8]`.
- En esta máquina, Panda3D reporta **un solo pipe disponible: `glxGraphicsPipe`**, y crea un `glxGraphicsBuffer`; el proceso carga `libX11`/`libGLX` `[M]`. Es decir: funciona, pero como cliente X11 bajo XWayland.
- **Consecuencias prácticas medidas:**
  - Fullscreen real a 1920x1080 funciona (`requestProperties(setFullscreen(True))` → `1920x1080`, `is_fullscreen=True`) `[M]`.
  - En un compositor tiling como Hyprland, una ventana normal **no respeta el tamaño pedido**: pedimos 800x600 y quedó 922x1030 (tileada a media pantalla) `[M]`. Para juegos: fullscreen/borderless, o regla de ventana flotante. No es culpa del motor, pero afecta el diseño del launcher.
  - **High-DPI sigue abierto** (issue #426, 2018): falta soporte out-of-the-box para escalar la UI según la densidad de píxeles `[7]`; el motor sí expone `get_display_zoom()` para consultar el escalado del sistema `[3]`. En 1080p sin escalado no debería afectar; si algún día se usa 1440p/4K con fractional scaling, hay que probarlo.
- **Riesgo de fondo:** si una sesión corre Wayland puro sin XWayland, Panda3D no arranca. Hoy Omarchy/Hyprland trae XWayland, así que es aceptable; conviene documentarlo como requisito.

### 2.3 Input

- **Panda3D** tiene soporte nativo de gamepads/joysticks/volantes desde 1.10 vía `InputDevice` (evdev en Linux, joystick API o XInput según OS), con clases `gamepad`, `steering_wheel`, `flight_stick`, etc. `[16]`. Es lo que necesita el proyecto para mandos intercambiables. **No verificado con un Wiimote real en esta sesión** (no había hardware); el plan de Wiimote por evdev queda como prototipo aparte.
- **Ursina** hereda el input de Panda3D y agrega helpers (`held_keys`, `mouse`), pero su API 8.x también cambió `[25][49][M]`.
- **pygame-ce** usa eventos SDL2: teclado, mouse, gamepads por SDL_GameController; Wayland nativo funciona `[M]`.
- **raylib** usa GLFW: teclado/mouse/gamepad; en Wayland nativo los avisos de "window position" son normales (Wayland no permite posicionar ventanas) `[M]`.

### 2.4 Audio

- **Panda3D** usa **OpenAL Soft** por defecto (alternativas FMOD/Miles; FMOD requiere licencia comercial) `[14]`. Tiene `Audio3DManager` para audio posicional 3D con listener (típicamente la cámara), y efectos DSP solo con FMOD `[14][15]`.
  - Medido: el plugin `libp3openal_audio.so` está en el wheel; al inicializar, OpenAL reporta `pulse_load: Failed to load libpulse.so.0` y cae al backend **ALSA**, que funciona: un WAV de 0.3 s se reprodujo completo (`get_time()==length==0.3`) `[M]`. Es una observación local (PipeWire con compat Pulse y ALSA presentes); no pudimos confirmar si el fallo del backend Pulse es del wheel o del entorno. **Riesgo menor:** si el audio no suena en otra máquina, revisar `ALSOFT_DRIVERS` y la cadena PipeWire/ALSA.
- **Ursina** no trae motor de audio propio: usa el de Panda3D (`ursina.audio`), con las mismas capacidades `[M]`.
- **pygame-ce** usa SDL_mixer: mezcla multicanal y panning estéreo por `Channel.set_volume(l, r)`, pero **no hay API de audio 3D posicional con listener** `[48]`. Para bolos/kart habría que implementarlo o usar otra lib.
- **raylib** usa miniaudio: reproduce WAV/OGG/MP3 y streams, pero su API de audio no tiene listener ni posiciones 3D; solo volumen maestro y volumen/pitch por sonido `[38]`. Verificado: `init_audio_device()` + `play_sound()` OK `[M]`.

---

## 3. Render 3D, glTF/GLB, materiales, shaders, cámaras y UI

| Capacidad | Panda3D | Ursina | pygame-ce + moderngl | raylib |
|---|---|---|---|---|
| Grafo de escena / transforms | Sí (`NodePath`) `[46]` | Sí (entidades) `[25]` | No | No (API inmediata) `[35]` |
| glTF/GLB | Plugin `panda3d-gltf` (glTF 2.0, GLB, luces, colisiones) `[9][10]` | Sí, vía `panda3d-gltf` `[24]` | No (habría que escribir loader) | Sí, glTF 2.0 con PBR metallic/roughness `[37]` |
| PBR / materiales | Shader generator + `panda3d-simplepbr` (IBL, sombras, tonemap) `[11][18]` | Materiales básicos; PBR vía simplepbr si se configura | GLSL a mano | glTF carga mapas PBR, pero el shader por defecto no es PBR (hay que usar `pbr.vs/fs` de los ejemplos) `[37]` |
| Shaders | GLSL y Cg; shader generator; compute shaders `[17][18][47]` | Shaders GLSL de Panda3D | GLSL crudo (control total) `[31]` | GLSL vía `rlgl`/`LoadShader` `[35]` |
| Cámaras / lentes | `Camera` + `Lens` (perspectiva, ortográfica, custom), múltiples cámaras y render-to-texture `[42]` | `Camera` de alto nivel | Matrices a mano | `Camera3D` + modos orbital/first-person `[35]` |
| UI | DirectGUI (botones, labels, entries, sliders, frames, menús) `[19]` | UI propia (Button, Text, Slider…) `[25]` | Ninguna (pygame_gui aparte) | raygui inmediata `[35]` |
| Post-proceso | FilterManager (bloom, SSAO, tonemap) `[44]` | Vía Panda3D | A mano | Shaders + render targets `[35]` |
| Animación esquelética | Sí (Actor, joints, anim blends) `[43]` | Sí | A mano | Sí (glTF animations) `[36]` |

Notas:

- **glTF en Panda3D es un plugin, no core.** El loader por defecto es Assimp y la propia doc dice que "la calidad de su converter no es muy buena"; recomienda `panda3d-gltf` `[9]`. Con el plugin instalado, `loader.loadModel("x.glb")` funciona directo `[9][M]`. Medido: `Box.glb` 0.047 s; `DamagedHelmet.glb` (3.7 MB) 0.79 s la primera vez, luego se cachea la conversión `[M]`.
- **PBR en Panda3D requiere add-on.** La doc de glTF lo dice explícitamente: para ver bien los materiales PBR hace falta un shader propio o `panda3d-simplepbr` `[9]`. Con simplepbr 0.13.1 renderizamos el DamagedHelmet con sombras, IBL y tonemapping a 1080p `[M]`; el script guarda una captura para verificarlo a ojo.
- **raylib carga glTF PBR** (metallic/roughness, mapas de material) `[37][36]`, pero el pipeline por defecto no aplica PBR: hay que cargar un shader PBR propio, como el `pbr.fs` de los ejemplos `[36]`. Además, el CHANGELOG avisa que **no soporta compresión Draco** `[36]`.
- **Ursina** es cómoda para prototipos (una entidad = un cubo en 3 líneas) pero no agrega capacidades de motor: todo lo pesado sigue siendo Panda3D.

---

## 4. Física

- **Panda3D** trae **Bullet** integrado en el wheel (`panda3d.bullet`): rigid bodies, soft bodies, constraints, character controller y **vehículos raycast** (`BulletVehicle`, pensado para juegos de conducción arcade) `[12][13]`. Verificado en esta máquina: una caja con masa cae y se apoya correctamente sobre un plano (z final 1.4998 con plano en z=1 y semialtura 0.5), y `BulletVehicle` se instancia sin error `[M]`.
- **Ursina** envuelve ese Bullet: `PhysicsHandler` crea un `BulletWorld` y `Entity` expone colliders, raycast y boxcast `[26]`. Es una capa fina; no hay física propia.
- **pygame + moderngl/PyOpenGL**: no hay física. La opción habitual, **pybullet**, no publica wheels para 3.14 (última 3.2.7, 2025-01-30; tags hasta cp311) `[39]`: habría que compilar desde sdist o usar otra librería. Para bolos (colisiones de esferas/cajas) se podría escribir a mano, pero kart necesita suspensión, fricción y vehículo: mucho trabajo.
- **raylib**: solo trae **physac**, física **2D**; no hay física 3D ni vehículos `[35][M]`. Para kart habría que integrar Bullet/Jolt por fuera (y en Python 3.14 eso hoy significa compilar pybullet o usar los bindings de otro motor).

**Conclusión:** solo Panda3D (y Ursina por herencia) cubre física 3D + vehículos con un paquete instalable en 3.14.

---

## 5. Performance en Intel Iris Xe a 1080p

### 5.1 Método

- Máquina: Intel Core i5-11320H, **Intel Iris Xe Graphics (TGL GT2)**, Mesa 26.2.5, Linux 7.2.15 (Omarchy), sesión Wayland/Hyprland.
- Python 3.14.10 (uv), `panda3d==1.10.16`, `panda3d-gltf==1.3.0`, `panda3d-simplepbr==0.13.1`, `raylib==6.2.0.0`, `pygame-ce==2.5.8`, `moderngl==5.13.0` `[M]`.
- Escena: buffer **offscreen 1920x1080**, vsync off, pipeline de render single-thread, N cubos (`models/box`) con luz ambiental + directional; cada cubo es un Geom/draw call separado (salvo `--flatten`). Se mide **GPU-complete** con `glFinish()` después de cada frame; sin `glFinish` los números son de submission y no sirven `[M]`.
- Reproducible: `research/bench/panda3d_bench_1080p.py` y `research/bench/panda3d_bench_pbr.py`.

### 5.2 Resultados

| Escena (1080p) | FPS (GPU-complete) | ms/frame |
|---|---|---|
| Panda3D — 300 cubos, sin sombras | **427–446** | 2.24–2.34 |
| Panda3D — 300 cubos + shadow map 2048² | **233–236** | 4.24–4.29 |
| Panda3D — 2000 cubos + shadow map 2048² | **111–113** | 8.82–8.98 |
| Panda3D — 2000 cubos, `flattenStrong()` + shadow map | **132–148** | 6.74–7.59 |
| Panda3D — glTF PBR (DamagedHelmet, 15k tris) + sombras + tonemap | **102–109** | 9.1–9.8 |
| raylib — 300 cubos, sin sombras (ventana oculta) | **462** | 2.16 |
| pygame-ce + moderngl — quad fullscreen (no es una escena 3D) | 1439 | 0.69 |
| Ursina — 100 entidades en ventana | 60.8 (vsync) | — |

Lectura:

- **El target de 60 fps es holgado.** Incluso el peor caso sintético (2000 draw calls + sombras) da ~111 fps; con batching sube a ~140. Un juego de bolos (1 pista, 10 pinos, bola, UI) va a estar dominado por fill-rate y no por geometría.
- **Kart es viable**, pero el costo está en draw calls y en el shadow pass, no en triángulos. La doc de Panda3D lo advierte: muchos nodos pequeños = muchos batches, y la solución es `flattenStrong`/instancing para geometría estática y LOD/culling para lo dinámico `[21]`. Medido: flatten de 2000 cubos recupera ~25–30% (132–148 vs 111–113) cuando el cuello es GPU; cuando el cuello es CPU/submission, el batching rinde mucho más (en una corrida sin `glFinish` la mejora fue ~4x) `[M]`.
- **PBR completo a 1080p con sombras da ~105 fps**: alcanza para el look del juego, con margen.
- **Comparación con raylib:** en la escena equivalente (300 cubos, sin sombras, 1080p) Panda3D 427–446 fps vs raylib 462 fps. Es la misma GPU y el mismo driver: la diferencia es ruido/metodología. Ninguna alternativa “gana” en GPU; la decisión es de features y ergonomía.
- **Caveats:** benchmark sintético, no un juego; no incluye carga de assets, física ni Python de gameplay. Las cifras varían ±15% con el estado de la GPU (frecuencias, temperatura, memoria compartida). No se midió latencia de input ni frame pacing.

---

## 6. Empaquetado, licencia y tamaño

| Aspecto | Panda3D | Ursina | pygame-ce + moderngl | raylib |
|---|---|---|---|---|
| Instalación | Wheel 54 MB; 114 MB instalado `[1][M]` | 4.3 MB + arrastra Panda3D `[24]` | 12 MB + 0.3 MB `[29][32]` | Wheel 2.4 MB; 7 MB instalado `[34][M]` |
| Dependencias | Autocontenido (libpanda, Bullet, OpenAL, Assimp, Cg) `[M]` | Panda3D + glTF + Pillow + pyperclip + screeninfo + sswg `[24]` | SDL2 + GL del sistema | cffi + GLFW/raylib embebidos `[34]` |
| Distribución | `build_apps`/`bdist_apps` (setuptools): binarios standalone para Windows/Linux/macOS `[20]` | Hereda Panda3D; no documenta packaging propio | Manual (PyInstaller/Nuitka) | Manual; el wheel no incluye un packager |
| Licencia | Modified BSD (3-clause) `[22]` | MIT `[24]` | LGPL-2.1 `[29]` | Bindings EPL-2.0; raylib zlib `[35]` |
| Riesgo de licencia | Ninguno para uso personal/comercial | Ninguno | LGPL: permitir relink (dinámico) | EPL-2.0: copyleft débil por archivo |

- **Panda3D** es la opción más "pesada" (114 MB instalado) pero la única que trae todo: no hay que ensamblar audio, física y carga de modelos por separado. `build_apps` permite empaquetar cada juego como binario standalone y descargar wheels optimizados `[20]`. No probamos `build_apps` en esta sesión (ver riesgos).
- **raylib** es el más liviano, pero el binding es EPL-2.0 (no BSD/MIT) y no trae física 3D ni audio 3D: lo que ahorrás en MB lo pagás en código propio.
- **pygame-ce** es LGPL-2.1: para un proyecto personal no es problema; si algún día se distribuye estáticamente, hay que revisar la cláusula de relink.

---

## 7. ¿Sirve para juegos variados (bolos, kart), no solo demos?

**Bolos (primer juego): sí, de sobra.** Necesita: pista y pinos con colisiones (Bullet rígidos), bola con física, cámara, UI de puntaje (DirectGUI), audio de impactos (OpenAL 3D), input de Wiimote/mandos (InputDevice) y assets glTF. Todo está en el wheel + dos add-ons. La performance sobra (300 cubos = 430 fps).

**Kart (futuro): sí, con diseño cuidadoso.**
- Física: `BulletVehicle` es exactamente el modelo raycast que usan los juegos de conducción arcade `[13]`.
- Render: el presupuesto de draw calls es el límite. La doc de Panda3D recomienda batch/merge de geometría estática y cuidado con muchos nodos `[21]`; medido, 2000 draw calls + sombras = 111 fps, y con flatten = 132–148. Un circuito con geometría estática fusionada y pocos objetos dinámicos entra cómodo en 60 fps.
- Input: gamepads evdev `[16]`; el Wiimote queda por validar (no hay hardware en esta sesión).
- La consola es general: el mismo `ShowBase` puede cargar cualquier juego; no hay nada específico de deportes en la API.

**Implicación para la consola (launcher/plugins):** Panda3D **no permite dos `ShowBase` a la vez**; el código lanza `Exception("Attempt to spawn multiple ShowBase instances!")` si ya existe `base` `[41]`. Para plugins in-process hay que destruir el `ShowBase` del juego anterior (`base.destroy()`) y crear uno nuevo al lanzar el siguiente, o diseñar un único `ShowBase` que cambie de escena. Es una decisión de arquitectura, no un bloqueante, pero conviene tenerla presente en el ticket de launcher.

**Input Android por WebSocket:** Panda3D expone `EventQueue` para encolar eventos y consumirlos en el hilo del motor `[45]`; es el patrón a evaluar si el servidor WebSocket corre en un hilo aparte. La seguridad entre hilos de ese patrón no la validamos en esta sesión (fuera de alcance).

---

## 8. Versión de Python a fijar

**Fijar 3.14** (probado 3.14.8 y 3.14.10).

```toml
# pyproject.toml
requires-python = ">=3.14,<3.15"
dependencies = [
    "panda3d==1.10.16",
    "panda3d-gltf>=1.3.0",
    "panda3d-simplepbr>=0.13.1",
]
```

```
# .python-version
3.14
```

Por qué:

| Versión | Estado | Decisión |
|---|---|---|
| **3.14** | Estable desde 2025-10-07; parches hasta 3.14.10 (2026-10-25) `[40]`; Panda3D publica cp314/cp314t `[1]`; probado `[M]` | **Pin** |
| 3.15 | Estable desde 2026-10-09 (3.15.2) `[40]`; **Panda3D no tiene wheels cp315 ni sdist** `[1]`; `uv pip install --only-binary :all: panda3d` en 3.15 falla con "no wheels with a matching Python ABI tag" `[M]` | No usar todavía |
| 3.13 | Soportado desde Panda3D 1.10.15 (2024-11) `[3]`; wheels cp313 `[1]` | Fallback válido si alguna dependencia no tiene 3.14 |
| 3.12 | Soportado desde 1.10.14 `[3]` | Demasiado atrás; sin motivo |

**No usar el build free-threaded** (`cp314t`) para el proyecto: hay wheels, pero los add-ons (simplepbr, panda3d-gltf) y el ecosistema no están probados en free-threading. El GIL no es el cuello de botella de un juego con render en C++.

**Revisar el pin cuando salga Panda3D 1.11 o una 1.10.17 con cp315**; hasta entonces, 3.15 obliga a compilar el motor a mano.

---

## 9. Hello world y benchmark

### 9.1 Hello world mínimo

`research/bench/panda3d_hello.py` (ventana + cubo girando + luces):

```python
from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, ClockObject, DirectionalLight, Vec4

base = ShowBase()
base.disableMouse()
base.cam.setPos(0, -6, 2.5)
base.cam.lookAt(0, 0, 0)

amb = AmbientLight("amb"); amb.setColor(Vec4(0.35, 0.35, 0.4, 1))
base.render.setLight(base.render.attachNewNode(amb))
sun = DirectionalLight("sun"); sun.setColor(Vec4(0.95, 0.9, 0.85, 1))
sun_np = base.render.attachNewNode(sun); sun_np.setHpr(35, -35, 0)
base.render.setLight(sun_np)

box = base.loader.loadModel("models/box")   # incluido en el wheel
box.reparentTo(base.render); box.setScale(1.5)

def spin(task):
    box.setH(box.getH() + 45 * ClockObject.getGlobalClock().getDt())
    return task.cont

base.taskMgr.add(spin, "spin")
base.run()
```

Ejecutar:

```bash
# en la raíz del repo/worktree
uv venv --python 3.14
uv pip install panda3d==1.10.16 panda3d-gltf panda3d-simplepbr
uv run python research/bench/panda3d_hello.py
```

### 9.2 Benchmark

```bash
uv run python research/bench/panda3d_bench_1080p.py --cubes 300
uv run python research/bench/panda3d_bench_1080p.py --cubes 300 --shadow
uv run python research/bench/panda3d_bench_1080p.py --cubes 2000 --shadow
uv run python research/bench/panda3d_bench_1080p.py --cubes 2000 --shadow --flatten
uv run python research/bench/panda3d_bench_pbr.py --glb /ruta/DamagedHelmet.glb
```

Resultados esperados en esta máquina: los de la tabla 5.2. El script imprime renderer, pipe, tamaño y ms/frame; sirve como smoke test de regresión si cambia el driver o la versión de Panda3D.

### 9.3 Verificación funcional hecha en esta sesión

- Instalación con `uv` en 3.14.8 y 3.14.10 `[M]`.
- Ventana + fullscreen 1920x1080 `[M]`.
- Carga glTF/GLB (Box y DamagedHelmet) `[M]`.
- Render PBR con simplepbr (captura verificada) `[M]`.
- Bullet: caída de caja y `BulletVehicle` `[M]`.
- Audio OpenAL: reproducción completa de un WAV `[M]`.
- Ursina 8.3.0 sobre 3.14: ventana + 100 entidades a 60 fps (vsync) `[M]`.
- pygame-ce en Wayland nativo + moderngl GL 4.6 `[M]`.
- raylib en Wayland nativo + cubos 3D + carga GLB + raygui `[M]`.

---

## 10. Riesgos y preguntas abiertas

| Riesgo | Impacto | Mitigación / estado |
|---|---|---|
| **Sin Wayland nativo en Panda3D** (#1579 abierto) `[6]` | Depende de XWayland; si se desactiva, no arranca | Aceptable hoy en Omarchy/Hyprland; documentar requisito; seguir el issue |
| **High-DPI** (#426 abierto desde 2018) `[7]` | UI pequeña en pantallas 1440p/4K con scaling | Target actual 1080p; si se sube de resolución, prototipar escalado de UI |
| **Ventana tiling en Hyprland** `[M]` | La ventana no respeta tamaño si no es fullscreen/flotante | Launcher y juegos en fullscreen/borderless; reglas de ventana |
| **Python 3.15 sin wheels** `[1][M]` | No se puede instalar hasta nuevo release de Panda3D | Pin 3.14; revisar cuando haya 1.10.17/1.11 |
| **Cadencia de releases lenta** (1/año) `[2]` | Un bug puede tardar en llegar a un wheel | El repo está activo; se puede construir desde `master` si hace falta (caro) |
| **PBR/glTF son add-ons de un solo maintainer** (Moguri) `[10][11]` | Si se rompen con una versión nueva, hay que escribir shaders/loader propios | Pinear versiones; el shader generator de Panda3D permite GLSL propio como fallback |
| **Audio Pulse falla y cae a ALSA** `[M]` | En algunas máquinas podría no haber audio | Verificar en la máquina objetivo; `ALSOFT_DRIVERS=alsa` o instalar libpulse; no confirmado como defecto general |
| **`build_apps`/`bdist_apps` no probado en 3.14** `[20]` | El empaquetado final podría requerir ajustes | Prototipo de empaquetado en un ticket aparte antes de distribuir |
| **Wiimote por evdev no probado** `[16]` | El input principal del proyecto no está validado | Ticket de prototipo de input; el simulador de mandos cubre mientras tanto |
| **Ursina como base** | Releases atrasados, API cambiada, dependencia `sswg` `[24][25][27]` | No usarla como base; solo prototipos desechables |
| **raylib: física 3D/audio 3D ausentes** `[35][38]` | Habría que integrar Bullet/Jolt y audio 3D por fuera | Descartado como base |
| **pygame/moderngl: motor a medida** `[31][32]` | Semanas/meses de trabajo en escena, assets, física, UI | Descartado como base |
| **pybullet sin wheels 3.14** `[39]` | Física 3D en stacks no-Panda3D requiere compilar | Refuerza la elección de Panda3D |

**No confirmado (no inventar):**

- Que Panda3D 1.10.16 sea "oficialmente" 3.14: hay wheels + classifier + commit, pero las release notes no lo dicen con todas las letras `[1][3][4][5]`.
- Que el fallo del backend Pulse de OpenAL sea general o de esta máquina `[M]`.
- El rendimiento real de un juego de kart (curvas, sombras, post-proceso, IA) más allá del benchmark sintético.
- `build_apps` funcionando en 3.14 (no ejecutado).
- Soporte de Wiimote/accelerometer vía `InputDevice` (sin hardware).
- Latencia input→render y frame pacing (no medidos).

---

## 11. Fuentes

1. **PyPI — panda3d 1.10.16 (archivos/wheels)** — https://pypi.org/project/panda3d/1.10.16/#files — wheels cp314/cp314t manylinux2014 x86_64; no hay sdist; tamaño 54 MB. Metadatos: https://pypi.org/pypi/panda3d/json
2. **GitHub — Panda3D releases** — https://github.com/panda3d/panda3d/releases — 1.10.16 (2025-12-25), 1.10.15 (2024-11-08), 1.10.14 (2024-01-09); actividad del repo.
3. **Panda3D — ReleaseNotes** — https://github.com/panda3d/panda3d/blob/v1.10.16/doc/ReleaseNotes — 1.10.15 "adds support for Python 3.13"; 1.10.14 "adds support for Python 3.12"; 1.10.16 no menciona 3.14.
4. **Panda3D — setup.cfg v1.10.16** — https://github.com/panda3d/panda3d/blob/v1.10.16/setup.cfg — classifier `Programming Language :: Python :: 3.14`.
5. **Panda3D — commit "Add Python 3.14 to setup.cfg"** — https://github.com/panda3d/panda3d/commit/e560eb8da370d86b096d6cb65eafd9ab40879b9a — fecha 2025-12-25.
6. **Panda3D issue #1579 "Wayland support"** — https://github.com/panda3d/panda3d/issues/1579 — abierto; hoy se pasa por XWayland; sin ETA.
7. **Panda3D issue #426 "Better support for high-DPI screens needed"** — https://github.com/panda3d/panda3d/issues/426 — abierto desde 2018.
8. **Panda3D — árbol de fuentes v1.10.16** — https://github.com/panda3d/panda3d/tree/v1.10.16/panda/src — módulos `glxdisplay`, `x11display`, `egldisplay`, `wgldisplay`; ninguno de Wayland (igual en `master`).
9. **Panda3D Manual — glTF Files** — https://docs.panda3d.org/1.10/python/pipeline/gltf-files — Assimp por defecto, calidad pobre; recomienda `panda3d-gltf`; PBR requiere shader propio o `panda3d-simplepbr`.
10. **PyPI — panda3d-gltf** — https://pypi.org/project/panda3d-gltf/ ; README: https://github.com/Moguri/panda3d-gltf — glTF 2.0/GLB, KHR_lights_punctual, BLENDER_physics, `collision_shapes` builtin/bullet.
11. **PyPI — panda3d-simplepbr** — https://pypi.org/project/panda3d-simplepbr/ — PBR/IBL/sombras para Panda3D; BSD-3.
12. **Panda3D Manual — Bullet** — https://docs.panda3d.org/1.10/python/programming/physics/bullet/index — rigid bodies, soft bodies, character controller.
13. **Panda3D Manual — Bullet Vehicles** — https://docs.panda3d.org/1.10/python/programming/physics/bullet/vehicles — `BulletVehicle` raycast para conducción arcade.
14. **Panda3D Manual — Sound** — https://docs.panda3d.org/1.10/python/programming/audio/index — OpenAL Soft por defecto; FMOD/Miles alternativas.
15. **Panda3D Manual — 3D Audio** — https://docs.panda3d.org/1.10/python/programming/audio/3d-audio — `Audio3DManager` con listener.
16. **Panda3D Manual — Joystick Support** — https://docs.panda3d.org/1.10/python/programming/hardware-support/joystick-support — `InputDevice`, evdev en Linux, clases gamepad/steering_wheel.
17. **Panda3D Manual — Shader Basics** — https://docs.panda3d.org/1.10/python/programming/shaders/shader-basics — GLSL y Cg; GLSL recomendado.
18. **Panda3D Manual — Shader Generator** — https://docs.panda3d.org/1.10/python/programming/shaders/shader-generator — normal/gloss/glow maps, HDR, cartoon shading sin escribir shaders.
19. **Panda3D Manual — DirectGUI** — https://docs.panda3d.org/1.10/python/programming/gui/directgui/index — botones, labels, entries, frames.
20. **Panda3D Manual — Distributing Applications** — https://docs.panda3d.org/1.10/python/distribution/index — `build_apps`/`bdist_apps` standalone para Windows/Linux/macOS.
21. **Panda3D Manual — Too Many Meshes** — https://docs.panda3d.org/1.10/python/optimization/performance-issues/too-many-meshes — costo por batch; flatten/merge.
22. **Panda3D — LICENSE** — https://github.com/panda3d/panda3d/blob/v1.10.16/LICENSE — Modified BSD (3-clause).
23. **Panda3D Manual — Installing Panda3D in Linux** — https://docs.panda3d.org/1.10/python/introduction/installation-linux — solo RPM/DEB o compilar; no documenta pip/uv.
24. **PyPI — ursina 8.3.0** — https://pypi.org/project/ursina/ — `Requires-Python >=3.12`; MIT; deps panda3d>=1.10.15, panda3d-gltf, pillow, pyperclip, screeninfo, sswg==4.3.0.
25. **GitHub — pokepetter/ursina** — https://github.com/pokepetter/ursina — commits 2026-11-16; 57 contribuidores; release de PyPI 8.3.0 vs pyproject 8.4.0.
26. **Ursina — physics.py** — https://github.com/pokepetter/ursina/blob/master/ursina/physics.py — `PhysicsHandler` sobre `panda3d.bullet`.
27. **Ursina — pyproject.toml** — https://github.com/pokepetter/ursina/blob/master/pyproject.toml — `requires-python = ">=3.12"`.
28. **PyPI — pygame 2.6.1** — https://pypi.org/project/pygame/2.6.1/#files — última 2024-09-29; wheels hasta cp313.
29. **PyPI — pygame-ce 2.5.8** — https://pypi.org/project/pygame-ce/2.5.8/#files — cp314/cp315; LGPL-2.1; SDL 2.32.10.
30. **GitHub — pygame-community/pygame-ce** — https://github.com/pygame-community/pygame-ce — actividad diaria (commit 2026-11-15).
31. **ModernGL — README** — https://github.com/moderngl/moderngl — "wrapper over OpenGL Core"; sin escena/assets/audio/física.
32. **PyPI — moderngl** — https://pypi.org/project/moderngl/ — 5.13.0; cp314; MIT; `glcontext`.
33. **PyPI — PyOpenGL** — https://pypi.org/project/PyOpenGL/ — 3.1.10; py3-none-any; BSD.
34. **PyPI — raylib 6.2.0.0** — https://pypi.org/project/raylib/6.2.0.0/#files — cp310–cp315 wheels; depende de cffi.
35. **GitHub — raylib-python-cffi** — https://github.com/electronstudio/raylib-python-cffi — EPL-2.0; raylib 6.2 + raymath + raygui + rlgl + physac + GLFW 3.5.1; API `pyray`.
36. **raylib — CHANGELOG 6.2** — https://github.com/raysan5/raylib/blob/6.2/CHANGELOG — Wayland habilitado por defecto en Linux; glTF PBR; "draco compression not supported".
37. **raylib — src/rmodels.c** — https://github.com/raysan5/raylib/blob/6.2/src/rmodels.c — glTF 2.0 metallic/roughness, carga de mapas PBR.
38. **raylib — src/raylib.h** — https://github.com/raysan5/raylib/blob/6.2/src/raylib.h — API de audio sin listener/posición 3D (solo volumen maestro y por sonido).
39. **PyPI — pybullet 3.2.7** — https://pypi.org/project/pybullet/ — sin wheels cp314; última 2025-01-30.
40. **python.org — calendario de releases** — https://www.python.org/downloads/ ; API: https://www.python.org/api/v2/downloads/release/ — 3.14.0 (2025-10-07), 3.14.10 (2026-10-25), 3.15.0 (2026-10-09), 3.15.2 (2026-10-25).
41. **Panda3D — ShowBase.py** — https://github.com/panda3d/panda3d/blob/v1.10.16/direct/src/showbase/ShowBase.py — lanza `Exception("Attempt to spawn multiple ShowBase instances!")` si `base` ya existe.
42. **Panda3D Manual — Camera Control** — https://docs.panda3d.org/1.10/python/programming/camera-control/index — `Camera`, lentes, múltiples cámaras.
43. **Panda3D Manual — Loading Actors and Animations** — https://docs.panda3d.org/1.10/python/programming/models-and-actors/loading-actors-and-animations — `Actor`, animaciones esqueléticas.
44. **Panda3D Manual — Common Image Filters** — https://docs.panda3d.org/1.10/python/programming/render-to-texture/common-image-filters — bloom, SSAO y otros filtros vía FilterManager.
45. **Panda3D API — EventQueue** — https://docs.panda3d.org/1.10/python/reference/panda3d.core.EventQueue — cola de eventos para consumir en el hilo del motor.
46. **Panda3D Manual — The Scene Graph** — https://docs.panda3d.org/1.10/python/programming/scene-graph/index — `NodePath`, jerarquía y transforms.
47. **Panda3D Manual — Compute Shaders** — https://docs.panda3d.org/1.10/python/programming/shaders/compute-shaders — soporte de compute shaders GLSL.
48. **pygame-ce docs — pygame.mixer** — https://pyga.me/docs/ref/mixer.html — mezcla multicanal y `Channel.set_volume(left, right)`; sin listener/posición 3D.
49. **Ursina — input_handler.py** — https://github.com/pokepetter/ursina/blob/master/ursina/input_handler.py — `held_keys`, `mouse` y helpers de input sobre Panda3D.

**Mediciones `[M]`:** scripts en `research/bench/`, ejecutados en esta máquina con Python 3.14.10, panda3d 1.10.16, Mesa 26.2.5, Iris Xe (TGL GT2), Wayland/Hyprland. Los números de fps son GPU-complete (`glFinish`) salvo donde se indica.
