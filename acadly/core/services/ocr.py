"""Timetable image -> proposed weekly grid.

Pipeline (OpenCV + Tesseract):
  1. detect the ruled lines of the table (morphology),
  2. cut the table into rows (days) and cells, honouring merged cells (labs, breaks),
  3. OCR every cell on its own and fuzzy-match the text to the known subject codes.

The result is only a *proposal*: the user always reviews and edits it before saving.
"""
import difflib
import re

import cv2
import numpy as np
import pytesseract

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]


def _clean(text):
    return re.sub(r"[^A-Za-z ]", "", text).strip().upper()


def _peaks(profile, thresh, gap=8):
    idx = np.where(profile > thresh)[0]
    if len(idx) == 0:
        return []
    groups, cur = [], [idx[0]]
    for i in idx[1:]:
        if i - cur[-1] <= gap:
            cur.append(i)
        else:
            groups.append(cur)
            cur = [i]
    groups.append(cur)
    return [int(np.mean(g)) for g in groups]


def _ocr_cell(gray, psm=7):
    if gray.size == 0:
        return ""
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    gray = cv2.copyMakeBorder(gray, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    txt = pytesseract.image_to_string(bw, config=f"--oem 3 --psm {psm}")
    return " ".join(txt.split())


def match_code(text, aliases):
    """aliases: {'SEPM': 'SEPM', 'DV LAB': 'DV', ...} -> best code or None."""
    t = _clean(text)
    if len(t.replace(" ", "")) < 2:
        return None
    compact = t.replace(" ", "")
    best, best_score = None, 0.0
    for alias, code in aliases.items():
        a = alias.replace(" ", "").upper()
        if a == compact:
            score = 1.0
        elif len(a) >= 4 and a in compact:
            score = 0.9
        elif len(a) < 4:
            # short codes (CN, RM, TOC): only accept when the cell is basically just that code,
            # e.g. "RM[T]" -> "RMT". Stops "PE" matching inside "DEPARTMENT".
            score = 0.9 if compact.startswith(a) and len(compact) <= len(a) + 3 else 0.0
        else:
            score = difflib.SequenceMatcher(None, a, compact).ratio()
        if score > best_score:
            best, best_score = code, score
    return best if best_score >= 0.8 else None


def read_table(path, aliases):
    """Return dict: {'rows': {day: [{'start': col, 'end': col, 'text': str, 'code': str|None}]},
                     'n_columns': int, 'warning': str}"""
    img = cv2.imread(path)
    if img is None:
        raise ValueError("Could not read the image file.")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 25, 10)
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(W // 25, 15), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(H // 45, 15)))
    hor = cv2.dilate(cv2.erode(bw, hk), hk)
    ver = cv2.dilate(cv2.erode(bw, vk), vk)

    ys = _peaks(hor.sum(axis=1) / 255, 0.25 * W)
    # the timetable is the top block; the course list below has other columns
    bands = [(a, b) for a, b in zip(ys, ys[1:]) if b - a > 0.015 * H]
    candidates = []  # (a, b, vertical_edges, detected_day_or_None) in top-to-bottom order
    for a, b in bands:
        edges = _peaks(ver[a:b, :].sum(axis=0) / 255, 0.5 * (b - a))
        if len(edges) < 2:
            continue
        label = _clean(_ocr_cell(gray[a + 3:b - 3, edges[0] + 3:edges[1] - 3])).replace(" ", "")
        day = next((d for d in DAYS if d in label
                    or difflib.SequenceMatcher(None, d, label).ratio() > 0.6), None)
        candidates.append([a, b, edges, day])

    # fill day labels OCR could not read, using the order of the rows
    offsets = [i - DAYS.index(c[3]) for i, c in enumerate(candidates) if c[3]]
    if offsets:
        base = max(set(offsets), key=offsets.count)
        for i, c in enumerate(candidates):
            k = i - base
            if 0 <= k < len(DAYS):
                c[3] = DAYS[k]
            else:
                c[3] = None
    rows = {c[3]: (c[0], c[1], c[2]) for c in candidates if c[3]}
    if len(rows) < 3:
        return {"rows": {}, "n_columns": 0,
                "warning": "Could not detect the day rows. Fill the grid by hand."}
    first_col = min(v[1] for _, _, v in rows.values())

    # column grid: union of vertical edges seen across day rows, snapped together
    all_edges = sorted({x for _, _, v in rows.values() for x in v if x >= first_col - 5})
    cols = []
    for x in all_edges:
        if not cols or x - cols[-1] > 18:
            cols.append(x)
    n_cols = len(cols) - 1

    out = {}
    for day, (a, b, v) in rows.items():
        edges = [x for x in v if x >= first_col - 5]
        snapped = [min(range(len(cols)), key=lambda i: abs(cols[i] - x)) for x in edges]
        cells = []
        for (xa, ia), (xb, ib) in zip(zip(edges, snapped), zip(edges[1:], snapped[1:])):
            if ib <= ia:
                continue
            text = _ocr_cell(gray[a + 4:b - 4, xa + 4:xb - 4], psm=6)
            cells.append({"start": ia, "end": ib - 1, "text": text,
                          "code": match_code(text, aliases)})
        out[day] = cells
    hits = {}
    for cells in out.values():
        for c in cells:
            if c["code"]:
                for i in range(c["start"], c["end"] + 1):
                    hits[i] = hits.get(i, 0) + 1
    breaks = [i for i in range(n_cols) if hits.get(i, 0) <= 1]
    for cells in out.values():
        for c in cells:
            if c["start"] in breaks and c["end"] in breaks:
                c["code"] = None
    return {"rows": out, "n_columns": n_cols, "break_columns": breaks, "warning": ""}
