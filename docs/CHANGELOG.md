# Registro de cambios — Yelikshop Landing

Historial de todas las modificaciones hechas al landing page (`index.html`) y a los recursos en `assets/`.

El formato sigue un estilo tipo *Keep a Changelog*. Las fechas están en formato `AAAA-MM-DD`.

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
