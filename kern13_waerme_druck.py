#!/usr/bin/env python3
"""kern13_waerme_druck.py - Waerme, Druckausgleich, Pumpen und Verdichter mit demselben linearen Kern.
Braucht kern13.py und kern13_linear.py im selben Ordner.

Waerme      zweite Sorte: N zaehlt die Waermemenge.  Leiten = Sickern, Mitnahme im Strom, Wand mit fester Temperatur.
Druck       p = th * N / V.  Die Streuung th ist beim Gas die Temperatur.  V gehoert zur Lagebeschreibung und ist je Schritt fest.
Bauteile    Speicher (Behaelter, Zylinder), Leitwert (Drossel, Ventil, Rohr), Antrieb (Pumpe als Kraftstrecke oder feste Menge
            je Schritt).  Ventilstellung und Kolbenlage aendern sich nur zwischen zwei Schritten.
Erwaermung  Waermemenge E als eigene Buchung: p = (gamma - 1) E / V, Arbeit der bewegten Flaeche dE = -p dV.

Aufruf: python3 kern13_waerme_druck.py      (alle Pruefungen, etwa zwei Minuten)
"""
import time

import numpy as np

from kern13 import C, OPP, Raum, p_eq, rates
from kern13_linear import GL, e_lin, flip, lauf, row


# ------------------------------------------------------------------ 1  Waermeuebergang an die Wand im laminaren Strom
def nu_soll(pe, n=400):
    """Abklingzahl des Temperaturfelds zwischen zwei Platten fester Temperatur, mit Leitung laengs (unabhaengige Rechnung)."""
    y = (np.arange(n) + 0.5) / n
    A = (np.diag(-2 * np.ones(n)) + np.diag(np.ones(n - 1), 1) + np.diag(np.ones(n - 1), -1)) * n * n
    A[0, 0] = A[-1, -1] = -3.0 * n * n
    u = 6 * y * (1 - y)
    lam = 7.54 / pe
    for _ in range(60):
        mu = np.linalg.eigvals(-(A + lam ** 2 * np.eye(n)) / (pe * u)[:, None])
        lam = mu[(np.abs(mu.imag) < 1e-8) & (mu.real > 0)].real.min()
    return lam * pe


def t_waermeuebergang(H=16, ubar=0.1, pe=40.0):
    L = 30 * H; D = ubar * H / pe; steps = int(3.2 * L / ubar)
    solid = np.zeros((L, H + 2, 1), bool); solid[:, 0] = solid[:, -1] = True
    raum = Raum(solid); n = solid.size
    yj = np.arange(H + 2) - 0.5
    u1 = np.where((yj > 0) & (yj < H), 6 * ubar * yj / H * (1 - yj / H), 0.0)        # gegebene laminare Stroemung
    U = np.zeros((3, L, H + 2, 1)); U[0] = u1[None, :, None]
    P = p_eq(U.reshape(3, -1))
    om_m = 1 / (3 * D + 0.5); om_p = 1 / (0.125 / (3 * D) + 0.5)
    wand = (raum.dir != np.arange(27)[:, None]) & raum.fluid[None, :]                  # Verbindungen, die von der Wand kommen
    ein = np.arange(n).reshape(solid.shape)[0].ravel(); ein = ein[raum.fluid[ein]]     # Einlaufspalte
    g = np.zeros((27, n))
    for _ in range(steps):
        T = g.sum(0); e = T * P
        g = raum.move(g - 0.5 * om_p * (g + g[OPP] - e - e[OPP]) - 0.5 * om_m * (g - g[OPP] - e + e[OPP]), 0.0)
        g[wand] = -g[wand]                                                             # Wand mit fester Temperatur 0
        g[:, ein] = P[:, ein]                                                          # Einlauf mit Temperatur 1
    T = g.sum(0).reshape(L, H + 2)
    Tb = (T * u1).sum(1) / u1.sum()
    um = u1[1:-1].mean()
    sl = slice(12 * H, 25 * H)
    nu = -np.polyfit(np.arange(L)[sl], np.log(Tb[sl]), 1)[0] * um * H ** 2 / D
    row("1 Waermeuebergang im Plattenkanal, %d Bloecke" % H, "Kennzahl 7,541 ohne Leitung laengs; mit ihr hier %.3f" % nu_soll(um * H / D),
        "%.3f (Temperatur faellt laengs auf %.1e)" % (nu, Tb[25 * H]))


def t_abkuehlung(D=0.02):
    """Schicht zwischen zwei Waenden fester Temperatur, ohne Stroemung: Abklingen mit D (pi/H)^2."""
    out = []
    for H in (8, 16, 32):
        solid = np.zeros((1, H + 2, 1), bool); solid[:, 0] = solid[:, -1] = True
        raum = Raum(solid); n = solid.size
        P = p_eq(np.zeros((3, n)))
        om_m = 1 / (3 * D + 0.5); om_p = 1 / (0.125 / (3 * D) + 0.5)
        wand = (raum.dir != np.arange(27)[:, None]) & raum.fluid[None, :]
        g = P * raum.fluid
        t1, t2 = int(1.0 * H * H / D / 9.87), int(3.0 * H * H / D / 9.87)
        rec = {}
        for t in range(t2 + 1):
            T = g.sum(0); e = T * P
            if t in (t1, t2):
                rec[t] = T[1:-1].sum()
            g = raum.move(g - 0.5 * om_p * (g + g[OPP] - e - e[OPP]) - 0.5 * om_m * (g - g[OPP] - e + e[OPP]), 0.0)
            g[wand] = -g[wand]
        out.append("%d Bloecke: %.5f" % (H, np.log(rec[t1] / rec[t2]) / (t2 - t1) / (D * (np.pi / H) ** 2)))
    row("1 Abkuehlen einer Schicht an zwei Waenden", "Abklingzahl / (D pi^2 / H^2) = 1", "; ".join(out))


# ------------------------------------------------------------------ 2  Druckausgleich zweier Behaelter ueber eine Drossel
def t_entspannung(A1=60, A2=60, Lp=20, r=3.0, steps=24000):
    n = A1 + Lp + A2 + 2
    solid = np.zeros((n, 1, 1), bool); solid[0] = solid[-1] = True
    raum = Raum(solid)
    x = np.arange(n)
    rr = np.where((x > A1) & (x <= A1 + Lp), r, 0.0)                                   # Bremszahl nur in der Drossel
    kraft = lambda N, m: -rr * m / (1 + rr / 2)
    om_p, om_m = rates(1 / 6)
    f = e_lin(GL, np.where(x <= A1, 1.2, 1.0) * raum.fluid, np.zeros((3, n)))
    m0 = f.sum(); ts, dn = [], []
    for t in range(steps):
        g, N, j = flip(f, om_p, om_m, kraft)
        f = raum.move(g, 0.0)
        if t % 50 == 0:
            ts.append(t); dn.append(N[1:A1 + 1].mean() - N[A1 + Lp + 1:n - 1].mean())
    ts, dn = np.array(ts), np.array(dn)
    sel = (ts > 8000) & (ts < 22000)
    lam = -np.polyfit(ts[sel], np.log(dn[sel]), 1)[0]
    Dz = (1 / 3) / r
    lo, hi = 1e-6, np.pi / Lp
    for _ in range(200):                                                               # kappa Lp = pi - atan(kappa A1) - atan(kappa A2)
        ka = 0.5 * (lo + hi)
        if ka * Lp < np.pi - np.arctan(ka * A1) - np.arctan(ka * A2):
            lo = ka
        else:
            hi = ka
    row("2 Druckausgleich ueber eine Drossel", "Zeitzahl 1/(D kappa^2) = %.0f Schritte (grob r Lp/(th (1/A1+1/A2)) = %.0f)" % (1 / (Dz * ka ** 2), r * Lp / ((1 / 3) * (1 / A1 + 1 / A2))),
        "%.0f Schritte, rein exponentiell (Streuung %.0e); Partikel %+.0e" % (1 / lam, np.abs(np.log(dn[sel]) - np.polyval(np.polyfit(ts[sel], np.log(dn[sel]), 1), ts[sel])).max(), f.sum() / m0 - 1))


# ------------------------------------------------------------------ 3  Pumpe als Kraftstrecke im geschlossenen Kreis
def t_pumpe(L=120, H=12, Lp=20, x0=20, nu=1 / 6, q=0.004):
    solid = np.zeros((L, H + 2, 1), bool); solid[:, 0] = solid[:, -1] = True
    raum = Raum(solid)
    a = 12 * nu * q / H ** 2 * L / Lp
    av = np.zeros((3, L, H + 2, 1)); av[0, x0:x0 + Lp] = a
    av = av.reshape(3, -1) * raum.fluid
    N, j, st, dm, f = lauf(raum, nu, lambda N, m: N * av, tol=1e-12)
    Nx = N.reshape(L, H + 2)[:, 1:-1].mean(1)
    Q = j[0].reshape(L, H + 2)[:, 1:-1].sum(1)
    G = H * (H * H + 0.5) / (12 * nu)                                                  # Leitwert des Kanals (Summe ueber die Bloecke)
    Qs = a * Nx[x0:x0 + Lp].sum() * G / L
    gef = Q.mean() / G                                                                 # Druckgefaelle im Rohr je Blockkante
    hub = (Nx[x0 + Lp] - Nx[x0 - 1]) / 3                                               # Druck = N/3, erste Bloecke ausserhalb der Pumpe
    rohr = (Nx[70] - Nx[110]) / 3 / 40
    row("3 Pumpe als Kraftstrecke im Kreis", "Strom = Kraft x Leitwert / Laenge; Foerderdruck = Verlust im Rohr",
        "Strom/Soll - 1 = %.0e, laengs gleich auf %.0e; Foerderdruck/Verlust - 1 = %.0e; Gefaelle im Rohr/Soll - 1 = %.0e; Druckhub %.2f %%"
        % (Q.mean() / Qs - 1, np.ptp(Q) / Q.mean(), hub / (gef * (L - Lp - 1)) - 1, rohr / gef - 1, 100 * 3 * hub / Nx.mean()))


# ------------------------------------------------------------------ 4  Druckstoss beim ploetzlichen Absperren
def t_druckstoss(L=400, m0=0.01, T=200):
    solid = np.zeros((L + 2, 1, 1), bool); solid[0] = solid[-1] = True
    raum = Raum(solid)
    fl = raum.fluid.astype(float)
    f = e_lin(GL, fl, np.stack([m0 * fl, 0 * fl, 0 * fl]))
    om_p, om_m = 1 / (0.0005 + 0.5), 1.0
    for _ in range(T):
        g, N, j = flip(f, om_p, om_m)
        f = raum.move(g, 0.0)
    N = f.sum(0); c = np.sqrt(1 / 3)
    xw = L + 0.5 - np.arange(L + 2)                                                    # Abstand von der abgesperrten Wand
    pl = (xw > 2) & (xw < 0.6 * c * T)
    k = np.flatnonzero((N[:-1] < 1 + m0 / (2 * c)) & (N[1:] >= 1 + m0 / (2 * c)) & (xw[:-1] < 1.5 * c * T))[-1]
    xf = xw[k] - (1 + m0 / (2 * c) - N[k]) / (N[k + 1] - N[k])
    row("4 Druckstoss beim Absperren", "Druckanstieg dN = Strom / Laufgeschwindigkeit = %.5f, Front nach %d Schritten bei %.1f" % (m0 / c, T, c * T),
        "dN = %.5f, Strom dahinter %.0e, Front bei %.1f" % (N[pl].mean() - 1, np.abs((C.T @ f)[0][pl]).max(), xf))


# ------------------------------------------------------------------ 5  Kolbenverdichter mit Ventilen (Knoten mit veraenderlichem Raum)
def t_verdichter(th=1 / 3, p1=1 / 3, pi=3.0, Vs=100.0, Vc=10.0, Tc=40000, zyklen=4):
    p2 = pi * p1
    gv = 0.2 * Vc / th                                                                # Leitwert eines offenen Ventils
    Ncyl = p2 * Vc / th
    V = lambda t: Vc + Vs * (1 - np.cos(2 * np.pi * t / Tc)) / 2
    raus = arbeit = 0.0
    for t in range(zyklen * Tc):
        Va, Vb = V(t), V(t + 1)
        p = th * Ncyl / Va                                                             # Lage dieses Schritts: Raum Va, Ventile nach Druck
        ein = gv * (p1 - p) if p < p1 else 0.0
        aus = gv * (p - p2) if p > p2 else 0.0
        Ncyl += ein - aus
        if t >= Tc:
            raus += aus
            arbeit += -th * Ncyl * 2 / (Va + Vb) * (Vb - Va)                           # Arbeit der Kolbenflaeche: -p dV
    raus /= zyklen - 1; arbeit /= zyklen - 1
    soll = p1 * Vs / th * (1 - Vc / Vs * (pi - 1))
    row("5 Kolbenverdichter, Druck 1 zu %.0f, Totraum %.0f %%" % (pi, 100 * Vc / Vs), "Menge je Hub = %.2f (Fuellgrad %.2f); Arbeit = Menge th ln(%.0f) = %.2f" % (soll, 1 - Vc / Vs * (pi - 1), pi, soll * th * np.log(pi)),
        "Menge %.2f, Arbeit %.2f" % (raus, arbeit))


# ------------------------------------------------------------------ 6  Verdichtung mit Erwaermung (Waermemenge als eigene Buchung)
def t_erwaermung(gam=1.4, schritte=400, verh=4.0):
    out = []
    for name, G in (("ohne Waermeabgabe", 0.0), ("mit starker Waermeabgabe an die Wand", 50.0)):
        N, V, E = 1.0, 1.0, 1.0 / (gam - 1)                                            # Druck p = (gam - 1) E / V = 1, Temperatur = (gam - 1) E / N
        Ew = E                                                                         # Waermemenge bei Wandtemperatur
        for k in range(schritte):
            Vn = V * verh ** (-1 / schritte)
            b = (gam - 1) * (Vn - V) / (Vn + V)                                        # Arbeit der bewegten Flaeche, halb vor, halb nach
            E = E * (1 - b) / (1 + b)
            E = (E + G * Ew) / (1 + G)                                                 # Waermeabgabe ~ Temperaturunterschied zur Wand
            V = Vn
        out.append("%s: Druck x %.4f, Temperatur x %.4f" % (name, (gam - 1) * E / V, E / Ew))
    row("6 Verdichtung auf 1/%.0f des Raums" % verh, "ohne Abgabe: Druck x %.4f, Temperatur x %.4f; mit: Druck x %.0f, Temperatur x 1" % (verh ** gam, verh ** (gam - 1), verh), "; ".join(out))


if __name__ == "__main__":
    t0 = time.time()
    print("Pruefung                                   | Soll                                               | Ist")
    import sys
    if "kurz" in sys.argv:
        t_pumpe(); t_abkuehlung(); t_waermeuebergang(8); t_waermeuebergang(16); t_waermeuebergang(24)
    else:
        t_abkuehlung(); t_waermeuebergang(16); t_entspannung(); t_pumpe(); t_druckstoss(); t_verdichter(); t_erwaermung()
    print("\nLaufzeit %.0f s" % (time.time() - t0))
