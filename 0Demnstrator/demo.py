"""Anzeigeadapter. Zeitgrenzen kommen ausschließlich aus dem Projektkern.

Reste sind Soll minus gerundete Grenze, gemessen in q. Die Astronomie ist
eine definierte bzw. angenäherte Modellanzeige, keine Naturmessung.
"""
from datetime import datetime, timedelta, timezone
from fractions import Fraction as F
from functools import lru_cache
import random

import config
import zyklus23 as z

STRUCTURE = z.Struktur()
ANCHOR = z.DefinierterAnker(STRUCTURE)
CALENDAR = z.VerteilterKalender(STRUCTURE, ANCHOR, z.JAHRE_HORIZONT)
MOON = z.Mondachse(STRUCTURE)
END_Q = CALENDAR.grenze(CALENDAR.c_max)
EPOCH = datetime(2029, 7, 12, 22, tzinfo=timezone.utc)


def _valid_time(t_q):
    if type(t_q) is not int:
        raise ValueError("Zeit muss eine ganze Zahl in q sein.")
    if not 0 <= t_q < END_Q:
        raise ValueError(f"Außerhalb des Demonstrationsbereichs: 0 bis {END_Q - 1} q ab jj.")


def _valid_group(group):
    if type(group) is not int or group not in config.GROUP_OPTIONS:
        raise ValueError("Die Gruppierung muss 4 oder 6 Karten umfassen.")


def utc_text(t_q, offset_seconds=F(0)):
    """Ganzzahlige Mikrosekunden; keine Float-Rundung großer Datumswerte."""
    us = z.runden((F(t_q) * STRUCTURE.q_s + offset_seconds) * 1_000_000)
    return (EPOCH + timedelta(microseconds=us)).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _residual(x, boundary):
    rho = ANCHOR.soll(x) - boundary
    return {"exact_q": str(rho), "q": float(rho), "seconds": float(rho * STRUCTURE.q_s)}


def _level(key, label, index, lo, hi, t_q):
    return {"key": key, "label": label, "index": index, "start_q": str(lo), "end_q": str(hi),
            "offset_q": str(t_q - lo), "total_q": str(hi - lo), "progress": (t_q - lo) / (hi - lo)}


def state(t_q=0, group=config.DEFAULT_GROUP):
    _valid_time(t_q)
    _valid_group(group)
    s, a, kal = STRUCTURE, ANCHOR, CALENDAR
    k = kal.koordinaten(t_q)
    n = k.karte * s.jahre_pro_karte + k.jahr
    c = kal.zyklus_von(t_q)
    b0, b1 = kal.grenze(c), kal.grenze(c + 1)
    y0, y1 = kal.jahresanfang(n), kal.jahresanfang(n + 1)
    j = k.karte
    gindex, phase = divmod(j, group)
    gy0, gy1 = gindex * group * s.jahre_pro_karte, (gindex + 1) * group * s.jahre_pro_karte
    great_years = s.jahre_pro_karte ** 2
    great_index = n // great_years
    great_y0 = great_index * great_years
    month = None if k.tag == s.monate * s.monatstage else k.tag // s.monatstage
    day = None if month is None else k.tag % s.monatstage
    day_c = (n * s.tage + k.tag) * s.C
    md0 = k.tag if month is None else month * s.monatstage
    md1 = md0 + (1 if month is None else s.monatstage)
    m0, m1 = kal.grenze((n * s.tage + md0) * s.C), kal.grenze((n * s.tage + md1) * s.C)
    zero = k.art == "nd_zyklus"
    tick0 = b0 + (s.N * s.k if zero else k.tick * s.k)
    tick1 = b1 if zero else tick0 + s.k
    levels = [
        _level("great", "Großkarte · 529 Jahre", great_index, kal.jahresanfang(great_y0), kal.jahresanfang(great_y0 + great_years), t_q),
        _level("group", f"Gruppierung · {group} × 23 Jahre", gindex, kal.jahresanfang(gy0), kal.jahresanfang(gy1), t_q),
        _level("chart", "Karte · 23 Jahre", j, kal.jahresanfang(j * s.jahre_pro_karte), kal.jahresanfang((j + 1) * s.jahre_pro_karte), t_q),
        _level("year", "Jahr", k.jahr, y0, y1, t_q),
        _level("month", "Nulltag" if month is None else "Monat · 28 Tage", 0 if month is None else month, m0, m1, t_q),
        _level("day", "Tag", k.tag, kal.grenze(day_c), kal.grenze(day_c + s.C), t_q),
        _level("cycle", "Zyklus · 66 Ticks + Nulldurchgang", k.zyklus, b0, b1, t_q),
        _level("tick", "Nulldurchgang" if zero else "Tick · 23 q", k.index if zero else k.tick, tick0, tick1, t_q),
    ]
    mk = MOON.koordinate(t_q)
    dk = z.drehkoordinate(t_q)
    return {
        "q": str(t_q), "utc": utc_text(t_q), "system_time": utc_text(t_q, z.JULES_S), "coordinate_text": k.text(),
        "calendar": {"chart": k.karte, "year": k.jahr, "year_index": n, "month": month, "day": day,
                     "day_of_year": k.tag, "cycle": k.zyklus, "cycle_index": str(c), "tick": k.tick,
                     "quant": k.quant, "kind": k.art, "countdown": k.index if zero else None},
        "group": {"size": group, "index": gindex, "phase": phase, "start_year": gy0, "end_year": gy1,
                  "start_q": str(kal.jahresanfang(gy0)), "end_q": str(kal.jahresanfang(gy1))},
        "moon": {"lunation": mk.lunation, "cycle": mk.zyklus, "tick": mk.tick, "joe": mk.joe, "quant": mk.q,
                 "phase": mk.phase, "phase_degrees": MOON.elongation_grad(t_q),
                 "mean_period_seconds": float(MOON.lunation_q(MOON._x(t_q)) * s.q_s)},
        "rotation": {"turn": dk.umlauf, "cycle": dk.zyklus, "tick": dk.tick, "quant": dk.quant, "residual": dk.rest},
        "levels": levels,
        "residual": {"cycle": _residual(F(c, kal.Z), b0), "year": _residual(n, y0),
                     "chart": _residual(j * s.jahre_pro_karte, kal.jahresanfang(j * s.jahre_pro_karte))},
        "cycle": {"length_q": str(b1 - b0), "zero_length_q": str(b1 - b0 - s.N * s.k), "is_zero": zero,
                  "offset_q": str(t_q - b0), "next_q": str(b1)},
        "year": {"extra_q": kal.sprung(n), "length_q": str(y1 - y0), "length_seconds": float((y1 - y0) * s.q_s)},
    }


@lru_cache(maxsize=1)
def overview():
    s = STRUCTURE
    targets = [("jj · Ursprung", 0), ("Erster Nulldurchgang", s.N * s.k), ("Jahr 1", CALENDAR.jahresanfang(1)),
               ("Karte 1 · 23 Jahre", CALENDAR.jahresanfang(23)), ("Großkarte 1 · 529 Jahre", CALENDAR.jahresanfang(529)),
               ("Horizontende − 1 q", END_Q - 1)]
    return {"version": config.VERSION,
            "credits": [{"name": "Jörn Christian Anders", "role": "Konzept und Festlegungen"},
                        {"name": "Claude (Anthropic)", "role": "Mathematische Ausarbeitung, Implementierung und Erstprüfung des Ausgangsprojekts"},
                        {"name": "ChatGPT (OpenAI)", "role": "Zusätzliche Prüfung, Korrekturen und Demonstrationspaket"}],
            "epoch_utc": utc_text(0), "q_seconds": {"exact": str(s.q_s), "value": float(s.q_s)},
            "horizon": {"years": CALENDAR.jahre, "end_q": str(END_Q), "end_utc": utc_text(END_Q)},
            "presets": [{"label": label, "q": str(q)} for label, q in targets],
            "math": {"Y": s.jahr_q, "b": ANCHOR.b, "g": ANCHOR.g, "d": ANCHOR.d, "Z": CALENDAR.Z},
            "group_options": list(config.GROUP_OPTIONS), "default_group": config.DEFAULT_GROUP}


@lru_cache(maxsize=96)
def series(mode="year", start=0, count=529):
    if type(start) is not int or type(count) is not int or not 1 <= count <= config.MAX_SERIES_POINTS:
        raise ValueError(f"Punktzahl muss zwischen 1 und {config.MAX_SERIES_POINTS} liegen; Start muss ganzzahlig sein.")
    maxima = {"year": CALENDAR.jahre, "chart": CALENDAR.jahre // STRUCTURE.jahre_pro_karte, "cycle": CALENDAR.c_max}
    if mode not in maxima or start < 0 or start + count - 1 > maxima[mode]:
        raise ValueError("Diagrammbereich liegt außerhalb des gültigen Rasters.")
    points, values = [], []
    for x in range(start, start + count):
        if mode == "cycle":
            target, boundary = F(x, CALENDAR.Z), CALENDAR.grenze(x)
        else:
            target = x if mode == "year" else x * STRUCTURE.jahre_pro_karte
            boundary = CALENDAR.jahresanfang(target)
        rho = ANCHOR.soll(target) - boundary
        values.append(rho)
        points.append({"x": x, "exact_q": str(rho), "q": float(rho), "seconds": float(rho * STRUCTURE.q_s),
                       "extra_q": CALENDAR.sprung(x) if mode == "year" and x < CALENDAR.jahre else None})
    mean = sum(values, F(0)) / count
    return {"mode": mode, "xlabel": {"year": "Jahresanfang n", "chart": "Kartenanfang j", "cycle": "Zyklusgrenze c"}[mode],
            "ylabel": "Rest ρ = Soll − gerundete Grenze [q]", "points": points,
            "summary": {"count": count, "mean_exact_q": str(mean), "mean_q": float(mean),
                        "min_q": float(min(values)), "max_q": float(max(values)), "max_abs_q": float(max(map(abs, values)))}}


def date_state(utc, group=config.DEFAULT_GROUP):
    if not isinstance(utc, str) or not utc.strip():
        raise ValueError("Bitte ein UTC-Datum eingeben.")
    try:
        dt = datetime.fromisoformat(utc.strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = dt.astimezone(timezone.utc) - EPOCH
    except (ValueError, OverflowError) as exc:
        raise ValueError("Ungültiges Datum. Erwartet wird beispielsweise 2029-07-12T22:00:00Z.") from exc
    micros = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    if micros < 0:
        raise ValueError("Das Datum liegt vor jj (12. Juli 2029, 22:00:00 UTC).")
    return state(z.runden(F(micros, 1_000_000) / STRUCTURE.q_s), group)


def jump(t_q, unit, delta, group=config.DEFAULT_GROUP):
    _valid_time(t_q)
    _valid_group(group)
    if type(delta) is not int or not -1000 <= delta <= 1000:
        raise ValueError("Sprungweite muss eine ganze Zahl von −1000 bis +1000 sein.")
    if unit == "quantum":
        dest = t_q + delta
    elif unit == "cycle":
        dest = CALENDAR.grenze(CALENDAR.zyklus_von(t_q) + delta)
    elif unit in ("year", "chart"):
        c = CALENDAR.zyklus_von(t_q)
        n = c // CALENDAR.Z
        ny = n + delta if unit == "year" else (n // STRUCTURE.jahre_pro_karte + delta) * STRUCTURE.jahre_pro_karte
        dest = CALENDAR.jahresanfang(ny)
    else:
        raise ValueError("Unbekannte Sprungeinheit.")
    return state(dest, group)


@lru_cache(maxsize=1)
def checks():
    results = []
    def check(name, fn, detail):
        try:
            good = bool(fn())
            results.append({"name": name, "passed": good, "detail": detail if good else "Sollbedingung nicht erfüllt: " + detail})
        except Exception as exc:
            results.append({"name": name, "passed": False, "detail": f"{type(exc).__name__}: {exc}"})
    s, a, kal = STRUCTURE, ANCHOR, CALENDAR
    check("Exakte Einheit", lambda: s.q_s == F(75, 1012), "q = 75/1012 s")
    check("Ursprung", lambda: kal.koordinaten(0).karte == kal.koordinaten(0).jahr == kal.koordinaten(0).quant == 0, "t=0: Karte/Jahr/q=0")
    check("Nulldurchgang", lambda: kal.koordinaten(1518).art == "nd_zyklus" and kal.koordinaten(1518).index == -1, "t=1518: Nulldurchgang −1")
    check("Nächster Zyklus", lambda: kal.koordinaten(1519).zyklus == 1 and kal.koordinaten(1519).quant == 0, "t=1519: Zyklus1, q0")
    check("Erster Jahresbeginn", lambda: kal.jahresanfang(1) == 425807411, "Jahr1 beginnt bei425807411 q")
    rho = lambda n: a.soll(n) - kal.jahresanfang(n)
    check("529-jährige Jahresrestperiode", lambda: all(rho(n + 529) == rho(n) for n in range(529)), "Alle529 Klassen exakt verglichen")
    check("Mittlerer Jahresrest", lambda: sum((rho(n) for n in range(529)), F(0)) / 529 == F(3, 529), "Mittel exakt3/529 q, nicht null")
    check("23 Kartenrestklassen", lambda: sorted(rho(23 * j) for j in range(23)) == [F(k, 23) for k in range(-11, 12)], "Alle k/23, k=−11..11")
    rng = random.Random(23)
    pts = [0, 1517, 1518, 1519, 425807410, 425807411, END_Q - 1] + [rng.randrange(END_Q) for _ in range(1000)]
    check("Exakter Hin- und Rückweg", lambda: all(kal.zeitpunkt(kal.koordinaten(t)) == t for t in pts), f"{len(pts)} feste und reproduzierbare Zeitpunkte")
    check("Rundungsschranke", lambda: all(abs(a.soll(F(c, kal.Z)) - kal.grenze(c)) <= F(1, 2) for c in [0, 1, 210, 211, kal.c_max]), "Gezielte Zyklusgrenzen innerhalb q/2")
    return {"passed": all(r["passed"] for r in results), "checks": results}

