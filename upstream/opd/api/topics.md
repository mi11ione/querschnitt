# Resource: topics

Proposed API resources for the `topics`, `topic_schemes` and `topic_codes` tables
(`../migrations/0001_topics.up.sql`), written to match the existing `/v1/` endpoints: list and detail endpoints,
relation endpoints under `/v1/affairs/{id}/…`, `group_by` endpoints, and the shared query parameters (`offset`, `limit`,
`sort_by`, `fields`, `lang`, `lang_fallback`, `lang_format`, `hide_null`, `exclude_null`, `output_format`) with the
`data` and `meta` envelope. Response models are in `models.py` (Pydantic v2).

## Endpoints

| Endpoint | Returns |
|---|---|
| `GET /v1/topics/` | topic rows, filtered (below); current rows by default |
| `GET /v1/topics/{id}` | one row |
| `GET /v1/topics/group_by/code` | counts per code for the filters given, e.g. chapters of one parliament in 2026 |
| `GET /v1/topics/group_by/body_key` | counts per parliament for the filters given, e.g. where "Digitalisierung" comes up |
| `GET /v1/affairs/{id}/topics` | the current rows of one affair (relation endpoint; `history=true` adds closed rows) |
| `GET /v1/affairs/?expand=topics` | affairs with their topic rows; `topics_limit`, `topics_offset` as for other relations |
| `GET /v1/affairs/?topic=aps:1.7.2.` | affairs whose current rank-1 row has this code (proposal: a filter on the affairs list) |
| `GET /v1/topic_schemes/`, `GET /v1/topic_schemes/{id}` | schemes and versions, with licence and source |
| `GET /v1/topic_schemes/{id}/codes` | the codes of a scheme with labels and parent |

The write side (how a parliament's decision reaches the table) is not part of the public read API; see
`../MERGE_REQUEST.md` §5.

## Filters on `/v1/topics/`

| Parameter | Example | Meaning |
|---|---|---|
| `scheme` | `aps`, `adhoc/digitalisierung` | `scheme_key`; comma-separated for several |
| `code` | `aps:1.7.2.`, `1.7.2.`, `adhoc/digitalisierung:yes` | the code; the short form without the scheme prefix works when `scheme` is set. With `level=2` and a chapter code: the subtopics under that chapter (`parent_code`) |
| `level` | `1` | 1 = chapter or yes/no, 2 = subtopic |
| `rank` | `1` | default `1` (the label); `1,2,3` adds the ranked suggestions |
| `body` (= `body_key`) | `BE,FR,VS` | parliaments; both names accepted, `body_key` as on every other OPD resource |
| `affair_id` | `340560` | rows of these affairs |
| `status` | `suggested,confirmed` | default: `suggested,confirmed` (rejected rows only on request) |
| `provenance` | `inferred` | `inferred` = machine suggestion, `confirmed` = published decision |
| `lane` | `please_check` | `readings_agree` or `please_check` |
| `p_min` | `0.8` | recalibrated probability at least this |
| `since` | `2026-10-15T00:00:00` | rows opened or closed after this time (UTC): a client re-syncs without re-reading the whole export |
| `current` | `true` | default `true`; `false` includes closed versions (history) |
| `affair_lang` | `fr` | the language of the affair (its title), for one-language feeds |
| `date_from`, `date_to` | `2026-01-01` | the affair's `begin_date`, as on `/v1/affairs/` |
| `lang`, `lang_format`, `lang_fallback` | `lang=fr&lang_format=flat` | as everywhere in OPD: the language of the `label` field (`nested` by default: `{"de", "fr", "it", "rm"}`) |

`lang` keeps its OPD meaning (the language of the returned labels), so the affair-language filter is named `affair_lang`.
Querschnitt's own API (`docs/CONTRACT.md` §2) calls the same filters `body` and `lang`; the OPD names above take precedence.

`sort_by` accepts any column; default `-valid_from`. `fields` and `output_format=csv|excel` work as on other resources;
CSV and Excel carry the flat columns of the table (`label_de` … `evidence_quote`).

## Row

| Field | Machine suggestion (`provenance = inferred`) | Published decision (`provenance = confirmed`) |
|---|---|---|
| `scheme_key`, `level`, `code`, `parent_code`, `rank`, `label` | the model's choice among the scheme's codes | the decided code |
| `p` | recalibrated probability for rank 1 (isotonic, fitted per served build); `null` for ranks 2–3 | copied from the machine row it decides |
| `p_raw` | the model's probability | copied |
| `lane` | `readings_agree`: two independent readings gave the same top code; `please_check`: they differ | copied |
| `status` | always `suggested` | `confirmed` or `rejected` |
| `evidence` | one sentence of the affair; `quote` is an exact substring at `char_start`–`char_end` of `field` | copied |
| `generated_by` | `model`, `model_build`, `cutoffs_id`, `prompt_id`, `input_hash`, `engine_version` | copied from the machine row |
| `confirmed_by`, `confirmed_at`, `confirmed_by_body_id` | `null` | who decided and when; the body when the parliament itself published it |
| `valid_from`, `valid_to` | version interval; `valid_to = null` = current | same |

Generated and confirmed content are never mixed in one row, and a decision never overwrites a suggestion: it closes the
machine row (`valid_to`) and adds its own row.

## Example

`GET /v1/affairs/340560/topics?scheme=aps&level=1&rank=1,2,3` (rows from the Querschnitt test load; the 2025–26 slice)

```json
{
  "data": [
    {
      "id": 1,
      "affair_id": 340560,
      "body_id": 258,
      "body_key": "GL",
      "scheme_id": 1,
      "scheme_key": "aps",
      "level": 1,
      "code": "aps:1.6.3.",
      "parent_code": null,
      "rank": 1,
      "label": {"de": "Raumplanung und Wohnungswesen", "fr": "Aménagement du territoire et logement", "it": "Pianificazione del territorio e alloggio", "rm": null},
      "p": 0.2838,
      "p_raw": 0.8877,
      "lane": "please_check",
      "status": "suggested",
      "provenance": "inferred",
      "evidence": null,
      "generated_by": {
        "model": "swiss-ai/apertus-v1.5-8b",
        "model_build": "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840",
        "cutoffs_id": "aps@dd237840",
        "prompt_id": "a929a8ba0c83,62f1472bd737,331cb0454e98",
        "input_hash": "6cfbfe55ae7f340f",
        "engine_version": "0.6.0"
      },
      "valid_from": "2026-10-13T23:57:18",
      "valid_to": null,
      "confirmed_by": null,
      "confirmed_by_body_id": null,
      "confirmed_at": null,
      "created_at": "2026-10-14T00:26:41",
      "updated_at": "2026-10-14T00:26:41"
    }
  ],
  "meta": {
    "offset": 0, "limit": 100, "total_records": 3, "total_pages": 1, "current_page": 1, "has_more": false,
    "next_page": null, "prev_page": null,
    "first_page": "https://api.openparldata.ch/v1/affairs/340560/topics?offset=0&limit=100",
    "last_page": "https://api.openparldata.ch/v1/affairs/340560/topics?offset=0&limit=100",
    "self": "https://api.openparldata.ch/v1/affairs/340560/topics?offset=0&limit=100"
  }
}
```

(Ranks 2 and 3 omitted above; `total_records` counts them.) The same row with `lang=fr&lang_format=flat` has
`"label": "Aménagement du territoire et logement"`.

## Queries and indexes

| Query | Index (migration 0001) |
|---|---|
| `/v1/affairs/{id}/topics` | `topics_affair_current (affair_id, scheme_key, level, rank) WHERE valid_to IS NULL` |
| `/v1/topics/?scheme=&code=&status=&rank=` | `topics_code_current (scheme_key, code, rank, status) WHERE valid_to IS NULL` |
| `… &body_key=` | `topics_body_current (body_key, scheme_key, code) WHERE valid_to IS NULL` |
| `… &code=<chapter>&level=2` | `topics_parent_current (scheme_key, parent_code) WHERE valid_to IS NULL AND level = 2` |
| `?since=` | `topics_updated_at (updated_at)` |
| loader: latest machine row of a key | `topics_machine_key (affair_id, scheme_key, level, rank, valid_from) WHERE provenance = 'inferred'` |

`date_from` / `date_to` and `affair_lang` join `affairs` on `affairs.id`, which OPD already indexes by its primary key.
