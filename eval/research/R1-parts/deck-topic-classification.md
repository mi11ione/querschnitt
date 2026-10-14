# Source: https://hackapertus-topic-classification-5c233f.gitlab.io/slides.md (fetched 2026-10-13T10:52:22Z); CC BY 4.0, Christian Gutknecht
</style>

# OpenParlData: Topic Classification for Swiss Parliaments with Apertus <!-- .element: style="font-size: 2.8rem; text-transform: none; font-weight: bold;" -->
<!-- .slide: id="title-slide" -->

**Hack Apertus Liebefeld**

[Christian Gutknecht, OpenParlData / Glue AG](https://orcid.org/0000-0002-7265-1692) <img src="https://orcid.org/sites/default/files/images/orcid_16x16.png" alt="ORCID iD" style="vertical-align: text-top;">

[info@openparldata.ch](mailto:info@openparldata.ch)

`Liebefeld, 18.10.2026`

[© CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

---

## Context

Switzerland has parliaments at three levels, operating across **four languages**:

- The Federal Assembly
- 26 cantonal parliaments
- Several hundred municipal / city parliaments

---

## Focus: the Parliamentary Affair

Motion, postulate, interpellation, written question, initiative

- Submitted by members
- Answered by the executive
- Usually closed by a decision

---

## OpenParlData

[openparldata.ch](https://openparldata.ch)

- Collects data from **90 Swiss parliaments** daily
- **300,000+ parliamentary affairs** and **900,000 documents**
- German, French, Italian and, to a tiny extent, Romansh
- API: [api.openparldata.ch](https://api.openparldata.ch/documentation)
- Bulk exports: [files.openparldata.ch](https://files.openparldata.ch/)

---

## Today: Full-Text Search Only

- Users must anticipate the terminology used in the documents
- ... and repeat that in every language
- A simple question like *"What did Swiss parliaments decide on digitalisation?"* means a lot of manual work

---

## Fragmented Topic Schemes

Several parliaments, organisations and research projects classify affairs by topic, but:

- Each built for a specific use case
- Different classification schemes
- Often tagged manually

A classification made for one purpose **cannot be reused** for another.

---

## The Gap

The data is available.

Its **thematic structure** is not available as a shared, reusable resource.

---

## Main Objective

Build an **open, reusable classification service** based on **Apertus** and **OpenParlData**.

Input: affairs, including titles, texts and associated documents, in de / fr / it / rm

---

## Two Kinds of Output

- **Standard topics**: a two-level classification scheme, e.g. [Année Politique Suisse](https://anneepolitique.swiss/)
- **Ad-hoc topics**: defined by users, e.g. "digitalisation" or "Covid-19", without retraining

---

## Real Use Case: Digital Administration Switzerland (DVS)

- DVS currently identifies digitalisation-related affairs **manually**
- Goal: identify them automatically across the whole OpenParlData dataset
- Validates the approach against a real, existing process

---

## Datasets Provided

- **OpenParlData API** (REST/JSON, public, no key): [api.openparldata.ch/documentation](https://api.openparldata.ch/documentation)
  - Affairs, documents with extracted text, bodies, persons, votes
  - Federal, cantonal and municipal level
- **Data export**: [files.openparldata.ch](https://files.openparldata.ch/)
- Data protection: only material already published by the parliaments themselves

---

## Supporting Materials

- Background and prior work: [OpenParlData wiki: Classification](https://gitlab.com/groups/opendata.ch/openparldatach/-/wikis/Home/Future-Topics/Classification)
- BFH prototype: [huggingface.co/spaces/rcds/SwissParlTopicModelling](https://huggingface.co/spaces/rcds/SwissParlTopicModelling)
- Demokratis classification for consultations: [github.com/Demokratis-ch/demokratis-ml](https://github.com/Demokratis-ch/demokratis-ml)
- Earlier classification work from Basel-Stadt
- API documentation and example queries

---

## Technical Preferences

| | |
|---|---|
| **Languages / frameworks** | No restriction |
| **Production stack (reference)** | Python (FastAPI), PostgreSQL, ETL via [Apache Hop](https://hop.apache.org/) |
| **Platform** | Apertus compute and inference infrastructure of the hackathon, or run locally |
| **Model** | Apertus |
<!-- .slide: id="tech-preferences" -->

---

## Model Sources

- [huggingface.co/swiss-ai](https://huggingface.co/swiss-ai)
- [huggingface.co/swiss-ai/Apertus-v1.5-8B](https://huggingface.co/swiss-ai/Apertus-v1.5-8B)
- [huggingface.co/swiss-ai/Apertus-v1.5-70B](https://huggingface.co/swiss-ai/Apertus-v1.5-70B)

---

## Expected Output

- Source code in a **public repository** under an open-source licence (README with setup and usage)
- A **working prototype** (API endpoint, script or small demo UI) that classifies affairs from the OpenParlData API
- Short **evaluation results** on a labelled sample
- **5-minute pitch / demo** on the final day

---

## Success Criteria

- Classification quality on a labelled sample (e.g. DVS "digitalisation", accuracy on APS topics)
- Works across languages (at least de / fr / it) and parliament levels
- Ad-hoc topics can be added **without retraining**
- Feasible runtime for **300,000+ affairs**

---

## Evaluation Criteria

- Usefulness for the OpenParlData community and public-sector users
- Technical quality and reproducibility
- Multilingual performance
- Innovation
- Ease of integration into OpenParlData
- Quality of the pitch

---

## Final Jury Criteria

- Purposeful use of AI
- Technical rigour
- Value, cost &amp; scalability
- Sovereign deployability
- Implementation feasibility

---

## Ethics: Transparency

- Explainable results: show **why** a topic was assigned (confidence, relevant text passage)
- Topic labels are **suggestions**; a human must be able to correct them

---

## Ethics: Neutrality

- Check for bias between languages, regions and parties
- Classification must stay neutral and must not judge political positions

---

## Legal &amp; Compliance

- All data is public open government data from Swiss parliaments
- Solutions published under an open-source licence
- See the Hack Apertus Terms &amp; Conditions (&sect;6)

---

## See You On Site
<!-- .slide: id="next-up" -->

**Deep-dive workshop: Sun 18 Oct, 10:30**

Mentoring on Sunday<br>Final pitches: Mon 19 Oct, 15:00

Christian Gutknecht<br>[info@openparldata.ch](mailto:info@openparldata.ch)
