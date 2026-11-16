# Input hub in-process con ControllerFrame canónico

La consola agrega todos los mandos en un hub in-process, con poll al inicio de cada frame, y expone a los juegos un `ControllerFrame` canónico (botones físicos, ejes, accel/gyro/orientación relativa al neutro, pointer y touch) más `InputState`/`ActionState`. Los gestos viven en una librería de plataforma opcional, no en el core.

Se eligió frente a un servicio de input separado y frente a frames crudos por dispositivo para evitar IPC, hacer intercambiables Wiimote, celular Android y gamepad, y mantener el input testeable con trazas. El costo es que el hub comparte proceso con el game loop y que `ShowBase` abre el nodo IR del Wiimote, con el consumo de batería correspondiente.

**Status**: accepted

**Consequences**: el contrato de juego depende de `InputState`/`ActionState`; cada adaptador de mando normaliza a un frame canónico; los juegos pueden optar por gestos de plataforma o implementar los suyos.
