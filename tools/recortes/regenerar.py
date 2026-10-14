#!/usr/bin/env python
"""
Regenera los recortes de los vasitos del catálogo a partir de las fotos originales.

Uso (desde la raíz del proyecto):
    python tools/recortes/regenerar.py              # los 8 sabores
    python tools/recortes/regenerar.py fresa coco   # solo algunos
    python tools/recortes/regenerar.py --verificar  # compara contra assets/ sin sobrescribir

Cada sabor tiene su receta en recetas.json: foto de origen, script y parámetros.
Seis sabores usan una variante del script con ajustes propios (sus tableros de
cuadros tenían defectos distintos); Parchita y Café usan tools/quitar_cuadros.py.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RECETAS = json.load(io.open(os.path.join(os.path.dirname(__file__), "recetas.json"), encoding="utf-8"))


def correr(sabor, destino):
    r = RECETAS[sabor]
    cmd = [sys.executable, "-W", "ignore", os.path.join(RAIZ, r["script"]),
           os.path.join(RAIZ, r["fuente"]), destino, "--params", json.dumps(r["params"])]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{sabor}: {(p.stderr or p.stdout)[-400:]}")
    return destino


def mismos_pixeles(a, b):
    import numpy as np
    from PIL import Image
    x = np.array(Image.open(a).convert("RGBA"))
    y = np.array(Image.open(b).convert("RGBA"))
    return x.shape == y.shape and bool((x == y).all())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    verificar = "--verificar" in sys.argv
    sabores = args or list(RECETAS)
    for s in sabores:
        if s not in RECETAS:
            sys.exit(f"Sabor desconocido: {s}. Opciones: {', '.join(RECETAS)}")
    tmp = tempfile.mkdtemp(prefix="recortes_")

    def tarea(s):
        final = os.path.join(RAIZ, RECETAS[s]["salida"])
        destino = os.path.join(tmp, os.path.basename(final)) if verificar else final
        correr(s, destino)
        if verificar:
            return s, "idéntico" if mismos_pixeles(destino, final) else "DISTINTO"
        return s, "generado"

    fallos = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        for s, estado in ex.map(tarea, sabores):
            fallos += estado == "DISTINTO"
            print(f"{s:10} {estado}", flush=True)
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
