#!/usr/bin/env python3
"""Estremi del turno ricavati dalle partite di /tmp/mstate.json.

Serve a non lasciare date di testata scritte a mano: restavano ferme alla giornata
in cui erano state messe e il report ne dichiarava una sbagliata.
"""
import datetime, re

GG = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']
MESI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno',
        'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']


def _punto(w):
    """(ordinamento, sigla giorno, giorno, mese, anno) da '2026-09-19T15:00' o 'sab 19/09 15:00'.

    Due formati perche il cloud legge le date ISO da BetExplorer e la passata locale
    le scrive gia leggibili in dati.json.
    """
    w = str(w or '')
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', w)
    if m:
        a, ms, g = (int(x) for x in m.groups())
        return (a, ms, g), GG[datetime.date(a, ms, g).weekday()], g, ms, a
    m = re.search(r'([a-z]{3})?\s*(\d{1,2})/(\d{2})', w)
    if m:
        g, ms = int(m.group(2)), int(m.group(3))
        return (0, ms, g), (m.group(1) or ''), g, ms, None
    return None


def intervallo(S, anno=False):
    """'ven 18 - dom 20 settembre': dalla prima all'ultima partita del turno."""
    p = sorted(x for x in (_punto(v.get('when')) for v in S.values()) if x)
    if not p:
        return '?'
    (_, g1, d1, m1, a1), (_, g2, d2, m2, a2) = p[0], p[-1]
    coda = f" {MESI[m2-1]}" + (f" {a2 or a1 or datetime.date.today().year}" if anno else '')
    if (d1, m1) == (d2, m2):
        return f"{g1} {d1}{coda}".strip()
    primo = f"{g1} {d1}".strip() + (f" {MESI[m1-1]}" if m1 != m2 else '')
    return f"{primo} – {g2} {d2}{coda}".strip()
