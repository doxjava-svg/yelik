# Pendientes — Yelikshop Landing

Tareas abiertas que necesitan **datos del dueño** o son mejoras opcionales.
Última actualización: 2026-08-30.

---

## ✅ Resueltos

- [x] **Número de WhatsApp confirmado:** `+58 412-5863169` — verificado contra el sello de marca del producto (2026-08-31).
- [x] **Usuario de Instagram confirmado:** `@yelik_shop` — verificado contra el sello de marca. Se descartó `@yelikshop_helados`.
- [x] **Enlace de Instagram** apuntando a `https://www.instagram.com/yelik_shop` (footer: contacto y botón social).
- [x] **Facebook eliminado** del footer (no existe la página) y reemplazado por un botón de **WhatsApp**.

## 🔴 Necesita tu confirmación / datos

- [ ] **Recortes de los 6 sabores restantes** (Ron Pasas, Coco, Fresa, Chocolate, Parchita, Galleta) para completar el catálogo estilo prototipo. **IMPORTANTE al exportar:** descargar el **PNG transparente real**, no la vista previa — si se ve el patrón de cuadritos grises al abrir el archivo, está mal exportado. Los de Oreo y Café se rescataron por software, pero un PNG bien exportado da bordes perfectos (vale la pena re-exportar también el de Oreo, que perdió la cúpula de la tapa).

- [ ] **URL de TikTok.** El ícono ya está en el footer en modo "próximamente" (sin enlace). Cuando exista la cuenta, pasar la URL: en `index.html` hay que cambiar el `<span class="ft-social-soon">` por `<a href="URL" target="_blank" rel="noopener">` y quitar la clase.
- [ ] **Precios.** Por indicación del dueño **NO** se muestran precios por ahora. Reactivar si se decide agregarlos a las tarjetas de sabor.
- [ ] **Dominio real.** Reemplazar `TU-DOMINIO.com` en el `<head>` (etiquetas `canonical` y `og:image`) por el dominio definitivo.
- [ ] **Datos de operación (opcional pero recomendado).** Zona de entrega / retiro, horario y pedido mínimo, para reforzar la sección "Cómo Pedir".

## 🟡 Mejoras opcionales

- [ ] **Auto-alojar las tipografías de Google** dentro de `assets/fonts/` para que la página **no haga peticiones externas** (100% autónoma/offline).
- [ ] **Optimizar los 8 JPG de sabores** (≈67–83 KB c/u) a WebP para bajar aún más el peso total.
- [ ] **Borrar archivos no usados** de `assets/` si se confirma que son basura de trabajo: `ChatGPT Image ....png` (la (2) ya se aprovechó como fuente de `logo-vertical.webp`), `test_crop.png`, `oreo-cutout.png` y `oreo-cutout.webp` (ambos sin uso desde que el CTA muestra el logo vertical).
- [ ] **Subir a GitHub** (hacer `push`) si se quiere respaldo remoto o publicar con GitHub Pages.

## 📌 Notas

- El proyecto es **100% local y estático** (HTML/CSS/JS + imágenes). No tiene servidor, base de datos ni repositorio remoto.
- Las únicas peticiones externas al abrir la página son **Google Fonts** y, al hacer clic, los enlaces a **WhatsApp**.
