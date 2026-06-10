# -*- coding: utf-8 -*-
"""Targeted fixes from the reviewer file "КоАП (6).docx".

The edits are intentionally narrow and applied to both final KOAP artifacts.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FILES = [
    ROOT / "data" / "final" / "koap_structured.html",
    ROOT / "data" / "final" / "koap_ready.html",
]

KOAP_DOC = "https://adilet.zan.kz/rus/docs/K1400000235"

EDITS = [
    # Article 40: reviewer expects the highlighted "статьей 59" to open the
    # KOAP NPA on Adilet, not just a local in-page anchor.
    (
        "KOAP6-40-article-59-absolute",
        '<a href="#z59h">статьей 59</a> настоящего Кодекса',
        '<a href="https://adilet.zan.kz/rus/docs/K1400000235#z59h">статьей 59</a> настоящего Кодекса',
    ),
    # Article 62: in koap_ready only the word "Кодексом" was linked; the
    # reviewer highlighted the whole Customs Code title.
    (
        "KOAP6-62-customs-full-title",
        '<a href="https://adilet.zan.kz/rus/docs/K1700000123#z574">Кодексом</a> Республики Казахстан "О таможенном регулировании в Республике Казахстан"',
        '<a href="https://adilet.zan.kz/rus/docs/K1700000123#z574">Кодексом Республики Казахстан "О таможенном регулировании в Республике Казахстан"</a>',
    ),
    (
        "KOAP6-179-rehab-law-docid",
        '<a href="https://adilet.zan.kz/rus/docs/Z2200000178">Законом Республики Казахстан "О реабилитации и банкротстве"</a>',
        '<a href="https://adilet.zan.kz/rus/docs/Z1400000176">Законом Республики Казахстан "О реабилитации и банкротстве"</a>',
    ),
    (
        "KOAP6-211-microfinance-law-docid",
        '<a href="https://adilet.zan.kz/rus/docs/Z2300000094">Законом Республики Казахстан "О микрофинансовой деятельности"</a>',
        '<a href="https://adilet.zan.kz/rus/docs/Z1200000056">Законом Республики Казахстан "О микрофинансовой деятельности"</a>',
    ),
    # Article 732: reviewer highlighted 445-1 and 455.
    (
        "KOAP6-732-445-1-455",
        '<a href="#z1504">445</a>, 445-1, 455 (частью 1-1) и <a href="#z1583">464</a>',
        '<a href="#z1504">445</a>, <a href="#z3405">445-1</a>, <a href="#z1552">455</a> (частью 1-1) и <a href="#z1583">464</a>',
    ),
    # Article 729: ready.html still had the highlighted 138, 637 and 641 as
    # plain text even though structured.html was already fixed.
    (
        "KOAP6-729-138",
        '<a href="#z264">79</a>, 138 (частью второй), <a href="#z472">156</a>',
        '<a href="#z264">79</a>, <a href="#z1742">138</a> (частью второй), <a href="#z472">156</a>',
    ),
    (
        "KOAP6-729-637",
        '<a href="#z1716">505</a>, 637 (частями четырнадцатой и пятнадцатой), <a href="#z640h">640</a>',
        '<a href="#z1716">505</a>, <a href="#z2131">637</a> (частями четырнадцатой и пятнадцатой), <a href="#z640h">640</a>',
    ),
    (
        "KOAP6-729-641",
        '<a href="#z640h">640</a>, 641настоящего Кодекса',
        '<a href="#z640h">640</a>, <a href="#z641h">641</a> настоящего Кодекса',
    ),
    # Article 802: law title after linked articles 13, 14, 15 was still plain text.
    (
        "KOAP6-802-electro-articles",
        'предусмотренном статьями 6-3, 6-4 и 6-5 <a href="https://adilet.zan.kz/rus/docs/Z040000588_">Закона Республики Казахстан "Об электроэнергетике"</a>',
        'предусмотренном статьями <a href="https://adilet.zan.kz/rus/docs/Z040000588_#z1096">6-3</a>, <a href="https://adilet.zan.kz/rus/docs/Z040000588_#z1136">6-4</a> и <a href="https://adilet.zan.kz/rus/docs/Z040000588_#z1241">6-5</a> <a href="https://adilet.zan.kz/rus/docs/Z040000588_">Закона Республики Казахстан "Об электроэнергетике"</a>',
    ),
    (
        "KOAP6-802-heat-13-link-text",
        'и <a href="https://adilet.zan.kz/rus/docs/Z2400000120#z197">статьями 13</a>, <a href="https://adilet.zan.kz/rus/docs/Z2400000120#z237">14</a> и <a href="https://adilet.zan.kz/rus/docs/Z2400000120#z342">15</a>',
        'и статьями <a href="https://adilet.zan.kz/rus/docs/Z2400000120#z197">13</a>, <a href="https://adilet.zan.kz/rus/docs/Z2400000120#z237">14</a> и <a href="https://adilet.zan.kz/rus/docs/Z2400000120#z342">15</a>',
    ),
    (
        "KOAP6-802-heat-law",
        '<a href="https://adilet.zan.kz/rus/docs/Z2400000120#z342">15</a> Закона Республики Казахстан "О теплоэнергетике"',
        '<a href="https://adilet.zan.kz/rus/docs/Z2400000120#z342">15</a> <a href="https://adilet.zan.kz/rus/docs/Z2400000120">Закона Республики Казахстан "О теплоэнергетике"</a>',
    ),
    # Article 804: several authority lists had bare article numbers.
    (
        "KOAP6-804-9-1-462-463",
        '<a href="#z1317">396</a> (часть вторая), <a href="#z1325">398</a>, 462, 463);',
        '<a href="#z1317">396</a> (часть вторая), <a href="#z1325">398</a>, <a href="#z1572">462</a>, <a href="#z1580">463</a>);',
    ),
    (
        "KOAP6-804-37-463",
        '<a href="#z1410">статьи 415</a> (часть вторая), <a href="#z1572">462</a>, 463);',
        '<a href="#z1410">статьи 415</a> (часть вторая), <a href="#z1572">462</a>, <a href="#z1580">463</a>);',
    ),
    (
        "KOAP6-804-45-667",
        '<a href="#z1543">статьи 453</a> (части вторая и третья) (за совершение правонарушений, связанных с государственными секретами), <a href="#z1572">462</a>, <a href="#z1619">477</a>, 667);',
        '<a href="#z1543">статьи 453</a> (части вторая и третья) (за совершение правонарушений, связанных с государственными секретами), <a href="#z1572">462</a>, <a href="#z1619">477</a>, <a href="#z2192">667</a>);',
    ),
    (
        "KOAP6-804-49-127-2",
        '<a href="#z406">127</a>, <a href="#z4047">127-1</a>, 127-2, <a href="#z423">134</a>',
        '<a href="#z406">127</a>, <a href="#z4047">127-1</a>, <a href="#z4814">127-2</a>, <a href="#z423">134</a>',
    ),
    (
        "KOAP6-804-52-424-1",
        '<a href="#z1437">424</a> (части третья и пятая), 424-1 (по нарушению порядка применения новых методов и средств профилактики, диагностики, лечения и медицинской реабилитации)',
        '<a href="#z1437">424</a> (части третья и пятая), <a href="#z4587">424-1</a> (по нарушению порядка применения новых методов и средств профилактики, диагностики, лечения и медицинской реабилитации)',
    ),
    (
        "KOAP6-804-64-462",
        '<a href="#z667">статьи 193</a> (часть третья), 462);',
        '<a href="#z667">статьи 193</a> (часть третья), <a href="#z1572">462</a>);',
    ),
    # Articles 822 and 829-10: the reviewer highlighted the full "Особенной части раздела 2".
    (
        "KOAP6-822-section-2-ready-variant",
        'санкциями норм Особенной части <a href="#z80">раздела 2</a> настоящего Кодекса, конфискуются',
        'санкциями норм <a href="#z242">Особенной части</a> <a href="#z80">раздела 2</a> настоящего Кодекса, конфискуются',
    ),
    (
        "KOAP6-822-section-2",
        '<a href="#z242">Особенной части</a> раздела 2 настоящего Кодекса, конфискуются',
        '<a href="#z242">Особенной части</a> <a href="#z80">раздела 2</a> настоящего Кодекса, конфискуются',
    ),
    (
        "KOAP6-829-10-section-2-ready-variant",
        'статьи Особенной части <a href="#z80">раздела 2</a> настоящего Кодекса, по которой возбуждено',
        'статьи <a href="#z242">Особенной части</a> <a href="#z80">раздела 2</a> настоящего Кодекса, по которой возбуждено',
    ),
    (
        "KOAP6-829-10-section-2",
        '<a href="#z242">Особенной части</a> раздела 2 настоящего Кодекса, по которой возбуждено',
        '<a href="#z242">Особенной части</a> <a href="#z80">раздела 2</a> настоящего Кодекса, по которой возбуждено',
    ),
    (
        "KOAP6-875-constitution-article-52",
        '<a href="https://adilet.zan.kz/rus/docs/K950001000_#z278">пункте 4</a> <a href="#z52h">статьи 52</a>',
        '<a href="https://adilet.zan.kz/rus/docs/K950001000_#z278">пункте 4 статьи 52</a>',
    ),
    (
        "KOAP6-889-article-8-absolute",
        '<a href="#z8h">статьи 8</a> настоящего Кодекса',
        '<a href="https://adilet.zan.kz/rus/docs/K1400000235#z8h">статьи 8</a> настоящего Кодекса',
    ),
    (
        "KOAP6-910-1-444-445",
        '<a href="#z1450">427</a> (часть первая), 444 (часть пятая), 445 (части первая, вторая, третья, четвертая, пятая, шестая, 6-1, седьмая, восьмая, девятая, десятая, 10-1 и 10-2), <a href="https://adilet.zan.kz/rus/docs/K1400000235#z3405">445-1</a>',
        '<a href="#z1450">427</a> (часть первая), <a href="https://adilet.zan.kz/rus/docs/K1400000235#z1501">444</a> (часть пятая), <a href="https://adilet.zan.kz/rus/docs/K1400000235#z1504">445</a> (части первая, вторая, третья, четвертая, пятая, шестая, 6-1, седьмая, восьмая, девятая, десятая, 10-1 и 10-2), <a href="https://adilet.zan.kz/rus/docs/K1400000235#z3405">445-1</a>',
    ),
]

SELF_ANCHORS_TO_ABSOLUTE = [
    "z80",
    "z242",
    "z1742",
    "z2131",
    "z641h",
    "z3405",
    "z1552",
    "z1572",
    "z1580",
    "z2192",
    "z4814",
    "z4587",
    "z4536",
    "z1501",
    "z1504",
]

def absolutize_self_links(snippet: str) -> str:
    for anchor in SELF_ANCHORS_TO_ABSOLUTE:
        snippet = snippet.replace(f'href="#{anchor}"', f'href="{KOAP_DOC}#{anchor}"')
    return snippet


def apply_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    report: list[str] = []
    for label, old, new in EDITS:
        count = text.count(old)
        if count >= 1:
            text = text.replace(old, new)
            report.append(f"ok {label} x{count}")
        elif count == 0 and (new in text or absolutize_self_links(new) in text):
            report.append(f"skip {label} already applied")
        else:
            raise RuntimeError(f"{path.name}: {label}: expected 1 match, got {count}")
    for anchor in SELF_ANCHORS_TO_ABSOLUTE:
        old = f'href="#{anchor}"'
        new = f'href="{KOAP_DOC}#{anchor}"'
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            report.append(f"absolute {anchor} x{count}")
    path.write_text(text, encoding="utf-8")
    return report


def main() -> None:
    for path in FILES:
        print(path.relative_to(ROOT))
        for line in apply_file(path):
            print("  " + line)


if __name__ == "__main__":
    main()
