# R1: OpenParlData topic classification (Hack Apertus Bern, 18–19 Oct 2026)

Research date: 13 Oct 2026. The research was read-only. We respected robots.txt, made no calls to `api.openparldata.ch/v1/`, made no `gitlab.com/api` or `/raw` calls, and contacted no one. Every claim carries a URL or a local path. **[guess]** marks an inference.

**Research hygiene.** One robots.txt slip: a sub-agent made a single metadata call to `data.bs.ch/api/explore/v2.1/catalog/datasets/100086` before reading that host's robots.txt, which disallows `/api/`. It did not repeat the call. Three blocks we respected: docs.fenceit.cloud (robots `Disallow: /`) was not fetched; anneepolitique.swiss serves a Cloudflare challenge, so we read Wayback captures instead; the GitLab spec repo renders only through the API, which robots.txt disallows.

Supporting part files (fuller evidence) are in `/Users/mi11ion/Desktop/hackapertus/bern/research/R1-parts/`:
- `deck-topic-classification.md`: the Bern challenge deck, verbatim
- `opd-wiki-classification.md`: the OPD wiki page, verbatim
- `local-opd-census.md`: numbers computed from our Gegenprobe caches
- `taxonomies.md`
- `prior-art.md`
- `methods.md`

---

## 0. The ten facts that matter

1. **The challenge text is already public, and it is specific.** The deck is at https://hackapertus-topic-classification-5c233f.gitlab.io/ (source `slides.md`, CC BY 4.0, dated "Liebefeld, 18.10.2026"). It asks for an "open, reusable classification service based on Apertus and OpenParlData" with two outputs:
   - "Standard topics: a two-level classification scheme, e.g. Année Politique Suisse"
   - "Ad-hoc topics: defined by users, e.g. 'digitalisation' or 'Covid-19', without retraining"

   **Success criteria (verbatim):**
   - "Classification quality on a labelled sample (e.g. DVS 'digitalisation', accuracy on APS topics)"
   - "Works across languages (at least de / fr / it) and parliament levels"
   - "Ad-hoc topics can be added without retraining"
   - "Feasible runtime for 300,000+ affairs"

   **Partner evaluation:** "Usefulness … Technical quality and reproducibility · Multilingual performance · Innovation · Ease of integration into OpenParlData · Quality of the pitch".

   **Final jury:** "Purposeful use of AI · Technical rigour · Value, cost & scalability · Sovereign deployability · Implementation feasibility".

   **Ethics:** "show why a topic was assigned (confidence, relevant text passage)"; "Topic labels are suggestions; a human must be able to correct them"; "Check for bias between languages, regions and parties"; "must not judge political positions".

   **Expected output:** a public repository under an OSI licence; a working prototype "that classifies affairs from the OpenParlData API"; "Short evaluation results on a labelled sample"; a 5-minute pitch.
2. **OPD itself specified this feature in March 2026.** The OPD GitLab wiki page "Future-Topics/Classification" (author Florin Hasler, BFH IPST, last edited 18 Mar 2026) asks for "a language independent subject classification" and favours "a two-tier classification system, like the one developed and utilized by année politique suisse (APS)". Its closing goal reads: "an open service … that on a given input (documents of political affairs) can provide standardized or ad hoc generated subjects" (https://gitlab.com/groups/opendata.ch/openparldatach/-/wikis/Home/Future-Topics/Classification). The page lists all the prior art (§4).
3. **OPD has no topic field today.** The affairs export, the OpenAPI v1.1 schema and the docs/texts metadata contain no topic, tag, keyword, descriptor, subject or Sachgebiet field. Search is ILIKE/trigram or Postgres tsquery only (local `openapi.json`; `local-opd-census.md`).
4. **Christian's own company already tags topics by hand.** OPD's `external_links` export links **211,525 affairs in about 75 bodies to POLITmonitor**. POLITmonitor is built by Glue AG with polsan AG and the Schweizerischer Gemeindeverband. polsan staff assign "Themen" from a POLITmonitor "Systematik" plus keywords by hand (https://www.politmonitor.ch/ueber-uns/; https://www.politmonitor.ch/angebot/; https://www.politmonitor.ch/handwerk-und-koepfchen-gutes-monitoring-braucht-immer-noch-beides/). The DVS "digitalisation" list the deck names as its use case is generated from POLITmonitor, where "digitalization" is "added manually" (OPD wiki). **[guess]** Automating this is a direct cost saving for Christian's own operation, and the POLITmonitor labels are the best cross-level oracle in existence, if he will share them.
5. **The largest free oracle is the federal parliament's own tags.** Curia Vista `Business.Tags`/`TagNames` (https://ws.parlament.ch/odata.svc/) carries 28 flat "Sachbereiche", assigned by hand by the Parlamentsbibliothek. It is multi-label (mean about 2.4 tags per affair) and uses identical ids in DE/FR/IT. About 59.6k of 68.8k federal affairs are tagged, and 96% of those since 2000 (`taxonomies.md` §2). The library's internal two-level scheme (31 main topics × about 209 sub-topics, **including "Unterthema: Digitalisierung"**, 352 of 15,007 training affairs) is published only inside the BFH prototype's files (https://huggingface.co/spaces/rcds/SwissParlTopicModelling).
6. **APS is the requested scheme, but it is a federal-only oracle and hard to fetch.**
   - **Scheme:** 24 chapters × 190 sub-topics, names in DE and FR only.
   - **Labels:** each APS process has exactly one chapter plus one main sub-topic.
   - **Link to OPD:** OPD links 9,522 CHE affairs (13.7% of CHE, 0 cantonal) to APS articles.
   - **Access:** anneepolitique.swiss sits behind a Cloudflare JS challenge (403 to curl/WebFetch on 13 Oct). We found no open licence and no API (`taxonomies.md` §1).
7. **Nobody has published an open, measured, multilingual, cross-level result.**
   - The BFH prototype uses TF-IDF + Omikuji, one model per language (de/fr/it), and publishes no metrics.
   - The Zürich KI pilot routed affairs to directorates at 92.5–93.4% accuracy, in German only.
   - Demokratis covers 9 of 26 consultation topics with OpenAI embeddings, micro-F1 0.88 on n=99.
   - ParlaCAP reaches macro-F1 0.65–0.72 on 21 CAP topics, but not for Switzerland (`prior-art.md`).
8. **Scale forces a design choice.**
   - 300k affairs × about 400 tokens is about 120M tokens. An 8B log-prob pass over that takes about 10 days on a 16-core CPU, against about 2 h (about $5) on one H100 **[guess, derived]**.
   - Embeddings on CPU take 1–12 h depending on the model.
   - So the back-catalogue is a GPU batch job, or a cheap student model distilled from Apertus. The 20 GB VPS handles the daily delta plus ad-hoc queries (`methods.md` §3).
9. **Apertus 8B on its own is weak at closed-label classification.** Handschuh measured 56 on Banking77 (77 intents). The model "invents types that are not on the list" and puts `License Grant` on 62 of 294 clauses where only 6 are correct, and it never abstains (receipts: 0% null). His advice: constrained decoding, and "With 40 or more categories … classify in two steps" (https://blog.nlp-lab.ai/2026/10/01/Apertus1-5-BusinessBenchmarks.html). Our Gegenprobe closed-set log-prob pointer with a null margin is exactly this remedy, already built and measured.
10. **Event rule:** "Your submission must use the Apertus model · Other open-weights models may support development (e.g. as automatic judges) — describe their role in your report" (hackapertus.ch bundle, per `R4-event-jury-intel.md`). Apertus must therefore do the classifying. Non-Apertus embedders count as support and must be declared **[guess on the interpretation]**.

---

## 1. OPD data (computed locally; bulk export snapshot 6–9 Oct 2026, `local-opd-census.md`)

### 1.1 Volume, levels, languages
- **Affairs:** 325,691 across 89 `body_key`s (LIE, Liechtenstein, accounts for 4,378 and is not Swiss).
  - By level: canton 167,133; city 83,929; federal (CHE) 69,687; municipality 564.
  - The deck's "90 Swiss parliaments / 300,000+ affairs / 900,000 documents" matches.
- **Title languages:**

  | Languages | Affairs | Bodies |
  |---|---|---|
  | de only | 151,603 | |
  | de+fr+it | 68,875 | all CHE |
  | fr only | 53,667 | |
  | it only | 28,071 | |
  | de+fr | 22,130 | BE 8,188, VS 8,589, FR 5,221 |
  | de+it+rm | 1,251 | GR |

  - **Romansh:** 1,252 affairs, all in Graubünden, plus 2,597 Romansh docs. 1,954 more docs carry the bogus `lang="GR"`, an OPD data bug.
  - **Parallel versions (a free cross-lingual consistency test):** about 69k CHE affairs in de/fr/it, and about 22k bilingual cantonal affairs. **[guess]** The cantonal titles are mostly official translations.
- **Time span:** 1990s 17k; 2000s 62k; 2010s 125k; 2020s 118k.

### 1.2 Affair types
- **Harmonised `type_harmonized_en`:**

  | Type | Affairs |
  |---|---|
  | None (untyped) | 55,767 |
  | Question | 55,165 |
  | Interpellation | 53,416 |
  | Government affairs | 37,864 |
  | Motion | 37,373 |
  | Postulate | 33,580 |
  | Question time | 19,060 |
  | "Votaziun" | 9,887 |
  | Parliamentary initiative | 5,817 |
  | Report | 4,340 |
  | Consultation | 3,722 |
  | Petition | 2,052 |
  | "Popular initiative " (trailing space) | 1,893 |

  - **Untyped share by body:** GE 97%, BS 40%, UR 43%, LU 33%, TI 32%.
  - **Data bugs:** "Votaziun" is the Romansh word used as the English label for Wahl (election); "Popular initiative " carries a trailing space. Both are logged in Gegenprobe `results/census/vocab_bugs.tsv`.
- Raw types per body range from 1 to 37 (SZ 37, BS 30, BE 28).
- **[guess]** Elections, naturalisations and appointments make up about 10k affairs that fit no policy topic. The service needs a "no policy topic / procedural" class, as CAP and ParlaCAP have ("Other"/"Mix").

### 1.3 Text available for classification
- **Usable text exists for 81.2% of affairs:** 264,506 have at least one usable document (over 200 characters) or a non-title text.
  - **Gaps:** Chur 0%, Stadt Schaffhausen 0%, Bulle 0%, Münsingen 7%, TI 33%, JU 42%, SZ 51%, GE 59%.
  - **Title-only fallback:** needed for about 19% of affairs.
  - **Title length:** median 65 characters, and 19.4% are under 40 characters, so title-only accuracy will be lower **[guess]**.
- **Documents:** 921,710 rows, of which 595,605 are attached to an affair.
  - Text status: ok 748,019 · null 87,565 · Fedlex JS placeholder 30,482 · blank 28,668 · failed 26,878.
  - Document text per affair: median 10.4k characters, p90 80k. Classify on title plus the first 300–500 tokens of the submitted text, not on all documents **[guess]**.
- **The `texts` table is mostly federal:** 226k rows, 210k of them CHE (Titel 68.8k, Eingereichter Text 63.7k, Antwort BR 50.9k, Begründung 25.6k). A few cantons and cities add Lead/Teaser/Beschreibung.
- **Answers add noise:** a cantonal affair's documents often mix the question with the executive's answer (St. Gallen hack limitation, `prior-art.md` §3b). The executive answer can pull the topic towards the answering department **[guess]**.

### 1.4 Existing topic-like fields in OPD and its sources

| Source | Field | Coverage | Use |
|---|---|---|---|
| OPD affairs/OpenAPI | none | 0 | the gap |
| OPD `external_links` | `politmonitor_affair` link | 211,525 affairs, about 75 bodies | pointer to Glue/polsan manual Themen (labels not in OPD) |
| OPD `external_links` | `aps_affair` link → anneepolitique.swiss/articles/<id> | 9,522 CHE affairs (Motion 3,840, Postulat 2,032, BRG 1,570, Pa.Iv. 1,327, Kt.Iv. 322, PAG 299); 2000s 1.2k, 2010s 3.8k, 2020s 4.6k | APS chapter/sub-topic oracle, if the pages can be read |
| Curia Vista OData `Business.Tags/TagNames` | 28 Sachbereiche, multi-label | about 59.6k CHE affairs; 96% since 2000 | **main free oracle**; join on BusinessShortNumber ↔ OPD CHE `number` **[guess: format check needed]** |
| Curia Vista `ResponsibleDepartment` | 7 departments + Parl/BK | about 99% | weak proxy |
| Bern canton OGD `geschaeft.csv` | `geschaeft_federfuehrung_*` (lead directorate: BVD 903, GSI 716, WEU 655, SID 637, BKD 582, STA 516, FIN 498, DIJ 463, GR 950) | 6,139 affairs, DE+FR | cantonal department proxy |
| Basel-Stadt OGD 100086 | `thema_1`, `thema_2`, `schwerpunkt` (manual, by Kantons- und Stadtentwicklung) | 2,437 überwiesene Vorstösse, Jan 2019–Mar 2024, CC BY 4.0 | **the only open manual cantonal topic gold** (https://data.bs.ch/explore/dataset/100086/; download path disallowed by robots for bots, but a human can download it) |
| Stadt Zürich PARIS API | `Departement`, `Stichworte` | city Gemeinderat | sparse keywords (https://data.stadt-zuerich.ch/dataset/parlamentsdienste_paris_api) |
| Kanton Zürich | directorate triage (internal) | all Kantonsrat Vorstösse | the pilot's training data, not public |
| OPD consultations | `consultation_topics` (Demokratis schema `label_source ∈ {openparldata, organisation_rule, manual}`) | consultations only | **[guess]** OPD already serves topics for consultations; ask which scheme (https://github.com/Demokratis-ch/demokratis-ml/blob/main/demokratis_ml/data/schemata.py) |

**Planned feature:** the OPD wiki "Future-Topics" lists Classification and "Personalized-Function" (fulltext, alerts, lists, labels and comments, "AI Summaries of affairs"). A Budget-2026 page plans a managed VM of 8 CPU / 64 GB RAM / 500 GB (fenceIT, CHF 500/month) to replace a €53/month Hetzner box (cached wiki dump `scratchpad/tc/wikis.txt`, from https://gitlab.com/groups/opendata.ch/openparldatach/-/wikis/pages). **[guess]** The "~20 GB RAM VPS" in the 2 Oct deck is the current box, and the 64 GB VM is the target for 2026/27. Ask which one to design for.

---

## 2. Label sets and free oracles

| Scheme | Shape | Languages | Free labels on OPD affairs | Licence / access | Verdict |
|---|---|---|---|---|---|
| **APS** (Uni Bern IPW) | 24 chapters (dotted codes 1.1.1.–2.0.2.) × 190 sub-topics; 1 chapter + 1 main sub-topic per process; keywords carry chapter CSS classes, so multi-label is recoverable | de, fr (no it/rm, per the APS FAQ) | 9,522 CHE via OPD links (federal only; APS has no current cantonal coverage) | no open licence found; Cloudflare-blocked; Wayback captures exist; no API | **The scheme Christian names.** Use it as the target vocabulary. Translate the labels to it/rm with Apertus and have them reviewed **[guess]**. Get the labels via Christian/APS (he links them already) |
| **Curia Vista Sachbereiche** | 28 flat (ids 4…2846); library-internal 2nd level about 209 (31 main) | de/fr/it identical ids | about 59.6k CHE, multi-label (mean 2.4) | public OData, no key, no robots.txt | **Best oracle by size.** Evaluate the chapter level via an APS↔Sachbereich crosswalk, which we would build and publish **[guess]** |
| **Parlamentsbibliothek 2-level** (BFH `topics_hierarchy.json`) | 31 × 209, includes "Digitalisierung" | German labels only | none public per affair (train file has features only, no ids) | HF Space files | Label priors plus the BFH baseline; cite it, beat it |
| **POLITmonitor Systematik** | unknown (topics like Gesundheit/Wirtschaft/Umwelt/Energie, plus Stichworte) | de/fr site | about 211k affairs linked across levels | proprietary (Glue/polsan) | **Ask Christian.** It is the only cross-level human labelling |
| **CAP** master codebook | 21 major / 220 sub | English codebook only; multilingual models gated | **Swiss CAP "Federal Reports" (Botschaften) 1978–2008: 1,951 rows with `source` = Geschäftsnummer (e.g. "78.001"), majortopic/subtopic, so they join to CHE "Geschäft des Bundesrates" affairs**; parliamentary interventions 1995–2003 (9,949) coded but not downloadable | CSVs open, citation required (https://minio.la.utexas.edu/compagendas/datasetfiles/switzerland_government.csv); poltextLAB models gated, academic only | a small extra federal oracle plus a crosswalk target; no APS↔CAP crosswalk exists (https://compagendas.la.utexas.edu/project/ch/datasets) |
| **Basel-Stadt KSE topics** | thema_1/2 + Schwerpunkt | de | 2,437 BS affairs | CC BY 4.0 | the only cantonal manual gold; out-of-domain check |
| **DVS digitalisation list** | single ad-hoc topic | de (site also fr/it/en) | 30 items rendered in a rolling window: BE 12, CHE 5, ZG 3, OW 3, BS 2, ZH 1, TG 1, plus 3 with no body. Of these, 4 are Vernehmlassungen, not affairs. No municipal items. The full list (with "Unterkategorien" and export) sits in POLITmonitor and is free only to staff on the KOMBV-KTV network | public web page, no download | **Positives only and small**, so it measures recall, not precision. The real gold is the POLITmonitor "Digitalisierung" export, which maps 1:1 to OPD via the politmonitor links (https://www.digitale-verwaltung-schweiz.ch/aktuelles/politische-geschaefte) |
| Swissvotes Politikbereiche | 3 levels (d1e1–d3e3; 12 / 56 / 87 distinct values), up to 3 areas per vote | de/fr/en | 714 federal votes, joinable via `gesch_nr` | CC BY 4.0 (https://swissvotes.ch/page/dataset) | too few items; a possible L1 alternative |
| EuroVoc 4.24 | 21 domains → 127 microthesauri → about 7k descriptors | 27 languages incl. de/fr/it, **no rm** | none | EU reuse policy | too EU-centric and fine-grained |
| Fedlex SR systematics | 0–9 top level, 2–3 sub-levels | de/fr/it | **[guess]** affairs that cite "SR 832.10" etc. can be auto-labelled | open LOD | a law-oriented silver oracle only |
| eCH Fachgruppe "Politische Geschäfte" | — | — | — | — | The mandate (FAAN v0.4, 13 Mar 2025, author Gutknecht; lead Michael Luggen, BK, and Gutknecht) lists "**Classification (indexation) des affaires parlementaires**" as a further harmonisation topic, with code lists to go on I14Y. No vocabulary has been chosen (https://ech.ch/sites/default/files/imce/Fachgruppen/Politische%20Gesch%C3%A4fte/FAAN_f_DRA_2025-03-13_Donn%C3%A9es%20affaires%20politiques.pdf). **[guess]** Our output schema can be pitched as a draft topic field for the standard |

**The recommended label strategy [guess, grounded]:**
- **Output:** APS's 24 chapters (level 1) and 190 sub-topics (level 2), because the deck and the wiki both name them, plus a residual "no policy topic" class.
- **Supervision and evaluation, CHE:** Curia Sachbereiche (about 60k, trilingual, multi-label), mapped to APS chapters through a published crosswalk, plus the 9.5k APS-linked affairs as direct gold if the labels are obtainable.
- **Supervision and evaluation, cantonal:** the Basel-Stadt 2,437 affairs, the Bern directorate proxy, and blind agent annotation of a stratified random sample.
- **Ad-hoc evaluation:** DVS recall, the library's "Digitalisierung" sub-topic if obtainable, and a second topic (Covid-19, as the Matoshi study used) with a precision estimate from blind annotation.

---

## 3. Prior art (details in `prior-art.md`)

| Prior art | Task | Model | Langs | Labels | Reported metric | Open? |
|---|---|---|---|---|---|---|
| BFH × Parlamentsbibliothek 2024 (Gygli, Singh, Matoshi); HF `rcds/SwissParlTopicModelling` | Curia topics suggestion | fastText LID → per-language TF-IDF (spaCy) + Omikuji Bonsai | de/fr/it, separate models | 233 (31 Haupt + Unterthemen) | **none published** | code + models (`kapllan/omikuji-bonsai-parliament-spacy-{de,fr,it}-…`) |
| Innosuisse study POLITmonitor × BFH IPST ("Mathoshi 2023" = Veton Matoshi) | predefined + ad-hoc topics (Covid-19) | ? | ? | ? | not public (docs.fenceit.cloud blocks all bots in robots.txt) | no |
| Kanton Zürich KI pilot 2023 | route Vorstösse to directorate | DistilBERT/GBERT fine-tune | de | 8 directorates | **92.5–93.4% acc**; office level 73%; zero-shot vs 129 blocks ~73% at **241 s/affair**, 28% when blocks were merged | report only (https://www.zh.ch/content/dam/zhweb/bilder-dokumente/organisation/direktion-der-justiz-und-des-innern/statistisches-amt/KI%20Pilot%20Bericht_V2.0.pdf) |
| Demokratis (MIT) | consultation topics | OpenAI text-embedding-3-large + LogReg | de | 9 of 26 | micro-F1 0.88 (n=99) | yes, but uses a closed API |
| ParlaCAP 2026 (CLARIN.SI) | speech CAP topics | GPT-4o teacher → XLM-R-Parla student | 28 parliaments, no CH | 21 + Other | macro-F1 0.65–0.72; 0.68–0.76 with conf<0.6 → "Mix" (about 10%) | model + data open (https://arxiv.org/abs/2602.16516) |
| St. Gallen Open Data Hack 2023 (#1076) | city parliament topics | Llama/GPT-4 prompts + Power BI | de | ad-hoc | **none** | GitHub |
| Basel-Stadt politmonitor.bs.ch | topic clustering | manual (KSE); AI redo promised for 2025 | de | thema_1/2 | n/a; site offline (NXDOMAIN) | OGD 100086 |
| SDSC DemocraSci | federal knowledge graph (Curia tags as `Tag/Issuelist`) | — | de | — | the APS classifier is only claimed orally ("works sufficiently", Luis Salamanca) | KG CC BY (https://zenodo.org/records/13920293) |
| GovTech Innovationsbörse 2023 (BK DTI) | "dynamische thematische Strukturierung" of about 1,500 Mo/Po per year | — | — | — | — | PDF returned 502; search snippet only |
| Commercial: politik.ch (PolitAnalytics; "Unsere leistungsstarke KI"), furrerhugi (uses politik.ch), POLITmonitor (manual) | monitoring | undisclosed | | | none published | closed |

Not found: any public topic tagging by LegisLense, Polittrends, smartmonitor or politools. The only common pattern is closed keyword-and-topic filtering with no published accuracy.

---

## 4. Method landscape (details in `methods.md`)

### 4.1 Accuracy anchors
- **Supervised in-domain CAP (XLM-R-large):** accuracy about 0.82, macro-F1 0.80. Applied cross-domain to ParlaMint speeches it falls to macro-F1 0.49–0.64 (https://arxiv.org/html/2602.16516v1, Table 4).
- **Zero-shot LLMs on 21-class CAP:**
  - GPT-4 0.69–0.70; GPT-3.5 and Llama 3 0.59–0.64.
  - Keeping only items where two models agree (65% coverage) gives 0.83 (https://ar5iv.labs.arxiv.org/html/2310.08167).
- **Cross-domain top-k gap:** top-1 0.41 vs top-3 0.65 (44 topics), and 0.51 vs 0.82 (8 topics) (Osnabrügge/Ash/Morelli, https://elliottash.com/papers/Osnabruegge-Ash-Morelli-Merged.pdf). Show top-3 suggestions.
- **Human ceiling:** CAP α ≈ 0.6–0.7; about 85% raw agreement on titles. GPT-4o vs humans α 0.60–0.64 ≈ human–human (ParlaCAP).
- **Apertus 8B:** about GPT-3.5 level or below (Handschuh: 57.9 overall vs GPT-3.5 63.2). **[guess]** Zero-shot accuracy on APS chapters alone would be about 0.50–0.65.

### 4.2 Compute (all [guess], derived from cited benchmarks)

| Path | 16-core CPU | OPD-like 8 vCPU | 1×H100 |
|---|---|---|---|
| Embed 325k × 400 tok, mE5-small (MIT, 226 NQ docs/s on 7950X) | ~1.2 h | ~3 h | minutes |
| Embed, mE5-large / bge-m3 / harrier-270m | 7–12 h | 1–1.5 days | ~15 min |
| Apertus 8B closed-set scoring (one forward pass, cached prefix) | ~10 days; ~1 day titles-only | ~1 month | ~2 h (~$5) |
| Apertus 70B teacher on a 20k sample | — | — | ~1 GPU-h on 4×H100 |

- **Daily delta [guess: ≲ a few hundred affairs/day]:** 8B Q4_K_M at about 3–5 s per affair on CPU means minutes per day, which fits 20 GB (5.1 GB weights + KV + Postgres/pgvector at about 0.5–1.3 GB for 325k vectors).
- **llama.cpp status:** Apertus 1.0 has been supported since b6671. Apertus 1.5 has no official support (issue #26300 open). Community text-only 1.5 GGUFs load with `--override-kv tokenizer.ggml.eos_token_id=int:68 -sp` (https://huggingface.co/katya228/Apertus-v1.5-70B-text-GGUF; Q4_K_M 8B at 5.06 GB: https://huggingface.co/Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF). Our Gegenprobe CI already runs an 8B GGUF Q4_K_M on CPU.

### 4.3 Patterns that work
- **Closed-set log-prob scoring.** Score each allowed label code after a fixed prompt, with no free text, so invented labels are impossible by construction.
  - Shuffle the codes or use neutral ones, and apply contextual calibration (Zhao et al. 2021: up to +30 points; https://arxiv.org/abs/2102.09690).
  - Run two steps, chapter then sub-topic, with KV reuse.
- **Teacher → student distillation (ParlaCAP recipe).** Apertus-70B labels a 5–20k stratified sample, and a logistic or MLP head on frozen embeddings labels all 325k in minutes on CPU and retrains in seconds. The student matches the teacher (EN 0.72 vs 0.74).
- **Computed abstention.**
  - A max-prob threshold: ParlaCAP keeps 90% of items and gains +0.04.
  - Agreement filters: student ∧ Apertus, or agreement across the de/fr/it titles.
  - Split-conformal prediction sets with about 90% coverage. An empty or oversized set means abstain.
- **Ad-hoc topics with no retraining:**
  1. Apertus expands the topic into a de/fr/it/rm definition and keywords.
  2. Hybrid retrieval: Postgres FTS (already in OPD) ∪ kNN over embeddings.
  3. Apertus checks yes/no by log-prob on the top-N, plus an evidence sentence (verified as an exact substring).
  4. Optionally, a few-shot head (SetFit / LogReg) learned from user thumbs.
- **Explanations.** The highest-similarity sentence per label, or an Apertus-chosen span verified by code (Gegenprobe `pointer.locate` pattern).

### 4.4 Embedders (licence matters for OPD)

| Model | Params | Licence | Notes |
|---|---|---|---|
| multilingual-e5-small / base / large | 118M / 278M / 560M | MIT | |
| bge-m3 | 568M | MIT | 8k context |
| microsoft/harrier-oss-v1-270m | 268M | MIT | best CPU-sized MMTEB: 66.6 vs bge-m3 59.6 |
| Qwen3-Embedding-0.6B | 596M | Apache | |
| jina-v3 | | **CC-BY-NC** | ✗ licence |
| EmbeddingGemma | | gated | ✗ |
| `andreasmartin/apertus-v1.1-swiss-embed-0.4b-bidir` | 439M | Apache | the only Apertus-derived embedder; covers rm; cross-lingual Acc@1 0.28 vs mono 0.80 |

- **No XLM-R-derived model lists Romansh.** Apertus post-training has 46k Romansh SFT examples (https://arxiv.org/abs/2509.14233). **[guess]** For the 1.3k GR affairs, route rm → Apertus (or classify their de/it parallel titles, which GR affairs always have) and audit them separately.
- **[guess]** An "all-Apertus" option for the event's "must use Apertus" rule: mean-pooled hidden states from Apertus 8B (or the 0.5B/1.5B v1.1), or the andreasmartin embedder, as the student's features. Benchmark against mE5 on the parallel federal titles first.

### 4.5 Evaluation without human gold (consistent with our no-human-labelling rule)
1. **Silver held-out sets:**
   - Curia Sachbereiche (about 60k CHE, multi-label): micro/macro-F1, top-3.
   - APS chapter/sub-topic on the linked 9.5k.
   - BS 2,437 thema.
   - BE directorate as a weak proxy (a confusion table, not accuracy).
2. **Blind agent annotators** on a stratified random sample (by level × language × type × party), using the Gegenprobe protocol: two blind annotators from different families plus a tie-breaker, code-verified quotes, an isolation audit. Report Krippendorff α annotator–annotator vs system–annotator, and target the human band of 0.6–0.7.
3. **Cross-lingual consistency:** classify each language version independently (69k CHE de/fr/it; 22k cantonal de/fr) and report the agreement rate and Fleiss κ per language pair. This is the deck's "multilingual" and "bias between languages" criteria, measured without any gold.
4. **Bias tables:**
   - label distribution and abstention rate by language, canton/level and submitter party (OPD contributors + groups)
   - a party-neutrality check: for a fixed silver label, do predictions shift with the party? **[guess: method]**
5. **DVS:** recall@k on the list's positives, plus precision from blind annotation of the top-k hits that are not on the list.
6. **Baselines on the same split:**
   - BFH Omikuji (federal)
   - keyword/FTS search, which is what users do today
   - a majority/prior baseline
   - embeddings-only zero-shot
   - Apertus-8B free generation (the naive arm), to show the invented-label rate

---

## 5. What other teams will build, where it breaks, and what reads as "clearly #1"

### 5.1 The naive build [guess, grounded in the St. Gallen hack, commercial tools and Handschuh]
Teams will prompt Apertus (8B or 70B) with a title and maybe the text, plus a list of topics, and ask for JSON tags. "Ad-hoc" will mean putting the user's word into the prompt. The demo will show 10–20 hand-picked federal affairs in a Streamlit UI, with "accuracy" eyeballed or measured on a handful of examples.

### 5.2 Where it breaks
1. **Invented or over-general labels.** Apertus 8B goes off-list ("Severability", "sarcasm") and collapses onto one general label (`License Grant` 62×) (Handschuh). With 214 APS labels (24 + 190), a flat prompt is beyond the 8B.
2. **No metric.** That is Christian's own 2A pain ("No gold standard. No metric") and the St. Gallen hack's outcome. The deck explicitly asks for "Short evaluation results on a labelled sample".
3. **Runtime.** Per-affair LLM generation over 300k affairs takes weeks on CPU. Zero-shot per-label scoring is O(labels): Zürich measured 241 s per affair. Teams will hand-wave "feasible runtime".
4. **DVS misuse.** The list holds positives only and is small, so a team reporting "precision" against it is reporting nothing.
5. **Federal-only demos.** CHE has clean trilingual text, while cantonal and municipal affairs are short, PDF-heavy, mixed question/answer, and 19% title-only. "Works on Curia Vista" is not "works on 90 parliaments".
6. **FR/IT/RM unmeasured.** Prior art is mono-German or uses separate monolingual models. Romansh is ignored.
7. **No "why", no abstain, no correction path.** These are explicit ethics requirements in the deck.
8. **Not integrable.** A notebook or Gradio app instead of a FastAPI service that reads OPD affairs and writes back a typed, provenance-marked topic record (OPD stack: FastAPI/Pydantic/PostgreSQL/Apache Hop).

### 5.3 What makes each juror say "#1" [guess, grounded in R4 + `prior-art.md`]
- **Christian (OPD/Glue; votes at gate 1 only):**
  - It runs against the OPD API and bulk exports as they are, and covers all 89 bodies and every language.
  - It automates the DVS/POLITmonitor manual tagging, his own operating cost, with a measured recall.
  - Output is an OPD-ready topic table (affair_id, scheme, label_id, score, rank, evidence span, model build, `inferred` provenance), plus a FastAPI endpoint and a Hop-friendly batch CLI.
  - It reports per-body coverage and failure lists, as Gegenprobe did.
  - It publishes the APS↔Curia crosswalk and the eval sets as reusable open artefacts, which is "The Gap: thematic structure … as a shared, reusable resource".
- **Susie Xi Rao (BFH, hierarchical classification):**
  - per-level metrics (chapter/sub-topic) with baselines and an ablation (embeddings-only vs + Apertus verifier vs naive generation)
  - calibration plots, an abstention-coverage curve, and annotation agreement
  - beating the BFH (her own institution's) Omikuji baseline on the same split
- **Lena Fuhrimann (bespinian, cloud architect):**
  - one `docker compose up` (API + Postgres/pgvector + llama.cpp 8B)
  - a measured RAM figure (≤20 GB) and throughput
  - a stated cost per 1,000 affairs and a full-backfill cost (GPU hours), with nightly delta jobs
- **Barthélémy Rochat (Biel/Bienne CDO):**
  - DE/FR parity measured on bilingual affairs (Biel and Bern are bilingual)
  - municipal coverage (Biel itself is not in OPD, which has 50+ cities; **[guess]** a "your city could plug in" story)
  - human-in-the-loop correction and governance
- **Oleg Lavrovsky (EPFL AI Center):**
  - everything open: code, crosswalk, eval sets, the HF model card for the student head
  - honest Apertus limits (e.g. the free-generation arm's invented-label rate)
  - reproducibility (`make eval`)
  - **[guess]** a contribution back upstream: llama.cpp 1.5 notes, an HF dataset

**The single strongest pitch line [guess]:**
- Today, finding everything Swiss parliaments did on digitalisation takes a person tagging by hand.
- Our Apertus service tags all 325k affairs in 24 APS fields, in de/fr/it/rm, every label with a quoted reason.
- It never invents a label: closed set, abstains when unsure.
- It recovers X% of the DVS list, agrees with the Federal Parliament's own Sachbereiche at F1 Y, gives the same answer across languages Z% of the time, and costs CHF N for the full back-catalogue, then runs nightly on OPD's own 20 GB server.

---

## 6. Questions for Christian (60-min deep dive, Sun 10:30)

**Data and labels (highest value first)**
1. Can Glue/polsan export the POLITmonitor Themen/Stichworte per affair (even a 2–5k sample) for evaluation? What is the POLITmonitor Systematik: levels, count, languages? Is "Digitalisierung" a subject there?
2. Can you give us the **full DVS list** (all affairs ever flagged, with OPD ids or numbers), and is it exhaustive for any time window, so that precision could be estimated?
3. **APS:** do you have, or can you get, the (Geschäftsnummer, chapter, sub-topic) pairs behind the 9,522 `aps_affair` links? The site is Cloudflare-protected. Is APS's licence OK for evaluation and for publishing derived labels? Is the APS scheme doc on docs.fenceit.cloud (wiki link) the 24×190 scheme, or a different two-tier version?
4. Should we target the **APS 24 chapters × 190 sub-topics**, or the 9-group roll-up as level 1? Are the "Parteien/Verbände" chapters (2.0.x) in scope for affairs? Is multi-label wanted (APS keywords span chapters) or one primary topic?
5. Is the Curia Vista Sachbereiche set (28, about 60k CHE tagged by the Parlamentsbibliothek) an acceptable silver standard? Do you know whether the library's second level (about 209 Unterthemen incl. Digitalisierung) can be obtained?
6. What does the OPD consultations topic field (seen in Demokratis' schema, `label_source=openparldata`) contain? Which scheme?
7. Basel-Stadt "earlier classification work" (deck): is the AI re-categorisation done, and can we use the KSE topics set 100086 (2,437 affairs)?

**Integration and deployment**

8. Target box: the current ~20 GB VPS, or the planned 8 CPU / 64 GB managed VM? Is there a GPU anywhere? Is a one-off GPU backfill (hours, about $5–50) acceptable if nightly runs stay on CPU?
9. Preferred output contract: a new `topics` table / API resource (affair_id, scheme, label, score, rank, evidence, model_version, status suggested|confirmed|rejected)? Does it go through Apache Hop or a FastAPI microservice? Any eCH Fachgruppe position on a topic/subject field or vocabulary?
10. Which input text: title + submitted text only, or the executive's answer too? Should we avoid documents (OCR cost, answer bias)?
11. Ad-hoc topics: who defines them (OPD admins vs end users)? What latency is expected: an interactive query (seconds) or a background job (minutes)? Should ad-hoc results persist as shared labels?
12. Human correction: should corrections flow back into the admin workbench (admin.openparldata.ch), as the extraction review step does?

**Judging and scope**

13. How will "accuracy on APS topics" be measured on the day? Do you bring a labelled sample? Is it federal only, or does it include cantonal?
14. Is non-Apertus support (an MIT multilingual embedder for retrieval) acceptable if Apertus does every classification decision? Or do you want all-Apertus (e.g. Apertus-derived embeddings)?
15. Priority: breadth (all 89 bodies, all languages) or depth (excellent on CHE + 3 cantons)? How much does Romansh matter (1,252 GR affairs)?
16. Neutrality: which party/region bias checks would convince you? Do you have a party field you trust (contributors → groups)?
17. Can we cite you and OPD/POLITmonitor by name in the pitch and report?
18. The deck says "classifies affairs from the OpenParlData API", but robots.txt disallows `/v1/`. Is a programmatic API client at the event, with a contact User-Agent and rate limits, explicitly OK? Otherwise we use the bulk exports plus a thin adapter.

---

## 7. Our reusable assets (from Gegenprobe, `~/Desktop/hackapertus/gegenprobe/track_2a/`)
- **Bulk-export loaders and census:** `src/gegenprobe/census/`, compact tables in `data/census/`, and raw exports under `~/Desktop/hackapertus/spikes/data/raw/opd/`. Re-download fresh exports from files.openparldata.ch on day 1.
- **Closed-set log-prob pointer** (`convert/pointer.py`): prefilled JSON prefix, summed log-probs over the allowed options, and a null margin θ fitted per model build (θ does not transfer across builds; memory note `project-publicai-build-switch.md`).
- **Public AI routing:** `swiss-ai/apertus-v1.5-8b` accepts prefill/logprobs; never prefill to `-70b`.
- **8B Q4_K_M GGUF CPU runs** in CI.
- **Blind-agent annotation protocol:** two annotators plus a tie-breaker, an isolation audit, a manifest. Qwen cross-relabel κ 0.80–0.87.
- **Pre-registration and hash-lock machinery.**
- **Lesson carried over:** test every Apertus headline against the best no-model or embedding baseline before claiming it (memory note on Gegenprobe P10).

## 8. Key URLs
- **Deck:** https://hackapertus-topic-classification-5c233f.gitlab.io/ (slides.md)
- **2 Oct deck:** https://hackapertus-document-extraction-26a562.gitlab.io/
- **OPD wiki Classification:** https://gitlab.com/groups/opendata.ch/openparldatach/-/wikis/Home/Future-Topics/Classification
- **OPD exports:** https://files.openparldata.ch/exports/
- **API docs:** https://api.openparldata.ch/documentation (docs page only; /v1/ is robots-disallowed)
- **Curia Vista OData:** https://ws.parlament.ch/odata.svc/$metadata; https://ws.parlament.ch/odata.svc/Tags?$filter=Language%20eq%20'DE'&$format=json
- **APS topics (archived):** https://web.archive.org/web/20260215050943/https://anneepolitique.swiss/topics
- **BFH prototype:** https://huggingface.co/spaces/rcds/SwissParlTopicModelling; https://www.bfh.ch/de/forschung/forschungsprojekte/2024-265-557-050/
- **ParlaCAP:** https://arxiv.org/abs/2602.16516; https://huggingface.co/classla/ParlaCAP-Topic-Classifier
- **Handschuh benchmark:** https://blog.nlp-lab.ai/2026/10/01/Apertus1-5-BusinessBenchmarks.html
- **POLITmonitor:** https://www.politmonitor.ch/ueber-uns/; https://www.politmonitor.ch/open-parl-data/
- **DVS list:** https://www.digitale-verwaltung-schweiz.ch/aktuelles/politische-geschaefte
- **Basel-Stadt topics:** https://data.bs.ch/explore/dataset/100086/
