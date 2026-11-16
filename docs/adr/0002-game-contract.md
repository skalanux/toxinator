# Contrato de juego: consola dueña del ShowBase y plugins con GameContext

La consola es dueña de un único `ShowBase` y entrega a cada juego un `Game` con `GameContext` (escena, viewports, input, audio, assets, settings, save, i18n, log, eventos). Los juegos no crean ventanas ni `ShowBase`; implementan el lifecycle y usan los servicios. El manifest declara `requires_api`, capacidades y modos; el `GameHost` in-process descubre, carga y ejecuta, y deja el seam para subprocess.

Se eligió frente a un `ShowBase` por juego (la recomendación del research) porque el singleton de Panda3D deja de ser un problema si la consola es la única dueña, el launcher no parpadea al cambiar de juego y los servicios quedan centralizados. El costo es que la consola debe limpiar escena/tasks/audio de cada juego y que un crash duro se lleva el proceso; el `GameHost` permite migrar a subprocess después.

**Status**: accepted

**Consequences**: los juegos dependen de la API semver y del `GameContext`; el runtime implementa `InProcessHost`; la física se suma como servicio opcional después de #10; los juegos no pueden leer input ni abrir red directo.
