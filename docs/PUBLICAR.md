# Publicar y actualizar la página

## Enlaces

- **Página en vivo (para el cliente):** https://doxjava-svg.github.io/yelik/
- **Repositorio:** https://github.com/doxjava-svg/yelik (público)
- **Carpeta local:** `C:\Users\d4bic\Documents\yelik`

## Cómo actualizar la página

Haz los cambios en la carpeta local y luego, desde esa carpeta:

```
git add .
git commit -m "Descripción del cambio"
git push
```

GitHub Pages tarda entre 1 y 2 minutos en reflejar el cambio.

## Cómo bajar una copia

- **Desde GitHub:** entra al repositorio, pulsa **Code** y luego **Download ZIP**.
- **Con Git:** `git clone https://github.com/doxjava-svg/yelik.git`

## Notas

- Los archivos `.zip` no se suben al repositorio (están en `.gitignore`).
- Si GitHub CLI pide volver a iniciar sesión: `gh auth login` (o `gh auth refresh -h github.com`).
- La cuenta de GitHub que aloja el repositorio es `doxjava-svg`.
- La carpeta `docs/` también es pública en el repositorio.
