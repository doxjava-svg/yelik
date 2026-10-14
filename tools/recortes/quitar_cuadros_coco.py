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
    "bgcell_tol": 0.0,       # >0: en celdas de fondo solo se borran píxeles a menos de N del color de
                             # la celda (protege producto claro en el margen de la celda; 0 = como antes)
    "line_both_sides": False,  # mezclas junto a las líneas solo son fondo si hay fondo a ambos lados
    "shadow_edge_min": 0.0,  # >0: una zona solo es sombra si en las líneas de la rejilla conserva al
                             # menos esta fracción del salto blanco/gris esperado (0 = como antes)
    "wash_step": 0.0,        # >0: salto mínimo (niveles de gris) en la línea para aceptar una celda
                             # "lavada" como fondo (0 = desactivado, como antes)
    "wash_depth": 3,         # celdas de distancia del fondo donde se buscan celdas lavadas
    "wash_iter": 3,          # pasadas (una celda lavada puede apoyarse en otra ya aceptada)
    "pure_tol": 0.0,         # >0: una celda plana (sd < pure_sd) con el color EXACTO del blanco o del gris del
                             # tablero (a menos de N por canal) pegada al fondo es fondo aunque tenga una sola
                             # vecina de fondo (paridad rota junto al producto). 0 = desactivado
    "pure_sd": 2.0,
    "shadow_blur": 0.0,      # >0: sigma (px) para suavizar la opacidad de la sombra dentro de su zona. Un error de
                             # paridad o una celda lavada deja la sombra "a cuadros"; una sombra real es suave
    "tol_px_top": 0.0,       # >0: tolerancia por píxel por ENCIMA de la línea de sombras (shadow_y_frac). Ahí no
                             # hay sombras de contacto y el plástico de la tapa sobre las celdas grises difiere
                             # del gris en solo ~10-14: una tolerancia menor la protege. 0 = igual a tol_px
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
    cells = np.array(cells, dtype=int)
    N = len(cells)

    lab_img = np.empty((h, w), dtype=np.int32)
    for j, ids in enumerate(band_cells):
        for cid in ids:
            _, x0, x1, y0, y1 = cells[cid]
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
    for j in range(len(band_cells) - 1):
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
                               limit=float(max(P["refine_depth"], P["shadow_depth"])) + 0.5)
    reach = np.isfinite(dist_c)
    dist_i = np.where(reach, dist_c, 1e9).astype(np.int64)
    src_white = np.zeros(N, bool)
    src_white[reach] = is_white[srcs[reach]]
    par_white = np.where(dist_i % 2 == 0, src_white, ~src_white)
    expect_white = np.where(bg_cell, is_white, par_white)
    E_cell = np.where(expect_white[:, None], Wloc, Gloc)
    E_cell = np.where(bg_cell[:, None], cols, E_cell)

    # ---------- 3b) celdas "lavadas" junto al producto ----------
    # El tablero aclarado (tonos intermedios entre blanco y gris, o paridad invertida) no pasa la
    # prueba de vecinas, pero en TODOS sus lados con el fondo hay un salto NÍTIDO justo sobre la
    # línea de la rejilla y la celda es plana a ambos lados del salto. Un producto claro casi nunca
    # tiene bordes rectos que caigan exactamente sobre dos líneas de la rejilla.
    washed = np.zeros(N, bool)
    if P["wash_step"] > 0:
        n_eh = len(eh)
        ext_w = cells[:, 2] - cells[:, 1]
        ext_h = cells[:, 4] - cells[:, 3]
        S = {k: [] for k in ("a1y", "a1x", "b1y", "b1x", "a2y", "a2x", "b2y", "b2x", "e")}
        for e, (a, b) in enumerate(ortho):
            if e < n_eh:   # a a la izquierda de b: línea vertical
                x = int(cells[b, 1])
                lo, hi = max(cells[a, 3], cells[b, 3]) + 3, min(cells[a, 4], cells[b, 4]) - 3
                if hi - lo < 8 or min(ext_w[a], ext_w[b]) < 12 or x - 8 < 0 or x + 7 >= w:
                    continue
                r = np.arange(lo, hi)
                c = lambda v: np.full_like(r, v)
                pts = (r, c(x - 3), r, c(x + 2), r, c(x - 8), r, c(x + 7))
            else:          # a arriba de b: línea horizontal
                y = int(cells[b, 3])
                lo, hi = max(cells[a, 1], cells[b, 1]) + 3, min(cells[a, 2], cells[b, 2]) - 3
                if hi - lo < 8 or min(ext_h[a], ext_h[b]) < 12 or y - 8 < 0 or y + 7 >= h:
                    continue
                r = np.arange(lo, hi)
                c = lambda v: np.full_like(r, v)
                pts = (c(y - 3), r, c(y + 2), r, c(y - 8), r, c(y + 7), r)
            for k, v in zip(("a1y", "a1x", "b1y", "b1x", "a2y", "a2x", "b2y", "b2x"), pts):
                S[k].append(v)
            S["e"].append(np.full(len(r), e))
        ne = len(ortho)
        if S["e"]:
            S = {k: np.concatenate(v) for k, v in S.items()}
            gA1, gB1 = g[S["a1y"], S["a1x"]], g[S["b1y"], S["b1x"]]
            gA2, gB2 = g[S["a2y"], S["a2x"]], g[S["b2y"], S["b2x"]]
            eid = S["e"]
            step = gB1 - gA1
            cE = np.maximum(np.bincount(eid, minlength=ne), 1)
            nE = np.bincount(eid, minlength=ne)
            mstep = np.bincount(eid, weights=step, minlength=ne) / cE
            good = (np.sign(step) == np.sign(mstep[eid])) & (np.abs(step) >= 0.5 * np.abs(mstep[eid]))
            frac = np.bincount(eid, weights=good.astype(float), minlength=ne) / cE
            slA = np.bincount(eid, weights=np.abs(gA1 - gA2), minlength=ne) / cE
            slB = np.bincount(eid, weights=np.abs(gB2 - gB1), minlength=ne) / cE
            am = np.abs(mstep)
            sharp = (nE >= 8) & (am >= P["wash_step"]) & (frac >= 0.85) & \
                    (slA <= 0.35 * am) & (slB <= 0.35 * am)
            dc = np.concatenate([ortho[:, 0], ortho[:, 1]])
            dn = np.concatenate([ortho[:, 1], ortho[:, 0]])
            dsharp = np.concatenate([sharp, sharp])
            elig = U & ~bg_cell & reach & (dist_i <= int(P["wash_depth"]))
            for _ in range(int(P["wash_iter"])):
                known = bg_cell | washed
                kn = known[dn]
                n_known = np.bincount(dc[kn], minlength=N)
                n_sharp = np.bincount(dc[kn & dsharp], minlength=N)
                # todos sus lados con fondo conocido deben ser saltos nítidos (y al menos 2)
                new = elig & ~known & (n_sharp >= 2) & (n_sharp == n_known)
                if not new.any():
                    break
                washed |= new
        E_cell = np.where(washed[:, None], cols, E_cell)
    if P["pure_tol"] > 0:
        # celdas planas con el color exacto del tablero pegadas al fondo: son fondo aunque la prueba de
        # vecinas falle (junto al producto la paridad del tablero puede estar invertida)
        dWc = np.abs(cols - Wcol).max(axis=1)
        dGc = np.abs(cols - Gcol).max(axis=1)
        known = bg_cell | washed
        pure = (cnt >= 12) & ~known & reach & (sd < P["pure_sd"]) & \
               ((dWc < P["pure_tol"]) | (dGc < P["pure_tol"])) & (count(oa, ob, known[ob]) > 0)
        washed |= pure
        E_cell = np.where(pure[:, None], cols, E_cell)
    E = E_cell[lab_img]

    # ---------- 4) refinado por píxel en celdas cercanas al fondo ----------
    bgc_px = (bg_cell | washed)[lab_img]
    refine = (~bg_cell) & (~washed) & reach & (dist_i >= 1) & (dist_i <= int(P["refine_depth"]))
    if washed.any():
        # las celdas pegadas a una lavada también se refinan (con el tono que pide su paridad)
        refine |= (~bg_cell) & (~washed) & reach & (count(oa, ob, washed[ob]) > 0)
    mixed_px = refine[lab_img]
    tol_map = np.full((h, 1), float(P["tol_px"]), np.float32)
    if P["tol_px_top"] > 0:
        # altura del producto aproximada por las filas con celdas que no son fondo
        py = np.where((~bg_cell[lab_img]).any(axis=1))[0]
        if len(py):
            tol_map[:int(py[0] + P["shadow_y_frac"] * (py[-1] - py[0]))] = P["tol_px_top"]
    seg = Wcol - Gcol
    t = np.clip(((img - Gcol) @ seg) / (seg @ seg), 0, 1)
    dseg = np.abs(img - (Gcol + t[..., None] * seg)).max(axis=-1)
    eb = P["edge_band"]
    near_h = (ly < eb) | (ly > wy - eb)      # junto a una línea horizontal
    near_v = (lx < eb) | (lx > wx - eb)      # junto a una línea vertical
    near_line = near_h | near_v
    line_mix = near_line & (dseg < tol_map)
    if P["bgcell_tol"] > 0:
        # en una celda de fondo solo se borra lo que se parece al color de la celda: el producto
        # claro que asoma en su margen (o en la franja de la línea) ya no se pierde con ella
        small_px = (cnt < 12)[lab_img]
        core = bgc_px & ((np.abs(img - cols[lab_img]).max(axis=-1) < P["bgcell_tol"]) | small_px)
    else:
        core = bg_cell[lab_img] | (washed[lab_img] & (np.abs(img - cols[lab_img]).max(axis=-1) < P["tol_px"]))
    strict = mixed_px & (np.abs(img - E).max(axis=-1) < tol_map)
    lzone = (mixed_px | (bgc_px & ~core)) & line_mix
    if P["line_both_sides"]:
        # una mezcla blanco/gris junto a la línea solo es fondo si hay fondo a AMBOS lados de la
        # línea; si no, es producto claro y neutro pegado a la línea (antes se "cortaba" en tiras
        # y los trozos sueltos se borraban como islas)
        base = core | strict
        r = 2 * int(np.ceil(eb)) + 1

        def any_shift(mask, axis, sign):
            acc = np.zeros_like(mask)
            for k in range(1, r + 1):
                acc |= np.roll(mask, sign * k, axis=axis)
            return acc

        ok_h = any_shift(base, 0, 1) & any_shift(base, 0, -1)
        ok_v = any_shift(base, 1, 1) & any_shift(base, 1, -1)
        lzone &= (near_h & ok_h) | (near_v & ok_v)
    bg_px = core
    cand = strict | lzone
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
        if P["shadow_edge_min"] > 0:
            # los trozos de una misma sombra que la franja de una línea separa se unen (si no, cada
            # celda queda sola, de un solo tono, y no pasa la prueba blanco/gris)
            zl, zn = ndimage.label(ndimage.binary_dilation(zone, iterations=2))
            zl = zl * zone
        else:
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
            if P["shadow_edge_min"] > 0:
                # una sombra real deja ver el tablero: en cada línea de la rejilla que cruza hay un
                # salto blanco/gris atenuado por s. Un sombreado del producto (helado o coco claro
                # sobre celdas blancas) "parece sombra" pero no tiene saltos alineados con la rejilla.
                o, q = 3, 2
                p1y, p1x, p2y, p2x = [], [], [], []
                for _, x0, x1, y0, y1 in cells:
                    if x0 >= o and x1 - x0 > 2 * o and y1 - y0 > 2 * o:
                        ys = np.arange(y0 + o, y1 - o)
                        p1y.append(ys); p1x.append(np.full_like(ys, x0 - o))
                        p2y.append(ys); p2x.append(np.full_like(ys, x0 + q))
                    if y0 >= o and y1 - y0 > 2 * o and x1 - x0 > 2 * o:
                        xs = np.arange(x0 + o, x1 - o)
                        p1y.append(np.full_like(xs, y0 - o)); p1x.append(xs)
                        p2y.append(np.full_like(xs, y0 + q)); p2x.append(xs)
                a1 = (np.concatenate(p1y), np.concatenate(p1x))
                a2 = (np.concatenate(p2y), np.concatenate(p2x))
                l1, l2 = zl[a1], zl[a2]
                Eg = E.mean(axis=-1)
                dE = Eg[a2] - Eg[a1]
                v = (l1 == l2) & (l1 > 0) & (np.abs(dE) > 0.5 * contrast_guess)
                sv = 0.5 * (s[a1] + s[a2])
                dobs = g[a2] - g[a1]
                num = np.bincount(l1[v], weights=(dobs * np.sign(dE))[v], minlength=zn + 1)
                den = np.bincount(l1[v], weights=(sv * np.abs(dE))[v], minlength=zn + 1)
                npr = np.bincount(l1[v], minlength=zn + 1)
                ratio = np.where(npr >= 8, num / np.maximum(den, 1e-6), 0.0)[1:]
                # además, cada trozo (zona ∩ celda) debe mostrar él mismo el salto con un trozo vecino:
                # así un pedazo del producto pegado a una sombra real no se cuela en ella. Aquí se
                # mide el tamaño del salto sin signo: tolera parches con la paridad invertida.
                cn, cd = np.abs(dobs)[v], (sv * np.abs(dE))[v]
                keys = np.concatenate([zl[a1][v].astype(np.int64) * N + lab_img[a1][v],
                                       zl[a2][v].astype(np.int64) * N + lab_img[a2][v]])
                uk, inv = np.unique(keys, return_inverse=True)
                pnum = np.bincount(inv, weights=np.concatenate([cn, cn]))
                pden = np.bincount(inv, weights=np.concatenate([cd, cd]))
                pcnt = np.bincount(inv)
                good_keys = uk[(pcnt >= 5) & (pnum / np.maximum(pden, 1e-6) >= P["shadow_edge_min"])]
                piece_ok = (zl > 0) & np.isin(zl.astype(np.int64) * N + lab_img, good_keys)
                # con esta prueba (más fuerte) basta que haya algo de ambos tonos
                okc = touch & (fw > 0.1) & (fw < 0.9) & (sz > 0.5 * cell_area) & (ratio >= P["shadow_edge_min"])
            sh = np.isin(zl, ii[okc])
            if P["shadow_edge_min"] > 0:
                sh &= piece_ok
            n_shadow = int(sh.sum())
            a_sh = np.clip(1.0 - s, 0.0, P["shadow_max_alpha"]).astype(np.float32)
            if P["shadow_blur"] > 0 and sh.any():
                # media ponderada dentro de la zona de sombra: borra el patrón de cuadros residual
                shf = sh.astype(np.float32)
                num_b = ndimage.gaussian_filter(a_sh * shf, P["shadow_blur"])
                den_b = ndimage.gaussian_filter(shf, P["shadow_blur"])
                a_sh = np.where(den_b > 1e-3, num_b / np.maximum(den_b, 1e-3), a_sh).astype(np.float32)
            alpha = np.where(sh, a_sh, alpha).astype(np.float32)
            out_rgb[sh] = P["shadow_color"]
    if internals is not None:
        internals.update(dict(img=img, cells=cells, lab_img=lab_img, bg_cell=bg_cell, checker=checker,
                              U=U, up=up, down=down, same=same, is_white=is_white,
                              expect_white=expect_white, near_bg=near_bg, E_cell=E_cell, cols=cols,
                              sd=sd, chroma=chroma, M=M, bg=bg, alpha=alpha, mixed_px=mixed_px,
                              white_nb=white_nb, gray_nb=gray_nb, oa=oa, ob=ob, washed=washed))
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
