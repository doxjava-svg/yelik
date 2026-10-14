#!/usr/bin/env python
"""
Quita un fondo de "tablero de cuadros" pintado en los píxeles (la vista previa de
transparencia exportada por error) y exporta un WebP con transparencia real.

Uso:
    python quitar_cuadros.py ENTRADA.png SALIDA.webp [--params '{"tol_px": 14}'] [--debug DIR]

Cómo funciona:
  1) Líneas del tablero. Las filas son líneas rectas de lado a lado con espaciado
     irregular (33-35 px y "costuras" de ~47 px). Las columnas también, pero su
     fase puede cambiar por zonas (mosaicos de tableros "cosidos"), así que se
     detectan por separado en cada franja de fila, como picos del perfil de bordes.
  2) Celdas de fondo. Una celda es fondo si es uniforme, casi neutra y clara, y sus
     vecinas uniformes son TODAS claramente más claras o TODAS más oscuras. Un
     helado blanco no pasa: sus "vecinas" tienen su mismo tono.
  3) Refinado por píxel solo en celdas que tocan el producto, usando el tono que le
     toca a esa celda (opuesto al de sus vecinas de fondo).
  4) Borde suave: se estima la opacidad del borde y se "desmezcla" el color del fondo.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.signal import find_peaks
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

DEFAULTS = {
    "bgish_chroma": 24.0,    # croma máxima de un píxel "tipo fondo" al buscar líneas
    "bgish_min": 150.0,      # brillo mínimo de un píxel "tipo fondo"
    "edge_min_frac": 0.30,   # fuerza mínima de una línea, fracción del contraste blanco-gris
    "margin": 3,             # px ignorados junto a las líneas al medir cada celda
    "std_max": 11.0,         # desviación máxima de gris dentro de una celda de fondo
    "chroma_max": 24.0,      # croma máxima del color medio de una celda de fondo (admite tinte del reflejo)
    "bright_min": 150.0,     # brillo mínimo de una celda de fondo
    "tc_frac": 0.25,         # contraste mínimo con vecinas (fracción de blanco-gris)
    "min_comp": 2,           # tamaño mínimo (celdas) de un grupo de celdas de fondo
    "tol_px": 14.0,          # tolerancia por canal para píxeles de fondo en celdas mixtas
    "refine_depth": 1,       # celdas de distancia del fondo que se refinan por píxel (más = se come las tapas)
    "low_refine_depth": None,  # refine_depth solo en la zona baja (bajo shadow_y_frac: apoyo, sin tapas)
    "bg_keep_chroma": None,  # dentro de celdas de fondo, conservar píxeles con color >= N y lejos del
                             # tono del tablero (bordes claros de palitos/frutas, migas). None = off
    "low_bitone": False,     # en la zona baja, aceptar también el blanco del tablero en celdas que
                             # esperaban gris (parches con la paridad invertida pegados al producto)
    "low_cell_mode": None,   # en la zona baja, aceptar también el tono plano dominante de cada celda
                             # refinada (celdas "lavadas" que no coinciden con el blanco/gris de las
                             # celdas de fondo más cercanas). Valor = tolerancia por canal. None = off
    "shadow_small_cells": None,  # aceptar sombras de un solo tono menores a N celdas. None = off
    "split_cells": False,    # partir celdas de filas-costura (>=1.2x alto típico) donde hay una línea
                             # horizontal local (franjas finas que solo existen en un tramo de la fila)
    "edge_band": 2.5,        # px junto a una línea donde se aceptan mezclas blanco/gris
    "edge_alpha_div": 40.0,  # distancia de color que equivale a opacidad total en el borde
    "island_cells": 4.0,     # islas sueltas con aspecto de fondo menores a N celdas se borran
    "shadow": True,          # convertir la sombra pintada bajo el producto en sombra transparente
    "shadow_depth": 4,       # hasta cuántas celdas del fondo se buscan sombras
    "shadow_y_frac": 0.65,   # solo se buscan sombras por debajo de este % de la altura del producto
    "shadow_s_min": 0.45,    # oscurecimiento máximo aceptado como sombra (s = observado / fondo)
    "shadow_s_max": 0.97,    # oscurecimiento mínimo (más claro = es fondo)
    "shadow_resid": 9.0,     # el píxel debe ser casi exactamente s * fondo (oscurecimiento neutro)
    "shadow_max_alpha": 0.6,
    "shadow_color": [30, 18, 22],
    "bimodal_tol_w": 10.0,   # tolerancia estricta al blanco del tablero (protege pulpa/crema ~240)
    "bimodal_tol_g": 12.0,   # tolerancia estricta al gris del tablero
    "bimodal_max_cells": 150.0,  # tamaño máximo de una isla bimodal que se borra
    "soft_ramp": 0.0,        # matting suave en celdas del borde: distancia al fondo para opacidad total
                             # (0 = desactivado; conviene apagarlo si el producto es casi blanco puro)
    "out_size": 1024,
    "pad": 40,
    "quality": 85,
}


def detect_lines(prof, trust, thr, n, fallback=None):
    """Líneas del tablero a lo largo de un eje: picos del perfil de bordes.

    prof[i] es la fuerza del borde entre los píxeles i e i+1 (una línea en i+1).
    Donde el perfil no es confiable (zona tapada por el producto) se usan las
    líneas de `fallback`; los huecos grandes se completan con el espaciado típico.
    """
    pk, _ = find_peaks(prof, distance=8, height=thr)
    lines = set((pk + 1).tolist())
    if fallback is not None:
        for b in fallback:
            b = int(b)
            if 0 < b < n and not trust[b - 1] and all(abs(b - q) >= 6 for q in lines):
                lines.add(b)
    lines = sorted(lines)
    if len(lines) >= 3:
        sp = float(np.median(np.diff(lines)))
        filled = [lines[0]]
        for b in lines[1:]:
            start = filled[-1]
            gap = b - start
            if gap > 1.6 * sp:
                k = int(round(gap / sp))
                for j in range(1, k):
                    exp = int(round(start + j * gap / k))
                    lo, hi = max(exp - 5, 1), min(exp + 5, n - 1)
                    win = prof[lo - 1:hi - 1]
                    filled.append(lo + int(np.argmax(win)) if win.size and win.max() > 0 else exp)
            filled.append(b)
        lines = sorted(set(filled))
    lines = [b for b in lines if 0 < b < n]
    return np.array([0] + lines + [n], dtype=int)


def edge_profile(d, v, axis, min_count):
    num = (d * v).sum(axis=axis)
    den = v.sum(axis=axis)
    trust = den >= min_count
    return np.where(trust, num / np.maximum(den, 1), 0.0), trust


def process(src, dst, params=None, debug_dir=None, internals=None):
    P = dict(DEFAULTS)
    if params:
        P.update(params)

    img = np.array(Image.open(src).convert("RGB")).astype(np.float32)
    h, w, _ = img.shape
    g = img.mean(axis=2)
    mx = img.max(axis=2)
    mn = img.min(axis=2)
    ok = ((mx - mn) < P["bgish_chroma"]) & (mx > P["bgish_min"])

    # contraste aproximado blanco-gris (franjas del borde de la imagen)
    sl = [np.s_[:40, :], np.s_[-40:, :], np.s_[:, :40], np.s_[:, -40:]]
    vals = np.concatenate([g[s][ok[s]] for s in sl])
    if len(vals) < 1000:
        raise RuntimeError("Los bordes de la imagen no parecen un tablero de cuadros.")
    contrast_guess = float(np.percentile(vals, 85) - np.percentile(vals, 15))
    if contrast_guess < 20:
        raise RuntimeError(f"Contraste del tablero demasiado bajo ({contrast_guess:.1f}).")
    thr = P["edge_min_frac"] * contrast_guess

    # ---------- 1) líneas: filas globales, columnas por franja ----------
    dyy = np.abs(np.diff(g, axis=0))
    vy = ok[1:] & ok[:-1]
    prof_y, trust_y = edge_profile(dyy, vy, 1, 20)
    by = detect_lines(prof_y, trust_y, thr, h)

    dxx = np.abs(np.diff(g, axis=1))
    vx = ok[:, 1:] & ok[:, :-1]
    prof_x, trust_x = edge_profile(dxx, vx, 0, 20)
    bx_global = detect_lines(prof_x, trust_x, thr, w)

    gl = bx_global[1:-1]
    cells = []        # (franja, x0, x1, y0, y1)
    band_cells = []
    for j in range(len(by) - 1):
        y0, y1 = int(by[j]), int(by[j + 1])
        H = y1 - y0
        if H >= 6:
            # líneas híbridas: se parte de las globales y solo se reemplazan donde esta
            # franja muestra con claridad un desfase (mosaicos de tableros cosidos)
            pj, tj = edge_profile(dxx[y0:y1], vx[y0:y1], 0, max(3, 0.5 * H))
            local_pk, _ = find_peaks(pj, distance=8, height=thr)
            local_pk = local_pk + 1
            sp_g = float(np.median(np.diff(gl))) if len(gl) > 2 else 30.0
            far = [int(p) for p in local_pk if len(gl) == 0 or np.abs(gl - p).min() > 4]
            far_arr = np.array(far, dtype=int)
            keep = list(far)
            for b in gl:
                lo, hi = max(b - 4, 1), min(b + 4, w - 1)
                win = pj[lo - 1:hi - 1]
                if win.size and win.max() >= 0.4 * thr:
                    keep.append(lo + int(np.argmax(win)))   # borde presente (aunque sea débil)
                    continue
                # sin borde cerca: solo se descarta si hay un borde fuerte desplazado que la
                # reemplaza (desfase real); si no, se confía en la línea global
                if len(far_arr) and np.any((np.abs(far_arr - b) > 4) & (np.abs(far_arr - b) < 0.6 * sp_g)):
                    continue
                keep.append(int(b))
            keep = sorted(set(keep))
            # evitar líneas casi duplicadas
            merged = []
            for b in keep:
                if merged and b - merged[-1] < 8:
                    continue
                merged.append(b)
            bxj = np.array([0] + [b for b in merged if 0 < b < w] + [w], dtype=int)
        else:
            bxj = bx_global
        ids = []
        for i in range(len(bxj) - 1):
            ids.append(len(cells))
            cells.append((j, int(bxj[i]), int(bxj[i + 1]), y0, y1))
        band_cells.append(ids)
    if P["split_cells"]:
        # la línea de fila puede existir solo en un tramo (mosaicos cosidos): se busca dentro de
        # cada celda alta una línea horizontal con la misma fuerza mínima que las líneas globales;
        # solo se parte si la vecina de la misma franja tiene la línea a la misma altura (±2 px)
        medH = float(np.median([c[4] - c[3] for c in cells]))
        found = []
        for (j, x0, x1, y0, y1) in cells:
            best = None
            if y1 - y0 >= 1.2 * medH and x1 - x0 > 8:
                for yy in range(y0 + 6, y1 - 5):
                    v = vy[yy - 1, x0 + 2:x1 - 2]
                    n = int(v.sum())
                    if n < 0.5 * (x1 - x0 - 4):
                        continue
                    sv = float((dyy[yy - 1, x0 + 2:x1 - 2] * v).sum()) / n
                    if best is None or sv > best[1]:
                        best = (yy, sv)
            found.append(best[0] if best is not None and best[1] >= thr else None)
        split = []
        for k, (j, x0, x1, y0, y1) in enumerate(cells):
            ys = found[k]
            ok_nb = ys is not None and any(
                0 <= q < len(cells) and cells[q][0] == j and found[q] is not None and abs(found[q] - ys) <= 2
                for q in (k - 1, k + 1))
            if ok_nb:
                split += [(j, x0, x1, y0, ys), (j, x0, x1, ys, y1)]
            else:
                split.append((j, x0, x1, y0, y1))
        cells = split
    cells = np.array(cells, dtype=int)
    N = len(cells)

    lab_img = np.empty((h, w), dtype=np.int32)
    for cid, (_, x0, x1, y0, y1) in enumerate(cells):
        lab_img[y0:y1, x0:x1] = cid
    X = np.arange(w, dtype=np.int32)[None, :]
    Y = np.arange(h, dtype=np.int32)[:, None]
    lx = X - cells[:, 1][lab_img]
    wx = (cells[:, 2] - cells[:, 1])[lab_img]
    ly = Y - cells[:, 3][lab_img]
    wy = (cells[:, 4] - cells[:, 3])[lab_img]
    m = P["margin"]
    inner = (lx >= m) & (lx < wx - m) & (ly >= m) & (ly < wy - m)

    # ---------- 2) estadísticas por celda ----------
    labels = np.where(inner, lab_img + 1, 0)
    idx = np.arange(1, N + 1)
    cnt = ndimage.sum_labels(np.ones_like(g), labels, idx)
    cols = np.stack([np.nan_to_num(ndimage.mean(img[..., c], labels, idx)) for c in range(3)], axis=-1)
    sd = np.nan_to_num(ndimage.standard_deviation(g, labels, idx))
    M = cols.mean(axis=1)
    chroma = cols.max(axis=1) - cols.min(axis=1)
    U = (cnt >= 12) & (sd < P["std_max"]) & (chroma < P["chroma_max"]) & (M > P["bright_min"])

    # ---------- vecindad entre celdas (rejilla irregular) ----------
    eh = [(a, b) for ids in band_cells for a, b in zip(ids[:-1], ids[1:])]
    ev = []
    for j in range(len(band_cells) - 1 if not P["split_cells"] else 0):
        A, B = band_cells[j], band_cells[j + 1]
        p = q = 0
        while p < len(A) and q < len(B):
            a, b = A[p], B[q]
            ax0, ax1 = cells[a, 1], cells[a, 2]
            bx0, bx1 = cells[b, 1], cells[b, 2]
            ov = min(ax1, bx1) - max(ax0, bx0)
            if ov >= 0.6 * min(ax1 - ax0, bx1 - bx0):
                ev.append((a, b))
            if ax1 <= bx1:
                p += 1
            else:
                q += 1
    if P["split_cells"]:
        # con celdas partidas la vecindad se lee de la imagen de etiquetas: dos celdas son
        # vecinas si comparten al menos el 60% del lado más corto (mismo criterio que antes)
        def shared(a, b):
            k = a != b
            pr, ln = np.unique(np.stack([a[k], b[k]], axis=1), axis=0, return_counts=True)
            return pr, ln
        pr, ln = shared(lab_img[:, :-1].ravel(), lab_img[:, 1:].ravel())
        hh = cells[:, 4] - cells[:, 3]
        okh = ln >= 0.6 * np.minimum(hh[pr[:, 0]], hh[pr[:, 1]])
        eh = [tuple(map(int, t)) for t in pr[okh]]
        pr, ln = shared(lab_img[:-1, :].ravel(), lab_img[1:, :].ravel())
        ww = cells[:, 2] - cells[:, 1]
        okv = ln >= 0.6 * np.minimum(ww[pr[:, 0]], ww[pr[:, 1]])
        ev = [tuple(map(int, t)) for t in pr[okv]]
    ortho = np.array(eh + ev, dtype=int).reshape(-1, 2)
    hn = [[] for _ in range(N)]
    for a, b in eh:
        hn[a].append(b)
        hn[b].append(a)
    dg = set()
    for a, b in ev:
        for a2 in hn[a]:
            dg.add((min(a2, b), max(a2, b)))
        for b2 in hn[b]:
            dg.add((min(a, b2), max(a, b2)))
    diag = np.array(sorted(dg), dtype=int).reshape(-1, 2)
    oa = np.concatenate([ortho[:, 0], ortho[:, 1]])   # aristas dirigidas
    ob = np.concatenate([ortho[:, 1], ortho[:, 0]])
    da = np.concatenate([diag[:, 0], diag[:, 1]])
    db = np.concatenate([diag[:, 1], diag[:, 0]])

    def count(src_a, src_b, cond):
        c = np.zeros(N, int)
        np.add.at(c, src_a, cond.astype(int))
        return c

    tc = P["tc_frac"] * contrast_guess
    dlt = M[ob] - M[oa]
    nbU = U[ob]
    up = count(oa, ob, nbU & (dlt > tc))
    down = count(oa, ob, nbU & (dlt < -tc))
    same = count(oa, ob, nbU & (np.abs(dlt) <= 0.5 * tc))
    # en las costuras (celdas angostas) el tablero no alterna: se toleran vecinas de igual tono
    cw = cells[:, 2] - cells[:, 1]
    ch = cells[:, 4] - cells[:, 3]
    narrow = (cw < 0.7 * np.median(cw)) | (ch < 0.7 * np.median(ch))
    checker = U & (((up >= 2) & (down == 0)) | ((down >= 2) & (up == 0))) & ((same == 0) | (narrow & (same <= 2)))
    is_white = down > up

    sel = checker[oa] & checker[ob]
    graph = coo_matrix((np.ones(sel.sum()), (oa[sel], ob[sel])), shape=(N, N))
    ncomp, comp = connected_components(graph, directed=False)
    comp_size = np.bincount(comp, minlength=ncomp)
    bg_cell = checker & (comp_size[comp] >= P["min_comp"])

    def any_nb(flag):
        return (count(oa, ob, flag[ob]) + count(da, db, flag[db])) > 0

    # celdas del borde de la imagen demasiado chicas para medir
    on_border = (cells[:, 1] == 0) | (cells[:, 2] == w) | (cells[:, 3] == 0) | (cells[:, 4] == h)
    tiny = (cnt < 12) & on_border & any_nb(bg_cell) & (chroma < P["chroma_max"]) & (M > P["bright_min"])
    bg_cell = bg_cell | tiny
    near_bg = any_nb(bg_cell)

    # ---------- 3) color esperado del fondo ----------
    Wsel = bg_cell & is_white & ~tiny
    Gsel = bg_cell & ~is_white & ~tiny
    if Wsel.sum() < 5 or Gsel.sum() < 5:
        raise RuntimeError("No se pudieron identificar celdas blancas y grises del tablero.")
    Wcol = np.median(cols[Wsel], axis=0)
    Gcol = np.median(cols[Gsel], axis=0)
    centers = np.stack([(cells[:, 1] + cells[:, 2]) / 2, (cells[:, 3] + cells[:, 4]) / 2], axis=1)
    iw = np.where(Wsel)[0]
    ig = np.where(Gsel)[0]
    _, nw = cKDTree(centers[iw]).query(centers)
    _, ng = cKDTree(centers[ig]).query(centers)
    Wloc = cols[iw[nw]]
    Gloc = cols[ig[ng]]

    white_nb = count(oa, ob, Wsel[ob])
    gray_nb = count(oa, ob, Gsel[ob])
    # tono esperado por paridad: BFS desde las celdas de fondo; cada paso alterna el tono
    src_ids = np.where(Wsel | Gsel)[0]
    graph_all = coo_matrix((np.ones(len(oa)), (oa, ob)), shape=(N, N)).tocsr()
    dist_c, _, srcs = dijkstra(graph_all, directed=False, unweighted=True, indices=src_ids,
                               min_only=True, return_predecessors=True,
                               limit=float(max(P["refine_depth"], P["shadow_depth"],
                                               P["low_refine_depth"] or 0)) + 0.5)
    reach = np.isfinite(dist_c)
    dist_i = np.where(reach, dist_c, 1e9).astype(np.int64)
    src_white = np.zeros(N, bool)
    src_white[reach] = is_white[srcs[reach]]
    par_white = np.where(dist_i % 2 == 0, src_white, ~src_white)
    expect_white = np.where(bg_cell, is_white, par_white)
    E_cell = np.where(expect_white[:, None], Wloc, Gloc)
    E_cell = np.where(bg_cell[:, None], cols, E_cell)
    E = E_cell[lab_img]

    # ---------- 4) refinado por píxel en celdas cercanas al fondo ----------
    bg_px = bg_cell[lab_img]
    if P["bg_keep_chroma"] is not None:
        keep = bg_px & ((mx - mn) >= P["bg_keep_chroma"]) & (np.abs(img - E).max(axis=-1) >= P["tol_px"])
        bg_px &= ~keep
    depth_c = np.full(N, int(P["refine_depth"]))
    if P["low_refine_depth"] is not None:
        # zona baja = bajo shadow_y_frac de la altura del producto; el producto se reconoce por
        # sus píxeles con color u oscuros (el tablero, aun lavado, es neutro y claro)
        prod = ((mx - mn) >= P["chroma_max"]) | (g < P["bright_min"])
        rows = np.where(prod.sum(axis=1) >= 20)[0]
        if len(rows):
            y_low = rows[0] + P["shadow_y_frac"] * (rows[-1] - rows[0])
            depth_c[centers[:, 1] >= y_low] = int(P["low_refine_depth"])
    refine = (~bg_cell) & reach & (dist_i >= 1) & (dist_i <= depth_c)
    mixed_px = refine[lab_img]
    cand = mixed_px & (np.abs(img - E).max(axis=-1) < P["tol_px"])
    if P["low_bitone"]:
        prod = ((mx - mn) >= P["chroma_max"]) | (g < P["bright_min"])
        rows = np.where(prod.sum(axis=1) >= 20)[0]
        if len(rows):
            y_low = int(rows[0] + P["shadow_y_frac"] * (rows[-1] - rows[0]))
            # solo blanco donde se esperaba gris: un gris donde se esperaba blanco puede ser la
            # sombra pintada (la resuelve el paso de sombras)
            lab_low = lab_img[y_low:]
            alt = (~expect_white[lab_low]) & (np.abs(img[y_low:] - Wloc[lab_low]).max(axis=-1) < P["tol_px"])
            cand[y_low:] |= mixed_px[y_low:] & alt
    if P["low_cell_mode"] is not None:
        prod = ((mx - mn) >= P["chroma_max"]) | (g < P["bright_min"])
        rows = np.where(prod.sum(axis=1) >= 20)[0]
        if len(rows):
            y_low = rows[0] + P["shadow_y_frac"] * (rows[-1] - rows[0])
            neutral = (mx - mn) < 12
            lo_t, hi_t = float(Gcol.mean()) - 10, float(Wcol.mean()) + 2
            for i in np.where(refine & (centers[:, 1] >= y_low))[0]:
                _, x0, x1, y0, y1 = cells[i]
                inn = inner[y0:y1, x0:x1]
                area = int(inn.sum())
                if area < 12:
                    continue
                gg = g[y0:y1, x0:x1]
                nm = neutral[y0:y1, x0:x1] & inn
                if nm.sum() < 0.2 * area:
                    continue
                hist = np.bincount(np.clip(gg[nm], 0, 255).astype(int), minlength=256)
                c = int(np.argmax(np.convolve(hist, np.ones(9), "same")))
                band = nm & (np.abs(gg - c) <= 4)
                # tono plano (>=20% de la celda dentro de +-4) y dentro del rango del tablero
                if not (lo_t <= c <= hi_t) or band.sum() < 0.2 * area:
                    continue
                sub = img[y0:y1, x0:x1]
                C = np.median(sub[band], axis=0)
                cand[y0:y1, x0:x1] |= neutral[y0:y1, x0:x1] & (np.abs(sub - C).max(axis=-1) < P["low_cell_mode"])
    seg = Wcol - Gcol
    t = np.clip(((img - Gcol) @ seg) / (seg @ seg), 0, 1)
    dseg = np.abs(img - (Gcol + t[..., None] * seg)).max(axis=-1)
    eb = P["edge_band"]
    near_line = (lx < eb) | (lx > wx - eb) | (ly < eb) | (ly > wy - eb)
    cand |= mixed_px & near_line & (dseg < P["tol_px"])
    plab, _ = ndimage.label(bg_px | cand)
    touching = np.unique(plab[bg_px])
    bg = np.isin(plab, touching[touching > 0])

    # islas sueltas con aspecto de fondo (celdas lavadas o con tinte): se borran
    flab, fn = ndimage.label(~bg)
    if fn > 1:
        cell_area = float(np.median(cells[:, 2] - cells[:, 1])) ** 2
        ii = np.arange(1, fn + 1)
        fs = ndimage.sum_labels(np.ones_like(flab), flab, ii)
        fch = ndimage.mean(mx - mn, flab, ii)
        fbr = ndimage.mean(g, flab, ii)
        drop = (fs < P["island_cells"] * cell_area) & (fch < P["chroma_max"]) & (fbr > P["bright_min"])
        # islas "bimodales": mezcla de píxeles exactamente blancos y exactamente grises del
        # tablero = restos de cuadros (parches de paridad invertida, costuras), de cualquier tamaño
        is_w = (np.abs(img - Wcol).max(axis=-1) < P["bimodal_tol_w"]).astype(np.float32)
        is_g = (np.abs(img - Gcol).max(axis=-1) < P["bimodal_tol_g"]).astype(np.float32)
        fw = ndimage.mean(is_w, flab, ii)
        fgr = ndimage.mean(is_g, flab, ii)
        bimodal = (fw >= 0.2) & (fgr >= 0.2) & (fs < P["bimodal_max_cells"] * cell_area)
        drop |= bimodal
        bg |= np.isin(flab, ii[drop])
    fg = ~bg

    # ---------- 5) alfa con borde desmezclado ----------
    dist = ndimage.distance_transform_edt(fg)
    alpha = np.where(bg, 0.0, 1.0).astype(np.float32)
    edge = fg & (dist <= 1.5)
    dcol = np.sqrt(((img - E) ** 2).sum(axis=-1))
    alpha[edge] = np.clip(dcol[edge] / P["edge_alpha_div"], 0.15, 1.0)
    if P["soft_ramp"] > 0:
        # el fondo de cada píxel es conocido (E): en las celdas que tocan el producto, la
        # opacidad crece con la distancia a ese fondo. Restos lavados -> casi transparentes;
        # plástico de la tapa sobre el tablero -> translúcido.
        dmax = np.abs(img - E).max(axis=-1)
        zone = fg & mixed_px & ((mx - mn) < P["chroma_max"])
        a_soft = np.clip((dmax - P["tol_px"]) / P["soft_ramp"], 0.0, 1.0)
        alpha = np.where(zone, np.minimum(alpha, a_soft), alpha).astype(np.float32)
    a3 = alpha[..., None]
    unmix = (img - (1 - a3) * E) / np.maximum(a3, 1e-3)
    out_rgb = img.copy()
    partial = fg & (alpha < 1.0)
    out_rgb[partial] = np.clip(unmix[partial], 0, 255)

    n_shadow = 0
    if P["shadow"]:
        # sombra pintada sobre el tablero: observado = s * E (oscurecimiento neutro del fondo
        # conocido). Se convierte en sombra real: color oscuro con opacidad 1 - s.
        EE = (E * E).sum(axis=-1)
        s = (img * E).sum(axis=-1) / np.maximum(EE, 1.0)
        resid = np.abs(img - s[..., None] * E).max(axis=-1)
        near = (reach & (dist_i <= int(P["shadow_depth"])))[lab_img]
        # las sombras de contacto están bajo el producto: se ignora la mitad superior
        # (ahí lo que "oscurece" el tablero es el plástico transparente del vaso)
        fy = np.where((alpha > 0.1).any(axis=1))[0]
        low = np.zeros((h, 1), bool)
        if len(fy):
            low[int(fy[0] + P["shadow_y_frac"] * (fy[-1] - fy[0])):] = True
        zone = fg & near & low & (s > P["shadow_s_min"]) & (s < P["shadow_s_max"]) & (resid < P["shadow_resid"])
        zone = ndimage.binary_opening(zone, iterations=1)   # corta uniones finas con el producto
        zl, zn = ndimage.label(zone)
        if zn:
            ii = np.arange(1, zn + 1)
            cell_area = float(np.median(cells[:, 2] - cells[:, 1])) ** 2
            fw = ndimage.mean(expect_white[lab_img].astype(np.float32), zl, ii)
            sz = ndimage.sum_labels(np.ones_like(zl), zl, ii)
            touch = ndimage.maximum(ndimage.binary_dilation(bg, iterations=2).astype(np.uint8), zl, ii) > 0
            # una sombra real cae sobre celdas blancas Y grises; un gris del producto solo
            # "parece sombra" sobre las blancas
            okc = touch & (fw > 0.3) & (fw < 0.7) & (sz > 0.5 * cell_area)
            if P["shadow_small_cells"] is not None:
                # sombras de contacto chicas que caen sobre una sola celda (un solo tono): se
                # aceptan si son pequeñas (las grandes de un solo tono suelen ser producto)
                okc |= touch & (sz > 0.5 * cell_area) & (sz <= P["shadow_small_cells"] * cell_area)
            sh = np.isin(zl, ii[okc])
            n_shadow = int(sh.sum())
            alpha = np.where(sh, np.clip(1.0 - s, 0.0, P["shadow_max_alpha"]), alpha).astype(np.float32)
            out_rgb[sh] = P["shadow_color"]
    if internals is not None:
        internals.update(dict(img=img, cells=cells, lab_img=lab_img, bg_cell=bg_cell, checker=checker,
                              U=U, up=up, down=down, same=same, is_white=is_white,
                              expect_white=expect_white, near_bg=near_bg, E_cell=E_cell, cols=cols,
                              sd=sd, chroma=chroma, M=M, bg=bg, alpha=alpha, mixed_px=mixed_px,
                              white_nb=white_nb, gray_nb=gray_nb, oa=oa, ob=ob))
    rgba = np.dstack([np.clip(out_rgb, 0, 255), alpha * 255]).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")

    # ---------- 6) recorte, cuadrado y exportación ----------
    yy, xx = np.where(alpha > 0.1)
    X0, X1, Y0, Y1 = int(xx.min()), int(xx.max()), int(yy.min()), int(yy.max())
    pad = int(P["pad"])
    out = out.crop((max(0, X0 - pad), max(0, Y0 - pad), min(w, X1 + pad), min(h, Y1 + pad)))
    side = max(out.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(out, ((side - out.width) // 2, (side - out.height) // 2))
    S = int(P["out_size"])
    sq = sq.resize((S, S), Image.LANCZOS)
    sq.save(dst, "WEBP", quality=int(P["quality"]), method=6)

    info = {
        "lines": {"rows": int(len(by) - 2), "cols_global": int(len(bx_global) - 2), "cells": int(N)},
        "white": [round(float(v)) for v in Wcol], "gray": [round(float(v)) for v in Gcol],
        "cells": {"uniform": int(U.sum()), "checker": int(checker.sum()), "bg": int(bg_cell.sum())},
        "bg_fraction": round(float(bg.mean()), 3),
        "shadow_px": n_shadow,
        "bbox": [X0, Y0, X1, Y1],
        "kb": round(os.path.getsize(dst) / 1024),
    }

    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(dst))[0]
        vis = img.astype(np.uint8).copy()
        vis[bg] = [255, 0, 200]
        Image.fromarray(vis).resize((w // 2, h // 2), Image.NEAREST).save(
            os.path.join(debug_dir, base + "_mask.png"))
        for tag, col in (("pink", (252, 232, 239, 255)), ("dark", (40, 40, 48, 255))):
            c = Image.new("RGBA", sq.size, col)
            c.alpha_composite(sq)
            c.convert("RGB").save(os.path.join(debug_dir, f"{base}_on_{tag}.png"))
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--params", default=None, help="JSON con parámetros a sobrescribir")
    ap.add_argument("--debug", default=None, help="carpeta para imágenes de diagnóstico")
    a = ap.parse_args()
    params = json.loads(a.params) if a.params else None
    info = process(a.src, a.dst, params, a.debug)
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
