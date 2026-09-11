#!/usr/bin/env python3
"""Avvolge il frammento di genera_html.py in un documento HTML completo per GitHub Pages.
L'Artifact fornisce da solo doctype/head; GitHub Pages no, e serve anche il noindex."""
import sys, re, datetime
frag = open(sys.argv[1]).read()
out  = sys.argv[2]
m = re.search(r'<title>(.*?)</title>', frag)
title = m.group(1) if m else 'Fantacalcio'
frag = re.sub(r'<title>.*?</title>\s*', '', frag, count=1)
doc = f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="Report fantacalcio privato. Pagina non indicizzata.">
<title>{title}</title>
<style>
  html{{color-scheme:light dark}}
  body{{margin:0;font:14px/1.5 system-ui,-apple-system,sans-serif;background:#fff}}
  img{{max-width:100%}}
  [hidden]{{display:none!important}}
</style>
</head>
<body>
{frag}
<!-- generato il {datetime.datetime.now().isoformat(timespec='seconds')} -->
</body>
</html>
"""
open(out, 'w').write(doc)
print(f"scritto {out} ({len(doc)} byte) — titolo: {title}")
