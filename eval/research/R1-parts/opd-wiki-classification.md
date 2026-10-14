## Automated Subject Classification

In addition to a fulltext search covering metadata and indexed documents, a language independent subject classification should be offered. In an Innosuisse-funded preliminary study, POLITmonitor and the BFH Institute for Public Sector Transformation examined the extent to which predefined or ad hoc topics (like Covid 19) can be derived using machine learning ([Mathoshi 2023](https://docs.fenceit.cloud/s/WqEaRJJEJ5Kb86Y)).

In light of the initial findings, it seems fitting to apply a two-tier classification system, like [the one](https://docs.fenceit.cloud/s/yYp4Kz8jmwE6pL7) developed and utilized by [année politque suisse](https://anneepolitique.swiss/) (APS).

The need for automatic classification is currently emerging in various places:

* The national parliament was looking for a [solution](https://www.bk.admin.ch/dam/bk/de/dokumente/dti/themen/veranstaltungen/Innovation_Challenge_DTI-SI.pdf.download.pdf/Innovation_Challenge_DTI-SI.pdf) as part of the fist [GovTech Innovation Fair 2023](https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.msg-id-96479.html). A prototype was set up by the [BFH](https://www.bfh.ch/de/forschung/forschungsprojekte/2024-265-557-050/) -\> [Project on Hugginface](https://huggingface.co/spaces/rcds/SwissParlTopicModelling)
* The [politmonitor.bs.ch](https://politmonitor.bs.ch/home) uses a clustering by topics.
* The City Parliament of St. Gallen conducted a [challenge on topic extraction](https://hack.opendata.ch/project/1076) during the Open Data Hack St.Gallen 2023.
* In Zurich, a [pilot project](https://www.zh.ch/de/news-uebersicht/mitteilungen/2023/politik-staat/statistik/ki-pilotprojekt.html) was conducted to utilize AI-generated suggestions for allocating new submissions in the cantonal parliament to administrative units of the cantonal government.
* The Digital Administration Switzerland publishes [a list](https://www.digitale-verwaltung-schweiz.ch/aktuelles/politische-geschaefte) with national and cantonal affairs related to digitalization. This list is generate from POLITmonitor, where the subject "digitalization" is added manually to an affair.
* Demokratis.ch - [Classification for consultations](https://github.com/Demokratis-ch/demokratis-ml/) / [Parsing Legislative Consultation PDFs Using LlamaParse](https://medium.com/@thiloweber/parsing-legislative-consultation-pdfs-using-llamaparse-fdd4627b9094)
* SDSC/[DemocraSci](https://zenodo.org/records/13920293) trained a topic classification algo on the APS data. It works sufficiently according to Luis Salamanca.

In order to save resources and enable standardised clustering across several parliaments, an open service should be created that on a given input (documents of political affairs) can provide standardized or ad hoc generated subjects.
{'last_commit_sha': '82a9b467724a139a86bf57f4c88791887db54c6d', 'persisted': True, 'title': 'Classification', 'format': 'markdown', 'uploads_path': 'https://gitlab.com/api/v4/groups/69616287/wikis/attachments', 'slug': 'Home/Future-Topics/Classification', 'path': '/groups/opendata.ch/openparldatach/-/wikis/Home/Future-Topics/Classification', 'wiki_path': '/groups/opendata.ch/openparldatach/-/wikis/home', 'help_path': '/help/user/project/wiki/_index.md', 'markdown_help_path': '/help/user/markdown.md', 'markdown_preview_path': '/groups/opendata.ch/openparldatach/-/wikis/Home/Future-Topics/Classification/preview_markdown', 'create_path': '/groups/opendata.ch/openparldatach/-/wikis', 'container_full_path': 'opendata.ch/openparldatach'}
