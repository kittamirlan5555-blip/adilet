"""Replays process_text_node on a single text to debug."""
import sys
sys.path.insert(0, "scripts")
import importlib.util
import json

spec = importlib.util.spec_from_file_location("s02", "scripts/02_fix_internal_links.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

with open("data/maps/article_map_socialnyy.json", encoding="utf-8") as f:
    article_map = json.load(f)
with open("data/maps/subpoint_map_socialnyy.json", encoding="utf-8") as f:
    subpoint_map = json.load(f)

text = "Лицам с инвалидностью, указанным в подпунктах 1), 2) и 4) статьи 176 настоящего Кодекса, государственные социальные пособия по инвалидности назначаются в следующих размерах:"

new, changes = mod.process_text_node(
    text, article_map, "K2300000224", "http://test",
    allow_bare_numbers=True,
    subpoint_map=subpoint_map,
)
print("NEW:", new)
print(f"Changes: {len(changes)}")
for c in changes:
    print(" ", c.get("original", "?"), "→", c.get("anchor", "?"))
