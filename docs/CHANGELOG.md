# Registro de cambios — Yelikshop Landing

Historial de todas las modificaciones hechas al landing page (`index.html`) y a los recursos en `assets/`.

El formato sigue un estilo tipo *Keep a Changelog*. Las fechas están en formato `AAAA-MM-DD`.

---

## [2.4.0] — 2026-10-13

Movimiento en la sección "Nuestros sabores": cuatro animaciones discretas, elegidas con una demo interactiva.

- **Entrada escalonada:** al aparecer en pantalla, cada tarjeta sube y aparece (`translateY(16px) scale(.97)` → su lugar, 600 ms), con 60 ms entre una y otra, en orden. Se dispara una sola vez por tarjeta con `IntersectionObserver`, así en el celular cada fila entra cuando llegas a ella.
- **Vasito que se asoma:** con el mouse encima, la tarjeta sube 4 px y el vasito recortado se levanta e inclina (`translateY(-8px) rotate(-3deg) scale(1.05)`, 400 ms).
- **Respuesta al toque en los botones:** `.btn:active` se encoge a `scale(.97)` en 160 ms. Aplica a todos los botones de la página, empezando por "Pedir", que en el celular no tenía ninguna respuesta.
- **Divisor que se dibuja:** el adorno sobre la sección se traza desde las puntas (1.1 s) y el corazón aparece al final.
- **Corrección:** el hover de las tarjetas ahora solo se activa con mouse (`@media (hover:hover) and (pointer:fine)`). Antes, en el celular la tarjeta quedaba levantada al volver de WhatsApp.
- **Tokens nuevos** en `:root`: `--ease-out` y `--ease-in-out`.
- **Accesibilidad y respaldo:**
  - con "reducir movimiento" activado en el sistema, las tarjetas solo aparecen suavemente y el divisor se muestra ya dibujado;
  - sin JavaScript todo se ve normal: el estado oculto depende de la clase `js-reveal`, que pone un script del `<head>`.
- Verificado con capturas reales de Chrome headless: entrada en orden, divisor dibujado y estado final completo.
- **Descartado:** html2canvas (convierte la página en imagen; no anima, pesa ~200 KB y no dibuja la sombra de los vasitos), vasitos flotando todo el tiempo, inclinación 3D con el mouse y confeti al pedir.

---

## [2.3.0] — 2026-10-13

Catálogo completo: **los 8 sabores** con vasito recortado estilo prototipo.

- **Las 6 tarjetas restantes** (Ron Pasas, Coco, Fresa, Chocolate, Parchita, Galleta) pasan a la variante `.sabor-media--cutout`; las 8 usan ahora `assets/vasito-*.webp` (1024×1024, alfa real, 63-81 KB c/u).
- **Recortes regenerados con un algoritmo nuevo** (`tools/quitar_cuadros.py`). La versión de agosto dejaba restos visibles de cuadros en Fresa y Galleta y comía bordes en Coco. Causa: el tablero pintado en las fotos es irregular (lo dibujó una IA):
  - celdas de 30-35 px con "costuras" de hasta 47 px y columnas angostas de 15 px;
  - en Parchita, un **mosaico** de tableros con las columnas desfasadas por zonas;
  - parches con la paridad invertida (dos celdas blancas juntas);
  - celdas "lavadas" y con **tinte rosado** del producto cerca del vaso.
- Cómo lo resuelve el script:
  - detecta las líneas del tablero (filas globales, columnas por franja) y clasifica **celda por celda**: es fondo si es uniforme y sus vecinas son todas más claras o todas más oscuras. El helado blanco no pasa la prueba porque sus vecinas tienen su mismo tono;
  - deduce el tono esperado de cada celda por paridad y refina píxel a píxel solo junto al producto (más profundo se comía las tapas de plástico);
  - borra las islas sueltas con mezcla exacta de blanco y gris del tablero;
  - convierte la **sombra pintada bajo el producto** en sombra transparente real, solo en la parte baja y solo si cubre celdas blancas y grises.
- Verificado: 8 tarjetas cargan sus recortes, alturas uniformes (360 px en escritorio, 245 px en móvil), 4/2 columnas, sin scroll horizontal.
- Limitaciones conocidas: con zoom quedan muescas pequeñas junto a algunas tapas y escalones leves en el vaso blanco del Coco (blanco sobre blanco). No se notan en la tarjeta; un PNG con transparencia real las eliminaría (ver PENDIENTES).

---

## [2.2.0] — 2026-08-31

Catálogo: primeras tarjetas con **vasito recortado estilo prototipo** (Oreo y Café).

- **Hallazgo:** los archivos de `assets/assets 2/` (oreo.png, cafe.png) **no tenían transparencia real** — eran RGB 100% opacos con el patrón de cuadros del editor **pintado en los píxeles** (se exportó la vista previa, no el PNG transparente).
- **Rescate por software:** se eliminó el patrón con detección de píxeles neutros + relleno por inundación desde los bordes (scipy), que solo borra lo conectado al fondo y protege el helado blanco del interior. Café quedó impecable; Oreo aceptable (el borde superior perdió la cúpula transparente, imposible de recuperar).
- **Nuevos assets:** `assets/vasito-oreo.webp` (86 KB) y `assets/vasito-cafe.webp` (65 KB) — 1024×1024, recortados, cuadrados y con alfa real.
- **Nueva variante de tarjeta** `.sabor-media--cutout`: vasito flotante con `object-fit: contain`, degradado radial rosa suave y sombra de apoyo — como las tarjetas del prototipo. Las tarjetas Oreo y Café ya la usan; las otras 6 siguen con foto hasta tener sus recortes.

---

## [2.1.0] — 2026-08-31

Datos de contacto confirmados contra el **sello de marca** del producto (la etiqueta circular azul que llevan los vasitos).

- **Usuario de Instagram corregido:** `@yelikshop_helados` → **`@yelik_shop`**. El sello es la fuente de verdad; el handle anterior no existía.
- **Enlaces de Instagram reales:** el texto de contacto y el botón social del footer ahora apuntan a `https://www.instagram.com/yelik_shop` (antes `href="#"`), con `target="_blank"` y `rel="noopener"`.
- **Número de WhatsApp validado:** el sello muestra `+58 412 5863169`, lo que **confirma** la corrección `472` → `412` hecha en la v1.0.0.

### CTA: logo vertical en lugar de la foto

- La imagen del CTA final (foto de Oreo con fondo de mármol, que desentonaba sobre la ola rosa) se reemplazó por el **logo vertical de la marca** (círculo YS + wordmark), a pedido del dueño.
- Nuevo asset: `assets/logo-vertical.webp` (640×564, 85 KB, con transparencia) — extraído del logo original que venía en `yelikshop_landing_final.zip` (resultó ser el mismo archivo que "ChatGPT Image … (2).png": tiene fondo transparente, no gris), recortado al contenido y convertido a WebP.
- Se suavizó el `drop-shadow` del CTA (estaba calibrado para la foto; en un logo de trazos finos se veía sucio).
- `assets/oreo-cutout.webp` y `assets/oreo-cutout.png` quedaron **sin uso** en la página.

### Redes del footer reorganizadas

- **Facebook eliminado** (no existe la página).
- **WhatsApp agregado** como botón social, enlazado a `wa.me/584125863169`.
- **TikTok agregado en modo "próximamente"**: se muestra el ícono pero **no es un enlace** — es un `<span class="ft-social-soon">` con fondo rosa suave, `cursor:default` y `aria-label="TikTok: próximamente"`. Cuando exista la cuenta, basta convertirlo en `<a href="…">` y quitarle la clase.
- Resultado: **ya no queda ningún `href="#"`** en toda la página.

---

## [2.0.0] — 2026-08-31

Reconstrucción completa del landing **fiel al prototipo de diseño** (`Prototipo.png`), construida con un workflow de **6 agentes en paralelo** (uno por sección) y ensamblada/verificada en navegador.

### Qué cambió

- **Página reescrita sección por sección siguiendo el prototipo:**
  - **Header**: logo real + nav (Inicio/Sabores/Sobre nosotros/Pedidos) + botón "Pedir ahora"; menú hamburguesa en móvil.
  - **Hero**: eyebrow, título serif con *"hecho con amor."* en itálica rosa + corazón doodle, línea decorativa, **un solo botón "Ver Sabores"** (como el prototipo), 3 badges de confianza con íconos de línea, y foto de fresa con **máscara orgánica tipo blob** sobre mancha rosa + corazón flotante.
  - **Divisor ornamental** caligráfico con corazón entre hero y sabores.
  - **Sabores**: solo el título "NUESTROS SABORES" (sin subtítulo, como el mock), 8 tarjetas blancas con botón píldora pequeño "Pedir".
  - **Sobre nosotros**: banda rosa (#fbe3ec) con kicker "EL TOQUE CASERO", título serif y 3 features con separadores verticales e íconos de línea (olla con corazones, ramita, cuchara).
  - **CTA**: continúa la banda rosa, con ola rosa profunda detrás del contenido, vasito de Oreo recortado y "¿Cuál vas a probar primero?"; transición de ola hacia el footer.
  - **Footer**: fondo blanco, 4 columnas (marca+doodle, Navegación, Contáctanos con íconos, Síguenos con botones circulares) y barra inferior.
- **Todos los íconos son SVG inline** de estilo línea (stroke 1.6, extremos redondeados), dibujados a medida — requisito explícito.
- **Se eliminaron** la sección "Cómo Pedir" y el segundo botón del hero (no existen en el prototipo).
- **Se conservaron** todas las mejoras técnicas de la v1.0.0: número 412 correcto (12 enlaces), Open Graph/favicon, año automático, skip-link, focus visible, `aria-hidden`, botón flotante de WhatsApp, imágenes con `width/height`, `oreo-cutout.webp`.

### Verificación

- Etiquetas balanceadas, sin IDs duplicados, 0 imágenes rotas, 0 errores de consola.
- Banda rosa continua entre #nosotros y #pedidos confirmada por estilos computados.
- Responsive verificado en 375px: hamburguesa funcional (aria-expanded), sabores a 2 columnas, hero apilado, sin scroll horizontal.

### Proceso

- 6 agentes en paralelo, cada uno con su recorte del prototipo en alta resolución (2x); tokens de diseño compartidos definidos centralmente; ensamblaje determinista por script.

---

## [1.0.0] — 2026-08-30

Primera ronda de optimización y corrección del sitio.

- **Commit:** `584aa11` — *"Optimiza y corrige el landing de Yelikshop"*
- **Autor:** davidcastlex-wq
- **Archivo principal:** `index.html`

### Resumen rápido

| Área | Cambio | Antes | Después |
|------|--------|-------|---------|
| Negocio | Número de WhatsApp | `472` (prefijo inexistente) | `412` |
| Estructura | `</div>` sobrante | HTML inválido | 69/69 balanceado |
| Conversión | Sección "Cómo Pedir" | No existía | 3 pasos |
| Conversión | Botón flotante de WhatsApp | No existía | Siempre visible |
| SEO | Open Graph + favicon | No existían | Añadidos |
| Mantenimiento | Año del footer | Fijo "2024" | Automático |
| Accesibilidad | Skip link, foco, `aria-hidden` | Faltaban | Añadidos |
| Rendimiento | `logo.png` | 356 KB | 17 KB |
| Rendimiento | `oreo-cutout` | 747 KB (PNG) | 114 KB (WebP) |

---

### 🔴 Correcciones críticas (negocio)

#### Número de WhatsApp corregido: `472` → `412`
- **Antes:** todos los enlaces apuntaban a `wa.me/584725863169`. El prefijo `0472` **no existe** en Venezuela (los válidos son 0412, 0414, 0416, 0424, 0426), por lo que todos los pedidos fallaban.
- **Después:** `wa.me/584125863169` en los **11 botones** (header, 8 tarjetas de sabor, CTA final y botón flotante) y en el texto del footer (`+58 412 5863169`).
- **Evidencia:** la propia foto de producto (`assets/fresa.jpg`) muestra impreso `0412-5863169`.
- ⚠️ **Pendiente de confirmación final del dueño** (ver `PENDIENTES.md`).

### 🟠 Estructura / HTML válido

#### Eliminado un `</div>` sobrante
- En la sección "Sobre Nosotros" había un `</div>` de más que dejaba el marcado inválido.
- **Después:** etiquetas balanceadas — 69 `<div>` abren / 69 cierran; 5 `<section>` correctas.

### 🟢 Conversión / UX

#### Nueva sección "Cómo Pedir" (`id="como-pedir"`)
- Tres pasos: **1)** Elige tu sabor · **2)** Escríbenos por WhatsApp · **3)** Recibe y disfruta.
- El botón "Cómo Pedir" del hero ahora apunta a `#como-pedir` (antes iba a `#pedidos`, que era solo un banner y no explicaba el proceso).

#### Botón flotante de WhatsApp (`.wa-float`)
- Círculo verde fijo abajo a la derecha, **siempre visible**.
- Resuelve que en móvil el botón "Pedir Ahora" del header desaparecía.

### 🔍 SEO / compartir en redes

Añadido al `<head>`:
- **Favicon** de marca: `assets/favicon.png` (corazón rosa) + `theme-color` `#ef5c89`.
- **Open Graph** (`og:type`, `og:title`, `og:description`, `og:image`, `og:locale`) para que el enlace se vea con imagen y descripción al compartirlo en WhatsApp/Instagram/Facebook.
- **Twitter Card** `summary_large_image`.
- **Canonical** (con dominio de marcador `TU-DOMINIO.com` — reemplazar por el real).

### 🔧 Mantenimiento

#### Año del footer automático
- Antes decía "© 2024" fijo. Ahora usa `<span id="year">` y un pequeño script (`new Date().getFullYear()`) que lo actualiza solo cada año.

### ♿ Accesibilidad

- **Enlace "Saltar al contenido"** (`.skip-link`) + `tabindex="-1"` en `<main>`.
- **Foco visible** por teclado: contorno rosa en `a` y `button` mediante `:focus-visible`.
- **24 íconos SVG decorativos** marcados con `aria-hidden="true"` para que los lectores de pantalla no los anuncien.
- Corregido un comentario engañoso en el código (`<!-- Leaf Icon -->` → `<!-- Icono: ingredientes de calidad -->`).

### ⚡ Rendimiento / imágenes

| Archivo | Antes | Después | Cómo |
|---------|-------|---------|------|
| `assets/logo.png` | 356 KB | **17 KB** | Redimensionado a 560 px + paleta cuantizada |
| `assets/oreo-cutout.webp` | 747 KB (PNG) | **114 KB** | Convertido a WebP (640 px, q82) |

- Se añadieron atributos `width`/`height` al logo (header y footer), a la imagen del hero (`fresa.jpg`, con `fetchpriority="high"`) y a la imagen del CTA, para **evitar saltos de maquetación** (CLS) al cargar.
- La imagen del CTA ahora usa `assets/oreo-cutout.webp` con `loading="lazy"`.
- **Respaldos:** las imágenes originales sin optimizar se guardaron en `assets/original/`.

> Nota: `assets/oreo-cutout.png` (versión redimensionada a 496 KB) quedó en el repo pero **ya no lo usa la página** (se usa el `.webp`). Puede borrarse si se desea.

---

### Archivos nuevos

- `assets/favicon.png` — favicon con forma de corazón.
- `assets/oreo-cutout.webp` — imagen del CTA optimizada.
- `assets/original/` — respaldo de imágenes originales.
- `.gitignore` — excluye los `.zip` distribuibles del control de versiones.
- `docs/CHANGELOG.md` y `docs/PENDIENTES.md` — esta documentación.

### CSS nuevo en `index.html`

`.skip-link`, reglas `:focus-visible`, `.steps` / `.step` / `.step-num`, y `.wa-float`.

---

## Cómo previsualizar el sitio

Abre `index.html` directamente en el navegador (doble clic) — las imágenes cargan por rutas relativas.
Para servirlo por HTTP local:

```bash
python -m http.server 8765
```

Luego abre `http://localhost:8765/index.html`.
