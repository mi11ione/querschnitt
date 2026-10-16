# Submission text (sprintd, Mon 19 Oct, 14:30 — Roman submits)

**Title:** Querschnitt

**Tagline:** One topic field for every parliament in OpenParlData — chosen by Apertus from a closed list, with the
sentence that supports it and a lane that says when a person should check.

**Links**
- Repository: https://github.com/mi11ione/querschnitt (Apache-2.0 code, CC BY 4.0 docs, CDLA-Permissive-2.0 topics file)
- Live: https://querschnitt.mi11ion.io
- Report: `querschnitt-report.pdf` (GitHub release `data-latest`; source `docs/REPORT.md`)
- Video (2 min, backup demo): `querschnitt-demo.mp4` (same release)

**Description (≈ 150 words)**

OpenParlData collects the affairs of about 90 Swiss parliaments but has no topic field. Querschnitt gives every affair
an Année Politique Suisse chapter with ranked subtopics, ad-hoc topics defined in one sentence, and a parliament's own
scheme as a file — Bern's directorates, Basel-Stadt's themes, Ticino's departments — without training. Each label is a
choice Apertus makes from a closed list, read from its next-token probabilities, with the quoted sentence that supports
it; where it is unsure, or where the German and French readings disagree, the affair goes to a person.

On 927 federal affairs labelled by the APS editors and never used while building, registered in advance, it picks the
editors' chapter in 0.696 (keywords 0.186); two thirds pass without a check and are right in 0.812. Every number is in
the Prüfstand with its source file. The upstream pack — migrations, an Apache Hop loader and a read API, tested in CI —
is ready for OpenParlData.

**Model roles:** Apertus (`swiss-ai/apertus-v1.5-8b` on Public AI) makes every topic decision that ships. Blind Claude
runs and Qwen-SEA-LION served only as annotators in the evaluation, where no human labels exist; the code was written
with Claude Code.

**Team:** (Roman fills in).
