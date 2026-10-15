# S29 sources: a French- or Italian-speaking parliament's own label on its affairs

Searched 15 Oct 2026, read-only. No call to api.openparldata.ch. Every automated web request was checked first against the
host's robots.txt with RFC 9309 longest-match (`querschnitt.net.robots_rules` / `decide`).

## 1. OPD exports on disk (`../data/opd-new/`, export of 15 Oct 2026 05:05 UTC)

`affairs.ndjson.gz` has no topic, keyword or department column for any body. The only fields filled for the French and
Italian bodies are number, ids, type, state, date and URL. The parliament or administration's own assignment shows up in
`contributors.ndjson.gz` as a group row with role `leading_department` («Federführung»). `data.py` reads Bern's `dept` from
the same field. Rows of role `publisher` are not tied to an affair (affair_id null).

| Body | Language | Field | Affairs with it | Distinct values | Joinable to inputs.jsonl.gz | Verdict |
|---|---|---|---|---|---|---|
| **TI Gran Consiglio** | it | contributors `leading_department`, position 1 (external_id `…_dep_1_DFE` etc.) | 16,855 (1985–2026) | 8: 5 Dipartimenti, Cancelleria dello Stato, Consiglio di Stato del Ticino, Gran Consiglio (Ticino) | 16,854 by OPD id; 2,274 begun 2023-01-01…2026-10-11 (2,267 with text) | **usable: chosen for S29** |
| NE Grand Conseil | fr | contributors `leading_department` | 4,383 (2009–2026) | 18: department names change with every reorganisation (2013, 2021, 2024, 2025), plus Présidence | 4,383 by OPD id | usable with care: affairs carry names from later periods (e.g. 27 affairs of 2021–23 labelled with the 2025 name «Département de la formation et des finances"), so a single scheme needs a mapping between periods. Not run; best French candidate for a follow-up |
| JU Parlement | fr | `leading_department` | 153 | 6 | 152 | too few (< 300) |
| VS Grand Conseil | de/fr | `leading_department` | 67 | 29 (departments and offices mixed, German names) | — | too few |
| VD Grand Conseil | fr | `leading_department` | 2,627 | 310: they are person names (rapporteurs/authors), not departments | — | not a topic field |
| GE Grand Conseil | fr | `publisher` (departments and offices, 181 values) | 0 affairs (rows not linked to an affair) | — | — | no per-affair label |
| FR Grand Conseil | de/fr | `publisher` | 0 affairs | — | — | no per-affair label |
| Genève (6621), Lausanne (5586), Lugano (5192), Bellinzona, Locarno, Mendrisio, Fribourg, Vernier, Neuchâtel (6458), La Chaux-de-Fonds, Sierre, Monthey, Bulle, Collombey-Muraz, Val de Bagnes | fr/it | author / co-signer / committee only | — | — | — | no topic or department field |

`texts/*` for the French/Italian bodies on disk (VD, FR, 5586, 6248, 6421) hold only text types (Texte déposé, Résumé,
Contenu, Réponse), not topics.

## 2. Open-data portals

opendata.swiss CKAN `package_search` (robots.txt allows `/api/3/action/`) for «Grand Conseil» (855 hits), «Gran
Consiglio» (93), «objets parlementaires» (530), «Conseil municipal Genève» (1,506), «Conseil communal Lausanne» (560),
«Consiglio comunale». I read the top 25 of each. None is a list of parliamentary affairs with a thème/dicastère/département
column. The hits are election results, seat counts by party (SSD Genève, USTAT Ticino), geodata, museum agendas and
digitised archives. No French- or Italian-language counterpart of Basel-Stadt's dataset 100086 exists there.

## 3. The chosen source: Ticino

- **Candidate:** Gran Consiglio della Repubblica e Cantone Ticino. The lead department per object is assigned by the cantonal
  administration; the government's own Messaggio documents print it as «competenza». OPD carries it as contributors role
  `leading_department` («Federführung»), position 1. 1,213 affairs also have a second department at position 2; position 1
  is the lead. The Gran Consiglio's object pages were not opened (robots.txt, below).
- **Field values (2023-01-01…2026-10-11, n = 2,274):** DSS 407, DT 429, DFE 404, DI 363, DECS 305, Consiglio di Stato 132,
  Cancelleria 118, Gran Consiglio 116. The 5 departments are the cantonal structure in force over the whole window.
- **Join to OPD inputs:** by OPD affair id (`contributors.affair_id` = `inputs.id`). All 2,274 join, 2,267 have text.
- **Caveat found before any call:** a Messaggio's document header names the competent department («Messaggio numero data
  competenza … DIPARTIMENTO DELLE ISTITUZIONI»). 589 of 2,274 inputs name one of the six units (487 of 512 Messaggi). The
  pre-registered primary population therefore excludes inputs that name any unit: 1,685 items.
- **Licence:** OPD's export index (`index.json`) and landing page state no licence. The repository already uses OPD exports as
  source data (README «Licences»). The underlying labels are public administrative records of the Canton of Ticino. Ticino's
  own site was not fetched: robots.txt for www4.ti.ch disallows `/poteri/gc/ricerca-messaggi-e-atti/ricerca/`, so the
  object pages were not opened. The licence of the labels is therefore unconfirmed. The scheme file holds only the 6 unit
  names (public names of state bodies) and a none line.
- **Scheme file:** `src/querschnitt/schemes/ti-dipartimenti.yaml` (kind `named`, body TI).
