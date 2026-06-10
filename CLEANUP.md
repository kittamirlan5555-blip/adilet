# CLEANUP — Большая уборка, Фаза B (2026-06-10)

Принцип: НИЧЕГО не удаляется. Разовые скрипты уходят в `scripts/attic/` через
`git mv` (история сохранена). История Анары (brief/, reports/) не тронута.
Дерево после Фазы A — см. [MOVES.md](MOVES.md).

## scripts/ после уборки

| где | что | статус |
|---|---|---|
| `scripts/paths.py` | единая точка истины по путям | канон |
| `scripts/audit_links_coverage.py` | резолвер-аудит; его импортируют канонические 28/29/30/43 | канон (несущий) |
| `scripts/pipeline/` (24 файла) | шаги построения, вход `pipeline.py` | канон |
| `scripts/audit/` (21 файл) | верификация, гейты раундов, auditlib | канон |
| `scripts/attic/` (65 файлов) | разовые фиксы/диагностика прошлых раундов | заморожено |
| `scripts/attic/debug/` (23 файла) | разовая диагностика | заморожено |

## Что ушло в attic (списком)

Разовые фиксы под документ/раунд: 04_validate, 09_fix_uk_specific,
14_sweep_remaining_internal_articles, 15_fix_broken_anchors,
19_fix_bare_article_headings, 20_fix_EKO_003, 21_fix_APPK_001, 22_fix_KOAP,
23_fix_SOC, 24_phase2_trudovoy, 25_phase2_predprinimatel_fix,
26_fix_koap_docx6, 27_verify_koap_docx6, 42_gkosob_canon_ready,
65_grazhdanskiy_diag, 66_grazh_2links_apply, 70_zhilishniy_deadlinks
(коллизия номера 70 с anara_flags_driver закрыта: тот живёт в audit/).

Диагностика/обмеры раунда ТЗ-01..03 и Анара-раундов: 32–36, 38–40, 44–49, 52,
54, 57–62, audit_TZ01/TZ02/TZ02_strict/TZ03, audit_uk_skeleton,
build_anara_verification, build_examples_md, debug_311, diag_gap, diag_typeA,
diag_typeA2, diag_typeB_frag, sweep_inventory, verify_hier, stats_ready,
reg_11_all, 90_build_public_export.

УПК-раунд (закрыт): _offmap, _uk_rebuild_map, _upk2/3/6/7/8/9/10.

**Правила attic:** скрипты историчны, на новые пути НЕ переводятся, их ROOT и
взаимные импорты (напр. `_upk* → scripts/_offmap.py`) сломаны намеренно.
Понадобился такой скрипт — копируй логику в канон, не реанимируй на месте.

## Диск: легаси data/ и config/

На момент Фазы B каталоги `data/` и `config/` на диске оказались ПУСТЫ
(легаси-бэкапы `data/final_backup_*`, `final_pre_links/` и пр. уже убраны
ранее) — пустые каталоги сняты с диска. Фолбэк в `64_final_verify.py` на
`data/final_backup_ANARA_RECHECK` остаётся: деградирует мягко («нет backup»),
новые бэкапы пишутся в `backups/` (gitignore).

## Техдолг Фазы C (не-шефский) — СДЕЛАНО 2026-06-10

- **Внутренний IP `<внутренний-ip>:9096` (§11 CLAUDE.md) — вычищен из рабочих копий:**
  - `source/{grazhdanskiy,nalog,trudovoy,ugolovniy}.html` — 6227 замен хоста в href
    на `https://adilet.zan.kz`; гейт text-invariance §6.1 PASS по всем 4 (видимый
    текст не изменился — source как сырьё для сверки текста остаётся валидным);
  - дефолты генерации `02/03/08/10/16` (`--base-url`, `BASE_URL`, `BASE`) →
    `https://adilet.zan.kz`;
  - ОСТАВЛЕНО намеренно: `17_normalize_link_targets` (regex нормализации СТАРЫХ
    ссылок — ему литерал нужен), `scripts/attic/` (заморожен), `law_kit/`
    (снапшот, обновить при передаче), исторические отчёты раундов в `reports/`
    и `brief/` (история Анары/раундов, правке не подлежит).
  - IP остаётся в ИСТОРИИ git (репо публичный с момента первого коммита) —
    вычистка рабочих копий снижает площадь, переписывание истории не делаем.
- `maps/article_map_ugolovniy_rebuilt.json` — рабочая копия рядом с канонической;
  слить после приёмки УК-раунда (вопрос шефу — НЕ Фаза C).
- `law_kit/` — поставляемый снапшот пайплайна (дубль 8 канонических скриптов на
  старых путях). Не мусор; обновить при следующей передаче kit'а.

## Известные КРАСНЫЕ корпуса на 2026-06-10 (verify.py --all, пре-существующие)

Уборка их НЕ правила (принятые файлы не трогаем без отдельного решения):

- **71_gates G6 (синхронность ready vs structured), 8 документов:**
  grazhdanskiy_osob=136, grazhdanskiy=77, nalog=11, appk=4, predprinimatel=3,
  koap=2, byudzhet=1, socialnyy=32 расхождений href при одинаковом тексте.
  Инструмент выравнивания существует: 29_diff + 30_reconcile (канон = _structured).
- **74_freshness: ROOT-stale=50** ссылок на подтверждённо протухшие НГР
  (авто-ремап подменой НГР безопасен по §5 — но это правка принятых файлов,
  применять отдельным решением), ART-stale=4 (ручной ре-резолв по §9),
  NEEDS_REVIEW=98 ссылок / 7 строк mapping (ручная сверка на живом adilet).
- **75_crosscode: MISMATCH=1** — grazhdanskiy_osob -> grazhdanskiy#z151h при
  спане «статей 151-152»: диапазон ведёт на якорь первой статьи (возможно,
  сложившийся стиль, а не мислинк) — на ручной разбор.
- В `npa_mapping.json` правка Фазы D: `K080000095_` -> `K2500000171`
  (Бюджетный кодекс, подтверждённый §5 repeal-replace, 2 строки).

## После приёмки (когда-нибудь, не сейчас)

- решить судьбу `*.docx`-потоков (в .gitignore, в репо не попадают);
- декабрь, ежегодно: НГР закона «о республиканском бюджете» (§2.1 CLAUDE.md).
