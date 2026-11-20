# Testing: simulador de mandos, trazas JSONL y CI headless

La consola se testea en cuatro capas: unitarios puros de Python, integración con `InputHub` + game loop + Bullet + `ShowBase` headless, e2e smoke del launcher y checklist manual para hardware real. El simulador de mandos es una fuente más del `InputHub` (`source="sim"`) con presets TOML por juego; las trazas son JSONL versionadas de `ControllerFrame`s normalizados, grabables y replayables sin wall clock. El game loop usa un `Clock` inyectable, física a paso fijo 1/120 y RNG seedeado; los tests de física comparan con tolerancia. CI corre unit+integration+smoke+i18n sin hardware ni GPU; Wiimote, Android y performance quedan en el checklist manual.

Se eligió frente a depender de hardware real (frágil y no corre en CI), frente a solo mocks sintéticos (no valida el pipeline real) y frente a tests visuales/snapshots como gate (brittles y no cubren input/física). El costo es mantener el formato de traza, los presets y un `ShowBase` headless estable; el beneficio es reproducibilidad, tests rápidos y una validación manual explícita para lo que depende de hardware.

**Status**: accepted

**Consequences**: `ControllerSource`/`ReplaySource` se suman al input; `Clock` y `ctx.rng` entran en `GameContext`; `tests/unit`, `tests/integration` y `tests/e2e` se separan por directorio; CI usa `xvfb` y `window-type none`/`offscreen`; la cobertura se mide en core/input/physics/reglas; Android, teclado/mouse y performance se validan con `docs/testing/manual-checklist.md`.

**Nota**: [ADR-0007](0007-phone-controller-v2.md) retira el Wiimote; la validación manual cubre Android y el simulador de teclado/mouse.
