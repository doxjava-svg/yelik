# Registro de cambios — Yelikshop Landing

Historial de todas las modificaciones hechas al landing page (`index.html`) y a los recursos en `assets/`.

El formato sigue un estilo tipo *Keep a Changelog*. Las fechas están en formato `AAAA-MM-DD`.

---

## [2.1.0] — 2026-08-31

Datos de contacto confirmados contra el **sello de marca** del producto (la etiqueta circular azul que llevan los vasitos).

- **Usuario de Instagram corregido:** `@yelikshop_helados` → **`@yelik_shop`**. El sello es la fuente de verdad; el handle anterior no existía.
- **Enlaces de Instagram reales:** el texto de contacto y el botón social del footer ahora apuntan a `https://www.instagram.com/yelik_shop` (antes `href="#"`), con `target="_blank"` y `rel="noopener"`.
- **Número de WhatsApp validado:** el sello muestra `+58 412 5863169`, lo que **confirma** la corrección `472` → `412` hecha en la v1.0.0.
- Pendiente: el botón de Facebook sigue en `href="#"` a la espera de definir si existe la página.

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
