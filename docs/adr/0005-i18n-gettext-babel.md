# i18n con gettext + Babel, catálogos por dominio y cambio en runtime

La consola y los juegos usan gettext (`.po`/`.mo`) con claves semánticas estables, Babel para números/fechas y un `I18nService` que carga un catálogo por dominio y locale. Los dominios son `toxinator` para la consola y el id del paquete para cada juego; los catálogos viven dentro de cada paquete. El idioma se cambia en runtime sin reiniciar: el servicio cambia los catálogos, persiste el ajuste y emite `language_changed`. Español es el default; inglés el segundo locale; el resto cae a español. Los assets se superponen por locale (`common/` + `<locale>/`) y los juegos sin el idioma activo caen a su `default_locale` con un aviso no bloqueante.

Se eligió frente a Fluent (más expresivo, pero una dependencia y un parser menos comunes en Python) y frente a un formato propio TOML/JSON (simple, pero obliga a reinventar plurales, formato, extracción y tooling). gettext es estándar, la stdlib lo soporta, Babel cubre CLDR y el ecosistema de traducción (Poedit, Weblate) lo entiende. El costo es el paso de compilación a `.mo`, que el traductor vea claves en vez de texto fuente y que el servicio tenga que envolver el formateo para respetar la frontera `toxinator.api`.

**Status**: accepted

**Consequences**: `.pot`/`.po` se commitean y `.mo` se genera al build; `scripts/i18n.py` y CI validan paridad, placeholders, fuzzy/vacíos/obsoletos; `I18nService` expone `tr`, `trn` y formateo; los juegos no importan Babel; el controlador web consume un JSON de la consola; `GLOSSARY.md` suma catálogo, dominio, clave, locale, pseudo-locale y asset localizado.
