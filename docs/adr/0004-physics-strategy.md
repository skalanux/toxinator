# Física de bolos: bola dinámica con CCD y pinos Bullet a paso fijo

La plataforma usa SI (1 unidad = 1 m), un `PhysicsWorld` con paso fijo de 1/120 s, interpolación de render y CCD en la bola. La bola es una esfera dinámica de ~7 kg con velocidad/efecto iniciales del `throw`; los pinos son convex hull/compound de 1.5 kg con colisiones Bullet; la pista es estática. El solver usa 10–20 iteraciones; `bullet-additional-damping` solo si aparece jitter.

Se eligió frente a una bola kinemática con sweep manual (más código y colisiones propias) y frente a una bola totalmente arcade (menos pin action). La bola dinámica + CCD da colisiones robustas y pin action creíble, con tuning arcade en el throw y la fricción. El costo es que la trayectoria no es 100% controlada y que el determinismo exacto depende del build/plataforma; los tests usan tolerancia y replay de inputs.

**Status**: accepted

**Consequences**: `PhysicsWorld` se suma a `GameContext` en API 1.1; el juego puede optar por Bullet directo; los parámetros iniciales viven en la config del juego; la validación requiere un prototipo de pinos.
