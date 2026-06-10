# АУДИТ 04 — чистота репозитория (ПРЕДЛОЖЕНИЕ, не исполнение)

Генератор: scripts/audit/a04_cleanup.py, 2026-06-10. Критерий «жив»: упомянут в КАНОНИЧЕСКИХ доках (CLAUDE.md, README, RUNBOOK) ИЛИ на него ссылается код (скрипты/тесты/экспорт 90). Упоминание только в brief/чеклистах = след прошлых раундов, не повод держать в scripts/.

## scripts/*.py: всего 97, КАНОНИЧЕСКИХ 32, кандидатов в attic 65

### ОСТАВИТЬ в scripts/ (канонические)

| скрипт | размер | mtime | в доках | в коде |
|---|---|---|---|---|
| 01_build_article_map.py | 5,047 | 2026-05-20 | да | да |
| 02_fix_internal_links.py | 80,600 | 2026-06-04 | да | да |
| 03_find_external_npa.py | 11,050 | 2026-05-19 |  | да |
| 06_finalize.py | 4,732 | 2026-05-20 |  | да |
| 07_add_subpoint_anchors.py | 11,035 | 2026-05-21 | да | да |
| 08_fix_selfref_subpoints.py | 14,533 | 2026-04-01 |  | да |
| 10_cross_code_refs.py | 19,575 | 2026-05-21 |  | да |
| 11_structure_html.py | 19,994 | 2026-06-08 | да | да |
| 13_cleanup_html.py | 14,801 | 2026-05-20 |  | да |
| 16_apply_targeted_overrides.py | 7,090 | 2026-05-21 |  | да |
| 17_normalize_link_targets.py | 9,073 | 2026-05-25 |  | да |
| 18_strip_links_in_notes.py | 11,892 | 2026-05-25 |  | да |
| 28_fix_link_correctness.py | 13,991 | 2026-06-01 |  | да |
| 29_diff_ready_structured.py | 8,988 | 2026-06-01 | да | да |
| 30_reconcile_ready_safe.py | 11,354 | 2026-06-02 | да | да |
| 31_add_lost_links_structured.py | 5,168 | 2026-06-02 |  | да |
| 43_dobivka_stage1_d.py | 17,839 | 2026-06-02 |  | да |
| 64_final_verify.py | 10,782 | 2026-06-04 |  | да |
| 67_independent_verify.py | 14,461 | 2026-06-08 | да |  |
| 70_anara_flags_driver.py | 22,427 | 2026-06-10 |  | да |
| 70_zhilishniy_deadlinks.py | 4,075 | 2026-06-08 |  | да |
| 71_fullspan_wrap.py | 16,859 | 2026-06-08 |  | да |
| 71_gates.py | 8,081 | 2026-06-10 |  | да |
| 72_external_root_link.py | 10,100 | 2026-06-09 | да | да |
| 73_fullspan_chains.py | 13,946 | 2026-06-09 | да | да |
| 74_code_freshness_check.py | 15,612 | 2026-06-09 | да | да |
| 75_crosscode_verify.py | 8,858 | 2026-06-09 | да | да |
| _offmap.py | 1,590 | 2026-06-08 |  | да |
| audit_links_coverage.py | 30,209 | 2026-06-08 | да | да |
| chunk_npa.py | 40,958 | 2026-06-01 | да |  |
| run_pipeline.py | 6,318 | 2026-05-19 | да | да |
| run_structure_all.py | 2,749 | 2026-05-19 | да |  |

### Кандидаты в scripts/attic/ (git mv, НЕ удалять)

Одноразовые фиксы под конкретный документ/раунд, диагностика, дубли. `git mv` сохраняет историю; ничего не теряется.

| скрипт | размер | mtime | упомянут в истории раундов |
|---|---|---|---|
| 04_validate.py | 7,540 | 2026-03-05 |  |
| 09_fix_uk_specific.py | 12,179 | 2026-05-12 |  |
| 14_sweep_remaining_internal_articles.py | 4,964 | 2026-05-21 |  |
| 15_fix_broken_anchors.py | 8,388 | 2026-05-21 |  |
| 19_fix_bare_article_headings.py | 3,997 | 2026-05-25 | да |
| 20_fix_EKO_003.py | 2,490 | 2026-05-25 |  |
| 21_fix_APPK_001.py | 1,794 | 2026-05-25 |  |
| 22_fix_KOAP.py | 7,711 | 2026-05-26 |  |
| 23_fix_SOC.py | 3,199 | 2026-05-26 |  |
| 24_phase2_trudovoy.py | 25,331 | 2026-05-26 |  |
| 25_phase2_predprinimatel_fix.py | 6,980 | 2026-05-26 |  |
| 26_fix_koap_docx6.py | 12,259 | 2026-05-26 |  |
| 27_verify_koap_docx6.py | 8,178 | 2026-05-26 |  |
| 32_classify_internal_links.py | 11,240 | 2026-06-02 |  |
| 33_verify_internal_max.py | 13,609 | 2026-06-02 |  |
| 34_probe_wrong.py | 4,667 | 2026-06-02 |  |
| 35_find_anchors.py | 4,304 | 2026-06-02 |  |
| 36_inventory_targets.py | 2,083 | 2026-06-02 |  |
| 38_external_audit.py | 13,278 | 2026-06-02 |  |
| 39_external_liveness.py | 4,438 | 2026-06-02 |  |
| 40_gap_breakdown.py | 8,814 | 2026-06-02 |  |
| 42_gkosob_canon_ready.py | 5,944 | 2026-06-02 |  |
| 44_measure_typeB.py | 2,859 | 2026-06-02 |  |
| 45_anara_typeB.py | 5,027 | 2026-06-02 |  |
| 46_anara_typeA_recon.py | 6,745 | 2026-06-02 |  |
| 47_anara_typeA_apply.py | 5,843 | 2026-06-02 |  |
| 48_anara_typeC_recon.py | 2,358 | 2026-06-02 |  |
| 49_anara_gate.py | 2,638 | 2026-06-02 |  |
| 52_divergence_diag.py | 8,568 | 2026-06-02 |  |
| 54_reconcile_ready.py | 6,723 | 2026-06-02 |  |
| 57_multiset_residual.py | 5,304 | 2026-06-02 |  |
| 58_genuine_context.py | 3,466 | 2026-06-02 |  |
| 59_add_genuine_ready.py | 4,573 | 2026-06-02 |  |
| 60_final_gettext_gate.py | 1,866 | 2026-06-02 |  |
| 61_recheck_recon.py | 4,876 | 2026-06-03 |  |
| 62_recheck_apply.py | 7,093 | 2026-06-03 |  |
| 65_grazhdanskiy_diag.py | 7,776 | 2026-06-04 |  |
| 66_grazh_2links_apply.py | 4,229 | 2026-06-04 |  |
| 68_link_canon.py | 13,557 | 2026-06-08 |  |
| 69_sixcheck_laws.py | 6,957 | 2026-06-08 |  |
| 90_build_public_export.py | 7,107 | 2026-06-10 |  |
| _uk_rebuild_map.py | 2,749 | 2026-06-08 |  |
| _upk10_crosscode_verify.py | 5,103 | 2026-06-08 |  |
| _upk2_recon.py | 3,291 | 2026-06-08 |  |
| _upk3_census.py | 3,951 | 2026-06-08 |  |
| _upk6_state.py | 6,585 | 2026-06-08 |  |
| _upk7_mislinks.py | 4,530 | 2026-06-08 |  |
| _upk8_apply_A.py | 5,361 | 2026-06-08 |  |
| _upk9_apply_B.py | 5,987 | 2026-06-08 |  |
| audit_TZ01.py | 7,611 | 2026-05-25 | да |
| audit_TZ02.py | 8,221 | 2026-05-25 |  |
| audit_TZ02_strict.py | 14,176 | 2026-05-25 | да |
| audit_TZ03.py | 6,739 | 2026-05-25 |  |
| audit_uk_skeleton.py | 10,101 | 2026-05-29 |  |
| build_anara_verification.py | 18,925 | 2026-05-29 |  |
| build_examples_md.py | 8,563 | 2026-05-28 |  |
| debug_311.py | 771 | 2026-05-28 |  |
| diag_gap.py | 2,643 | 2026-05-29 |  |
| diag_typeA.py | 1,882 | 2026-05-29 |  |
| diag_typeA2.py | 2,674 | 2026-05-29 |  |
| diag_typeB_frag.py | 2,069 | 2026-05-29 |  |
| reg_11_all.py | 1,315 | 2026-06-08 |  |
| stats_ready.py | 2,776 | 2026-05-12 |  |
| sweep_inventory.py | 12,221 | 2026-05-28 |  |
| verify_hier.py | 5,975 | 2026-05-29 |  |

## Коллизии нумерации и подпапки

- ФАКТ: номер 70 занят ДВАЖДЫ (`70_zhilishniy_deadlinks.py` — разовый фикс, и `70_anara_flags_driver.py` — драйвер флагов УПК-раунда); номер 71 тоже (`71_fullspan_wrap.py` — канонический §7 п.6, и `71_gates.py` — гейты УПК-раунда). Предложение: `70_zhilishniy_deadlinks.py` -> attic (работа сделана), `71_gates.py` -> переименовать в `77_gates.py`, `70_anara_flags_driver.py` -> `76_anara_flags_driver.py` (после «ок»).
- `scripts/debug/` (23 файлов) — целиком кандидат в attic (разовая диагностика).
- `scripts/_upk*.py`, `scripts/_offmap.py`, `scripts/_uk_rebuild_map.py` — подчёркнутые временные скрипты УПК-раунда: в attic после закрытия раунда.
- `law_kit/scripts/` — снапшот пайплайна для передачи (дубль 8 канонических скриптов): оставить как есть (это поставляемый kit, не мусор).

## Корень и data/: лишнее/осиротевшее

- `data/final_backup_*` (16 папок, ~150MB) — уже в .gitignore; на диске оставить до приёмки, потом можно унести в archive/.
- `data/final_pre_links/`, `data/final_pre_fix11_zhilishniy_structured.html` — пре-снапшоты, тот же статус.
- `data/reports/` (старые отчёты раундов, ~9MB) — исторические; трогать не предлагаю (на них ссылаются чеклисты).
- `data/maps/article_map_ugolovniy_rebuilt.json` — рабочая копия рядом с канонической `article_map_ugolovniy.json`: после приёмки УК-раунда слить в одну (вопрос шефу).
- `data/anara_package/`, `data/chunks/`, `data/tree/` — производные артефакты чанкера; перегенерируемы, оставить.
- Корень: `ADILETkz_гиперссылки_2026-06-02.zip` (в .gitignore), `session-export-*.zip` в brief/ — локальные архивы, в репо не идут.

## Что НЕ вошло в публичную ветку (локально, §11)

- 22 скрипта/отчёта с внутренним IP (см. .git/info/exclude),
- 4 source-страницы (grazhdanskiy/nalog/trudovoy/ugolovniy) с IP в href,
- brief/ТЗ-01, brief/HANDOFF, 22 CSV-отчёта с IP,
- anara_review/ (160MB docx, ПДн), archive/ (352MB).

