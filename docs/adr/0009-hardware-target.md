# Hardware soportado: Linux 64-bit, OpenGL de escritorio y Raspberry Pi 5 como referencia ARM

La consola corre en **Linux 64-bit con glibc** (x86_64 o aarch64) y un driver
**OpenGL de escritorio con perfil compatibilidad**; el piso funcional es OpenGL
2.1 y el objetivo es 3.1, que es lo que expone la Raspberry Pi 5 con Mesa/V3D.
La especificación mínima es 4 núcleos de ~1.5 GHz, 2 GB de RAM, ~1 GB de disco y
una ventana de 1280×720; el gate de release sigue siendo 60 FPS a 1080p
(`docs/testing/manual-checklist.md`). La **Raspberry Pi 5 (8 GB, Pi OS Trixie
64-bit)** es la referencia ARM; una Pi 4 de 4/8 GB es plausible pero no está
certificada. En x86, cualquier mini PC o notebook de la última década con GPU
Intel/AMD sobra.

Se eligió este target porque el corte actual no necesita más: mallas
procedurales de bajo poligonaje, pipeline fixed-function sin shaders propios, una
pista, diez pinos y una bola a paso fijo 1/120. Panda3D 1.10.16 publica wheel
`manylinux2014_aarch64` para Python 3.14, así que en la Pi no se compila nada, y
`uv` instala el intérprete que Pi OS no trae. Se descartaron los **Android boxes
baratos**: Android no es glibc (el wheel no instala), Termux/proot cae a
render por software (llvmpipe) y los SoC viejos tipo Amlogic S905 con Mali-450
solo tienen GLES 2.0, sin el OpenGL de escritorio que usa `pandagl`. Pasarlos a
Armbian solo tiene sentido en placas con GPU Bifrost/Panfrost (por ejemplo
RK3399), y aun así es más caro en tiempo que una Pi 5 o un mini PC x86 usado.

**Status**: accepted

**Consequences**: el soporte de Pi 5 es un objetivo hasta que se corra el
checklist en hardware real; `toxinator`, `toxinator play` y
`toxinator dev phone` aceptan `--fps` (overlay de FPS, frametime medio y peor
frame del último segundo; **F3** lo oculta) para medir sin PStats. La ventana
sigue fija en 1280×720: llevarla a 1080p exige cambiar el PRC y volver a medir.
No hay plan de backend GLES/Vulkan ni de pipeline solo-shader; si el split-screen
de 4, las sombras, los avatares o el audio suben el costo, este ADR se revisa con
mediciones nuevas. CI sigue sin GPU: la performance se valida a mano.
