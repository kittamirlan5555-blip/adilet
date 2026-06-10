"""Запускает 11_structure_html.py на всех кодексах и выводит статистику."""
import sys, os, re
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths

# Import functions directly without triggering argparse
import importlib.util
spec = importlib.util.spec_from_file_location(
    's11', str(Path(__file__).resolve().parent / '11_structure_html.py'))
mod = importlib.util.module_from_spec(spec)
# Monkey-patch argv so argparse in __main__ doesn't run
_orig_argv = sys.argv[:]
sys.argv = ['11_structure_html.py', '--input', 'x', '--output', 'x']
try:
    spec.loader.exec_module(mod)
except SystemExit:
    pass
sys.argv = _orig_argv

process_file = mod.process_file
count_stats  = mod.count_stats

codexes = [
    ('nalog_ready.html',          'nalog_structured.html',          'K2500000214', 'НК'),
    ('trudovoy_ready.html',       'trudovoy_structured.html',       'K1500000414', 'ТК'),
    ('grazhdanskiy_ready.html',   'grazhdanskiy_structured.html',   'K940001000_', 'ГК'),
    ('predprinimatel_ready.html', 'predprinimatel_structured.html', 'K1500000375', 'ПК'),
    ('socialnyy_ready.html',      'socialnyy_structured.html',      'K2300000224', 'СК'),
    ('ekologicheskiy_ready.html', 'ekologicheskiy_structured.html', 'K2100000400', 'ЭК'),
    ('zemelnyy_ready.html',       'zemelnyy_structured.html',       'K030000442_', 'ЗК'),
    ('upk_ready.html',            'upk_structured.html',            'K1400000231', 'УПК'),
    ('koap_ready.html',           'koap_structured.html',           'K1400000235', 'КоАП'),
    ('appk_ready.html',           'appk_structured.html',           'K2000000350', 'АППК'),
    ('byudzhet_ready.html',       'byudzhet_structured.html',       'K2500000171', 'БК'),
    ('ugolovniy_ready.html',      'ugolovniy_structured.html',      'K1400000226', 'УК'),
]

print('Структурирование кодексов...')
results = []
for inp, out, doc_id, label in codexes:
    inp_path = str(paths.FINAL / inp)
    out_path = str(paths.FINAL / out)
    if not os.path.exists(inp_path):
        print(f'  {label}: файл не найден ({inp_path})')
        continue
    tree = process_file(inp_path, out_path)
    stats = count_stats(tree)
    stats['label'] = label
    stats['doc_id'] = doc_id
    results.append(stats)

print()
print(f"{'Кодекс':<8} {'Частей':>7} {'Разд':>5} {'Подр':>5} {'Глав':>6} {'Пар':>5} {'Стат':>6}")
print('-' * 47)
for s in results:
    print(f"{s['label']:<8} {s.get('part',0):>7} {s.get('section',0):>5} "
          f"{s.get('subsection',0):>5} {s.get('chapter',0):>6} "
          f"{s.get('paragraph',0):>5} {s.get('article',0):>6}")

print()
print('Готово. Файлы *_structured.html записаны в final/')
