"""
Скрипт 06: Финализация — добавляет CSS/JS подсветку в готовый HTML

Запускается ПОСЛЕ скриптов 02 и 03.
Добавляет CSS + JS который работает и локально и на проде.

Использование:
  python 06_finalize.py --input data/trudovoy_final.html --output data/trudovoy_ready.html
  python 06_finalize.py --input data/ugolovniy_final.html --output data/ugolovniy_ready.html
"""

import re
import argparse
from bs4 import BeautifulSoup


HIGHLIGHT_CODE = """
<style>
/* Подсветка только нужного фрагмента, а не всего абзаца:
   мягкий приглушенный фон + цветной бордер слева для визуального ориентира. */
.highlight-target {
    background-color: rgba(255,255,140,0.35) !important;
    box-shadow: inset 3px 0 0 #f0b400;
    padding: 2px 4px;
    border-radius: 3px;
    transition: background-color 0.5s ease;
}
</style>
<script>
function highlightTarget(hash) {
    document.querySelectorAll('.highlight-target').forEach(function(el) {
        el.classList.remove('highlight-target');
    });
    if (!hash) hash = window.location.hash.substring(1);
    if (!hash) return;
    var target = document.getElementById(hash) || document.querySelector('a[name="' + hash + '"]');
    if (!target) return;
    var el = target;
    while (el && !['P', 'H3', 'H2', 'DIV', 'ARTICLE', 'BODY'].includes(el.tagName)) {
        el = el.parentElement;
    }
    if (el && el.tagName !== 'BODY' && el.tagName !== 'ARTICLE') {
        el.classList.add('highlight-target');
        el.scrollIntoView({behavior: 'smooth', block: 'center'});
    }
}

// Перехватываем ВСЕ клики по ссылкам с якорями — работает и локально и на проде
document.addEventListener('click', function(e) {
    var a = e.target.closest('a');
    if (!a || !a.href) return;
    
    // Извлекаем якорь из href
    var hashIndex = a.href.indexOf('#');
    if (hashIndex === -1) return;
    var hash = a.href.substring(hashIndex + 1);
    if (!hash) return;
    
    // Проверяем что якорь существует в текущем документе
    var target = document.getElementById(hash) || document.querySelector('a[name="' + hash + '"]');
    if (!target) return;  // якорь не в этом документе — пусть браузер сам обработает
    
    // Якорь найден — перехватываем
    e.preventDefault();
    window.location.hash = hash;
    highlightTarget(hash);
});

window.addEventListener('hashchange', function() { highlightTarget(); });
window.addEventListener('load', function() { highlightTarget(); });
</script>
"""


def main():
    ap = argparse.ArgumentParser(description="Добавляет подсветку в финальный HTML")
    ap.add_argument("--input", required=True, help="HTML файл после скриптов 02/03")
    ap.add_argument("--output", required=True, help="Финальный HTML с подсветкой")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        html = f.read()

    # Убираем старый CSS/JS если есть (от скрипта 02)
    html = re.sub(r'<style>.*?highlight-target.*?</style>', '', html, flags=re.DOTALL)
    html = re.sub(r'<script>.*?highlightTarget.*?</script>', '', html, flags=re.DOTALL)

    # Добавляем id к <a name="zN"> (если скрипт 02 уже сделал — не дублируем)
    soup = BeautifulSoup(html, "html.parser")
    for a_tag in soup.find_all("a", attrs={"name": True}):
        name_val = a_tag["name"]
        if re.match(r'^z\d+', name_val) and not a_tag.get("id"):
            existing = soup.find(id=name_val)
            if not existing:
                a_tag["id"] = name_val
    html = str(soup)

    # Вставляем CSS+JS
    if "<head>" in html:
        html = html.replace("<head>", "<head>" + HIGHLIGHT_CODE, 1)
    elif "<body>" in html:
        html = html.replace("<body>", HIGHLIGHT_CODE + "<body>", 1)
    else:
        html = HIGHLIGHT_CODE + html

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Готово: {args.output}")
    print("Открой в браузере и нажми на любую ссылку — должно прокрутить и подсветить жёлтым.")


if __name__ == "__main__":
    main()