# Mando celular v2: PWA única, botones PlayStation y simulador de teclado/mouse

El mando de la consola es la PWA `controller-web`, rediseñada de punta a punta.
Se retira la UI vieja (A/B, skins tokyo, readout siempre visible) y el Wiimote
sale del roadmap y de la documentación: nunca hubo código de Wiimote, solo
menciones en README, glosario, ADRs y checklist. Los botones canónicos pasan a
ser `cross`, `circle`, `square`, `triangle`, `options`, `l1` y `r1`, con `A`/`B`
como alias de compatibilidad durante una versión de API. El mando agrega un stick
analógico izquierdo con retorno al centro, una zona táctil derecha absoluta, y
layouts landscape y vertical con override por juego. El perfil `controller` que
ya viaja por WebSocket se extiende con orientación, labels por botón, panel de
imagen estática y bandera de cámara. La foto del celular se sube por HTTP
autenticado (no por el canal de input) y alimenta la creación de avatares
(ADR-0008). Un `KeyboardMouseSource` de pleno derecho entra al `InputHub` con
`source="sim"`, y `InputState.primary_frame()` hace que la consola prefiera el
teléfono y caiga al teclado.

Se eligió frente a conservar la UI vieja como modo legacy, frente a renombrar los
botones en seco, y frente a dejar teclado/mouse como atajos solo del launcher,
porque el rediseño cambia la anatomía del mando (cuatro botones de acción, stick
y panel) y mantener dos UIs en una PWA sin build step es deuda sin retorno. El
Wiimote no tenía implementación que preservar. El teclado/mouse como atajos del
launcher no permite jugar ni testear juegos sin celular, que es el objetivo.

**Status**: accepted

**Consequences**: `ControllerFrame.buttons` usa nombres canónicos y emite `A`/`B`
como alias; `API_VERSION` sube a `0.3`; el launcher y Maldito Pino migran a
`state.primary_frame()` y `frame.pointer`; el protocolo WebSocket sube a v2 y
agrega los mensajes `panel` y el endpoint HTTP de foto; la PWA se reescribe con
tests de shell nuevos; la documentación, el checklist manual y `pyproject.toml`
dejan de mencionar Wiimote. Sin d-pad, sin L2/R2 y sin minimapa vivo en esta
versión. Reemplaza la suposición de ADR-0001 sobre Wiimote; el hub y el frame
canónico siguen vigentes.
