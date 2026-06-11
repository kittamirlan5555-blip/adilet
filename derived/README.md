# derived/ — производные данные (перегенерируемые)

Руками не править — всё строится из final/ одной командой:

- `chunks/{слаг}.jsonl` + `tree/{слаг}.json` — чанки и деревья
  (`python scripts/pipeline/chunk_npa.py --all`);
- `structured_out/` — jsonl по схеме шефа с hier_id вида `UKCH1R1ST1P1`
  (`python scripts/pipeline/structurize.py --all`; самотесты внутри,
  сводка — structured_out/QUALITY.md; jsonl не в гите — копии chunks/).

Если данные разошлись с final/ — просто перегенерировать; structurize
сам перечанкует слаг, когда чанки старее финала.
