# Prototype: launcher UX

Prototipo throwaway para **#11**. No es el launcher final; sirve para elegir
estructura, jerarquía, identidad y navegación antes de implementar la versión
Panda3D.

## Cómo abrirlo

Desde la raíz del repo:

```bash
python3 -m http.server 8080
```

Abrí:

```text
http://localhost:8080/prototype/launcher/?variant=C&theme=feria
```

También podés abrir `index.html` directo, pero el Gamepad API funciona mejor por
`localhost`.

## Dirección visual: La Feria Maldita

La variante C dejó de ser una grilla de tarjetas y pasó a ser el **cartel de una
feria de juegos malditos**. La consola es una carpa: los juegos son atracciones,
los mandos son entradas y el pin es el número principal.

- **Paleta**: lona `#0D3532`, papel `#F2E3C6`, oxblood `#8E1F1F`, mostaza
  `#E0A526`, coral `#E85C3A`, tinta `#17110C`.
- **Tipografía**: Nimbus Sans Narrow para carteles y titulares; Liberation Sans
  para la interfaz; Liberation Mono solo para datos de entrada. La versión final
  puede usar una woodtype/display licenciada.
- **Estructura**: marquesina con bombillas, carteles de papel con chinchetas,
  borde punteado en el cartel seleccionado y una **entrada general** perforada
  como hoja inferior.
- **Marca**: Toxinator 3 como la feria; tagline **LA FERIA MALDITA**; marca de
  ticket con pin; mascota **pin barker** con sombrero y moño.
- **Principios**: material físico (lona, papel, tinta), una sola pieza memorable
  (la marquesina/ticket), cero neón/glass/gradientes suaves. Las etiquetas
  funcionales van en sentence case; las mayúsculas quedan para los carteles.

La barra inferior cambia variante (`V`) y tema (`T`): **Feria**, **Cómic** y
**Neón**. Cómic y Neón quedan para comparar; Tóxica y Bolera 78 se descartaron
(quedan en el historial del branch). Actualiza `?variant=` / `?theme=`.

## Estados para revisar

Agregá `&screen=` a la URL:

```text
?screen=detail
?screen=players
?screen=settings
?screen=connecting
?screen=error
?screen=empty
?screen=help
?screen=launching      (&ready=1 para el estado listo)
```

## Controles

- `← ↑ → ↓` / WASD: navegar.
- `Enter` / `A`: seleccionar.
- `Esc` / `B`: volver.
- `S` / `Start`: ajustes.
- `P`: jugadores y mandos.
- `C`: conectar teléfono (QR mock).
- `E`: error de capacidades.
- `0`: biblioteca vacía.
- `Q`: apagar.
- `L`: idioma ES/EN.
- `H`: ayuda y estado actual.
- `J`: simular join de un mando.
- `V`: cambiar variante.
- `T`: cambiar tema.
- Gamepad estándar: D-pad/stick, A, B, Start.

## Capturas

**La Feria Maldita (variante C)**

- [Home](screenshots/feria-home.png)
- [Jugadores](screenshots/feria-players.png)
- [Ajustes](screenshots/feria-settings.png)
- [Conectar teléfono](screenshots/feria-connecting.png)
- [Error de capacidades](screenshots/feria-error.png)
- [Biblioteca vacía](screenshots/feria-empty.png)

**Layouts alternativos (tema Neón, el anterior)**

- [Variante A](screenshots/home-a.png)
- [Variante B](screenshots/home-b.png)
- [Variante C](screenshots/home-c.png)

**Comparación**

- [Cómic de barrio](screenshots/theme-comic.png)
- [Neón, el estado anterior](screenshots/theme-neon-before.png)

## Qué evaluar

- ¿La feria se siente propia de Toxinator 3 y no de cualquier launcher?
- ¿La marca funciona? (ticket-pin, pin barker, tagline, carteles)
- ¿La lona verde + papel + oxblood/mostaza es la paleta correcta?
- ¿La tipografía condensada va en esa dirección?
- ¿El cartel seleccionado con borde punteado y la entrada general se leen bien?
- ¿Qué partes de Cómic o Neón todavía querés conservar?
- ¿La navegación y los estados se entienden?

Las tipografías son stacks del sistema; cuando la dirección cierre, propongo
familias reales para licenciar/empaquetar. No se mergea a `main`; es un prototipo
para reaccionar.
