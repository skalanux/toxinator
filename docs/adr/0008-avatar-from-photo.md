# Avatares 3D desde foto, locales y sin nube

La consola crea avatares 3D paramétricos estilo Mii a partir de una foto del
celular. El avatar es un conjunto de parámetros (forma de cabeza, tono de piel,
pelo, ojos, nariz, boca, accesorios y colores) que la consola guarda como JSON y
construye en runtime con primitivas de Panda3D; no se guarda un modelo editado a
mano. La foto solo inicializa los parámetros con heurísticas locales de color y
proporción (Pillow), el jugador ajusta el resto en un editor de la consola, y la
foto se descarta al terminar. Los avatares viven en
`~/.local/share/toxinator/avatars/`, asociados al perfil local de jugador
(varios avatares por consola, uno activo por jugador), y los juegos los consumen
con un servicio nuevo `ctx.avatar`.

Se eligió frente a un avatar 2D o una foto pegada como textura porque el objetivo
es el equivalente al Mii: un personaje reutilizable y editable, no un retrato. Se
eligió no usar ML local (OpenCV/mediapipe) en la v1 porque agrega peso, tiempos
de build y modos de falla nuevos; la foto alcanza para arrancar el editor. Se
eligió guardar parámetros y construir en runtime frente a exportar un modelo por
avatar porque evita un pipeline de assets y mantiene un único rig de plataforma.

**Status**: accepted

**Consequences**: nuevo servicio `AvatarService` y almacenamiento local; el
launcher suma la pantalla de captura/edición; `ctx.avatar` entrega parámetros y
un constructor de `NodePath` por slot, con cache en memoria; el avatar entra en
la API `0.4`; la foto requiere HTTPS (igual que el QR) y no se
persiste por defecto. Sin cuenta, sin nube y sin subida de avatares entre
consolas. Depende de la captura de foto del mando v2 (ADR-0007).
