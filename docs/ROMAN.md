# For Roman (morning list)

Short list of things only you can do. Everything else is running or decided.

1. **Basel-Stadt topic gold (2 min, by hand).** data.bs.ch disallows bots on `/api/` and `/explore/dataset/*/download`, so the
   agent will not fetch it. Please download dataset 100086 as CSV from https://data.bs.ch/explore/dataset/100086/ (Export → CSV)
   and save it as `~/Desktop/hackapertus/bern/data/manual/bs_100086.csv`. It becomes the human cantonal gold row in the Prüfstand.

2. **Optional: a higher Public AI rate limit.** The key serves ≈ 100 requests/min across all clients (measured again tonight:
   my jobs together use ≈ 88/min). At that rate the 2025–26 slice (≈ 96k requests: chapter, subtopic, "Digitalisierung")
   finishes around Thu 00:00, evidence quotes by Thu midday, and the since-2015 chapter pass gets ≈ 60–70% done by Sat night.
   The whole back catalogue (325k affairs, chapter step, ≈ 420k requests) would need ≈ 3× the rate. If Public AI raises the
   limit for this key (or you want a dedicated key for the run), say so and put the key at
   `~/.config/hackapertus/publicai.key` (or tell me the path); the run reads a new ceiling from `runs/main/control.json` (`{"max_rate": 4}`) each minute.

3. **Before publishing `upstream/APERTUS-NOTES.md`:** it includes the observation (from `loop/learnings.md`) that a `-70b`
   route given a system message or prefill is answered by Qwen-SEA-LION. `learnings.md` marks disclosing that to Public AI
   as your call; the note is ready either way — remove that line if you prefer to raise it privately first.

4. **GitHub remote + CI (your call: outward-facing).** The repo has no remote yet, so CI (`.github/workflows/ci.yml`: tests, `make run`
   smoke, Docker build, Postgres suite) has never run, and there is no Docker on this Mac. When you are fine with it: create
   the repo (private until you submit is fine), push `main`, and CI runs. `gh` is the quickest:
   `cd ~/Desktop/hackapertus/bern/querschnitt && gh repo create querschnitt --private --source . --push`.
