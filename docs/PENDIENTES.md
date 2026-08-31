# Pendientes — Yelikshop Landing

Tareas abiertas que necesitan **datos del dueño** o son mejoras opcionales.
Última actualización: 2026-08-30.

---

## 🔴 Necesita tu confirmación / datos

- [ ] **Confirmar el número de WhatsApp.** Se dejó `0412-5863169` (según la foto de producto). Confirmar que es el correcto.
- [ ] **Precios.** Por indicación del dueño **NO** se muestran precios por ahora. Reactivar si se decide agregarlos a las tarjetas de sabor.
- [ ] **Links reales de Instagram y Facebook.** Hoy los botones del footer apuntan a `#` (no llevan a ningún lado).
- [ ] **Reconciliar el usuario de Instagram.** El footer dice `@yelikshop_helados`, pero la foto de producto muestra `@yelik_shop`. Definir cuál es el correcto y unificarlo.
- [ ] **Dominio real.** Reemplazar `TU-DOMINIO.com` en el `<head>` (etiquetas `canonical` y `og:image`) por el dominio definitivo.
- [ ] **Datos de operación (opcional pero recomendado).** Zona de entrega / retiro, horario y pedido mínimo, para reforzar la sección "Cómo Pedir".

## 🟡 Mejoras opcionales

- [ ] **Auto-alojar las tipografías de Google** dentro de `assets/fonts/` para que la página **no haga peticiones externas** (100% autónoma/offline).
- [ ] **Optimizar los 8 JPG de sabores** (≈67–83 KB c/u) a WebP para bajar aún más el peso total.
- [ ] **Borrar archivos no usados** de `assets/` si se confirma que son basura de trabajo: `ChatGPT Image ....png`, `test_crop.png`, y el `oreo-cutout.png` (496 KB) que ya no referencia la página.
- [ ] **Subir a GitHub** (hacer `push`) si se quiere respaldo remoto o publicar con GitHub Pages.

## 📌 Notas

- El proyecto es **100% local y estático** (HTML/CSS/JS + imágenes). No tiene servidor, base de datos ni repositorio remoto.
- Las únicas peticiones externas al abrir la página son **Google Fonts** y, al hacer clic, los enlaces a **WhatsApp**.
