#!/usr/bin/env python3
"""Write prompts/: a verbatim copy of src/querschnitt/prompts.py and every prompt the task sends, rendered for one APS item
and one DVS item. No model calls.

    python upstream/eval-task/render_prompts.py

File format: lines starting with '#' are a header (not sent). Then '[user]' and the user message, then
'[assistant prefill]' and the prefill the assistant turn starts with (sent with continue_final_message=true)."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "src"))
import run as T  # noqa: E402
from querschnitt import prompts as P  # noqa: E402

OUT = HERE / "prompts"


def write(name: str, um, note: str):
    u, pre = um
    (OUT / name).write_text(f"# {note}\n# prompt_id {P.pid(u, pre)} = sha256(user + '\\x00' + prefill)[:12]\n"
                            f"[user]\n{u}\n[assistant prefill]\n{pre}\n")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    src = ROOT / "src/querschnitt/prompts.py"
    shutil.copyfile(src, OUT / "prompts.py")
    items = {it["id"]: it for it in T.aps_items()}
    it = items[202727]
    for s, note in (("d0a", "chapter, codes A-Y in identity order (D0 reading a)"),
                    ("d0b", "chapter, S1 code permutation (D0 reading b)"),
                    ("d3m", "chapter with the item's five APS-labelled examples, identity order (D3 reading)")):
        write(f"aps_{s}.txt", T.p_ch(it, s)[0], f"APS item {it['id']} (Curia {it['curia_number']}): {note}")
    # the subtopic prompt for a fixed chapter list (in a run the list follows from the chapter readings)
    write("aps_subtopic.txt", T.p_sub(it, [18, 17, 16])[0],
          f"APS item {it['id']}: subtopics of the top chapters (here chapters 18, 17, 16), top chapter first; last code = none")
    dv = T.dvs_items()[0]
    for o in ("a", "b"):
        write(f"dvs_yesno_{o}.txt", T.p_yn(dv, o)[0],
              f"DVS item {dv['id']} ({dv['body']}): 'Digitalisierung' yes/no, order {o} ({'A = yes' if o == 'a' else 'A = no'})")
    for lang in ("fr", "it"):
        x = dict(dv, lang=lang)
        write(f"yesno_frame_{lang}_a.txt", T.p_yn(x, "a")[0],
              f"the {lang} frame of the same question (affairs in {lang}); title shown as on the DVS item")
    man = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.name != "MANIFEST.json"}
    (OUT / "MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")
    print("\n".join(man))
    return 0


if __name__ == "__main__":
    sys.exit(main())
