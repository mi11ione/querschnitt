# Annotation guide: APS chapters for cantonal and municipal affairs

You get 160 parliamentary affairs from Swiss cantonal and municipal parliaments (2015 or later), in German, French or
Italian. For each affair, choose the **single best chapter** of the Année Politique Suisse (APS) scheme below, or
`0` for "no policy topic". You may add **one optional second chapter** if the affair clearly also belongs there.

## Input
`items.txt` has one block per affair: an opaque id (`C001` …), the parliament, the affair type and the text, exactly
as the model saw it: title, long title (if any), and for most affairs the first 1,500 characters of a document
(often the executive's reply, which usually restates the question). Some affairs are title-only. Judge only from this
text; do not look anything up. The ids are shuffled and say nothing about the affair.

## Output
Copy `ann_TEMPLATE.tsv` to `ann_A.tsv` (first annotator) or `ann_B.tsv` (second annotator) and save it in the s6 folder
(`.../spikes/s6-cantonal/`), one line per id, tab-separated:

```
<id>\t<first chapter code>\t<optional second chapter code>
C001\t1.6.2.\t
C002\t1.4.1.\t1.6.3.
C003\t0\t
```

Write the codes exactly as in the table, including the trailing dot. Leave the third column empty if there is no second chapter.
Work independently: do not compare answers with the other annotator, and do not look at `key.jsonl`.

## Rules
1. Code the **policy substance**, not the instrument (motion, question, report) or the institution answering.
2. Local matters map to the national chapter of the same substance: a municipal school building goes to *Bildung und Forschung*
   (`1.8.1.`) if the issue is schooling, to *Raumplanung und Wohnungswesen* (`1.6.3.`) if it is zoning or construction law, and to
   *Öffentliche Finanzen* (`1.5.`) only if the issue is the budget or the credit as such.
3. Cantonal and municipal finance, budgets, taxes and fiscal equalisation go to `1.5.` (subtopic *Finanzhaushalt der Kantone und
   Gemeinden*, *Direkte Steuern*, …).
4. *Föderativer Aufbau* (`1.1.4.`) covers relations between Confederation, cantons and municipalities, mergers of municipalities,
   and municipal autonomy; *Institutionen und Volksrechte* (`1.1.3.`) covers the parliament, government, administration and
   popular rights of the canton or municipality itself.
5. Use `0` only for affairs with no policy topic: elections or appointments of persons, naturalisations, resignations,
   pure council procedure.
6. If two chapters fit equally well, put the one the text spends more words on first.

## The 24 APS chapters (with their APS subtopics)
| Code | Chapter | Subtopics |
|---|---|---|
| `1.1.1.` | **Politische Grundfragen** | Verfassungsfragen; Nationale Identität; Landes- und Weltausstellungen; Staatsjubiläen; Image der Schweiz im Ausland; Stimmung in der Bevölkerung |
| `1.1.2.` | **Rechtsordnung** | Bürgerrecht; Niederlassungsrecht; Stimm- und Wahlrecht; Datenschutz und Statistik; Grundrechte; Öffentliche Ordnung; Innere Sicherheit; Kriminalität; Polizei; Äussere Sicherheit; Rechtshilfe; Strafrecht; Privatrecht |
| `1.1.3.` | **Institutionen und Volksrechte** | Bundesrat; Regierungspolitik; Bundesverwaltung - Organisation; Bundesverwaltung - Personal; Parlamentsmandat; Parlamentsorganisation; Organisation der Bundesrechtspflege; Volksrechte; Wahl- und Abstimmungsverfahren |
| `1.1.4.` | **Föderativer Aufbau** | Beziehungen zwischen Bund und Kantonen; Interkantonale Zusammenarbeit; Städte, Regionen, Gemeinden; Territorialfragen; Jurafrage |
| `1.1.5.` | **Wahlen** | Wahlen in kantonale Parlamente; Wahlen in kantonale Regierungen; Kantonale Ersatzwahlen; Kommunale Wahlen; Kommunale Ersatzwahlen; Eidgenössische Wahlen; Ständeratsersatzwahlen |
| `1.2.` | **Aussenpolitik** | Beziehungen zur EU; Beziehungen zu internationalen Organisationen; Zwischenstaatliche Beziehungen; Gute Dienste; Auslandschweizer; Entwicklungspolitik; Aussenwirtschaftspolitik |
| `1.3.` | **Landesverteidigung** | Landesverteidigung und Gesellschaft; Militäreinsätze; Militärorganisation; Ausrüstung und Beschaffung; Zivildienst und Dienstverweigerung; Bevölkerungsschutz |
| `1.4.1.` | **Wirtschaftspolitik** | Konjunkturlage- und politik; Strukturpolitik; Wettbewerb; Gesellschaftsrecht; Wirtschaftsordnung |
| `1.4.2.` | **Geld, Währung und Kredit** | Finanzmarkt; Geldpolitik; Makroprudenzielle Regulierung; Nationalbank; Internationale Finanzinstitutionen; Wettbewerbsfähigkeit; Banken; Börsen; Versicherungen; Kapitalmarkt |
| `1.4.3.` | **Landwirtschaft** | Agrarpolitik; Internationale Landwirtschaftspolitik; Landwirt (Beruf); Landwirtschaft und Umweltschutz; Agrarprodukte; Tierische Produktion; Pflanzliche Produktion; Lebensmittel; Tierhaltung, -versuche und -schutz; Forstwirtschaft; Fischerei; Jagd |
| `1.5.` | **Öffentliche Finanzen** | Direkte Steuern; Indirekte Steuern; Finanz- und Ausgabenordnung; Finanzplan und Sanierungsmassnahmen; Staatsrechnung; Voranschlag; Finanzausgleich; Finanzhaushalt der Kantone und Gemeinden |
| `1.6.1.` | **Energie** | Energiepolitik; Netz und Vertrieb; Wasserkraft; Kernenergie; Alternativenergien; Erdöl und Erdgas |
| `1.6.2.` | **Verkehr und Kommunikation** | Verkehrspolitik; Strassenverkehr; Eisenbahn; Agglomerationsverkehr, öffentlicher Verkehr; Schiffahrt; Luftfahrt; Post und Telekommunikation |
| `1.6.3.` | **Raumplanung und Wohnungswesen** | Mietwesen; Raumplanung; Bodenrecht; Wohnungsbau und -eigentum; Wohnqualität |
| `1.6.4.` | **Umweltschutz** | Naturschutz; Naturgefahren; Gewässerschutz; Luftreinhaltung; Lärmschutz; Bodenschutz; Allgemeiner Umweltschutz; Klimapolitik; Abfälle |
| `1.7.1.` | **Bevölkerung und Arbeit** | Bevölkerungsentwicklung; Arbeitsmarkt; Löhne; Arbeitszeit; Kollektive Arbeitsbeziehungen; Arbeitnehmerschutz; Arbeitsrecht |
| `1.7.2.` | **Gesundheit, Sozialhilfe, Sport** | Gesundheitspolitik; Ärzte und Pflegepersonal; Medikamente; Epidemien; Medizinische Forschung; Suchtmittel; Sozialhilfe; Sport |
| `1.7.3.` | **Sozialversicherungen** | Alters- und Hinterlassenenversicherung (AHV); Invalidenversicherung (IV); Ergänzungsleistungen (EL); Erwerbsersatzordnung (EO); Berufliche Vorsorge; Private Vorsorge; Krankenversicherung; Unfallversicherung; Arbeitslosenversicherung (ALV) |
| `1.7.4.` | **Soziale Gruppen** | Migrationspolitik; Asylpolitik; Familienpolitik; Frauen und Gleichstellungspolitik; Kinder- und Jugendpolitik; Alterspolitik; Menschen mit Behinderungen; LGBTQIA+ |
| `1.8.1.` | **Bildung und Forschung** | Grundschulen; Mittelschulen; Berufsbildung; Hochschulen; Forschung |
| `1.8.2.` | **Kultur, Sprache, Kirchen** | Kulturpolitik; Urheberrecht; Heimatschutz und Denkmalpflege; Archive, Bibliotheken, Museen; Buchmarkt; Musik; Film; Sprachen; Fahrende; Kirchen und religionspolitische Fragen |
| `1.8.3.` | **Medien** | Radio und Fernsehen; Presse; Medienpolitische Grundfragen; Telekommunikation; Neue Medien; Meinungsforschung |
| `2.0.1.` | **Parteien** | Parteiensystem; Grosse Parteien; Linke und ökologische Parteien; Liberale Parteien; Konservative und Rechte Parteien; Andere Parteien |
| `2.0.2.` | **Verbände** | Industrie, Handel und Unternehmer; Arbeitgeber; Landwirtschaft; Gewerbe, Dienstleistungen, Konsum; Arbeitnehmer, Gewerkschaften; Gesundheit; Sozialwesen, Soziale Gruppen; Raumplanung und Wohnungswesen; Verkehr; Energie; Natur und Umwelt; Bildung; Kultur, Medien und Sprachen; Kirche, Religion; Freizeit, Tourismus, Gastgewerbe; Überparteiliche politische Interessen / Think Tanks |
| `0` | **Kein Sachthema** | Wahl oder Ernennung von Personen, Einbürgerung, Rücktritt, Verfahrensfragen des Rats |
