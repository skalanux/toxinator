# Monorepo con workspace uv y frontera pública toxinator.api

El repo es un workspace uv: el paquete `toxinator` en la raíz (`src/toxinator/...`) y cada juego como paquete separado (`games/<id>/`), más `controller-web/` estático, `docs/` y `tests/`. `toxinator.api` es el único módulo que un juego puede importar del runtime; `core` depende de `api`, `input`/`render`/`physics` de `core`+`api`, y `launcher` de `core`+`input`+`render`. Un test de fronteras lo verifica.

Se eligió frente a un paquete único y frente a un workspace multi-paquete por el equilibrio entre simplicidad y extracción futura: el juego ya es una distribución separada, pero comparte lockfile y venv. El costo es un test de fronteras y disciplina de imports; el beneficio es que mover un juego a su repo es packaging, no reescritura.

**Status**: accepted

**Consequences**: los juegos dependen de `toxinator.api`; el runtime y los juegos comparten un `uv.lock`; `controller-web` no comparte código Python; el corte phone-only es el primer milestone.
