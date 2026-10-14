"""S13 Neues Thema timing (PREREG-ADDENDA 2026-10-13 21:20). Three new topics, E6 prompt shape (de/fr/it), one yes/no call
(order a, yes=A) per census-week affair (items_cache date 2026-09-30..2026-10-06, in_window), exactly 3 workers, nocache=True.
Topics run one after another; per call: start/end timestamps, latency, http statuses, fp. Usage: python3 -I s13.py [topic_key]
-> raw/s13_<topic>.jsonl (one fresh run per topic; a topic file that already has 577 rows is skipped)."""
import json, math, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/lib')
import pai
S8 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s8-dvs'
sys.path.insert(0, S8)
from common import E6, FP_EXPECTED, MODEL
H = '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s13-timing'
TAG, TAG_CAP, TOTAL_CAP = 'bern2-s13-timing', 0.30, 0.60

# (question with parenthetical scope, yes answer) per language; item/labels/no/format taken from E6 unchanged
TOPICS = {
 'wolf': {
  'de': ("Betrifft das folgende parlamentarische Geschäft das Thema «Wolf und Grossraubtiere» (Wolf, Bär, Luchs, Goldschakal, "
         "Regulierung und Abschuss, Herdenschutz, Schäden an Nutztieren, Jagd- und Schutzstatus)?",
         "Ja, das Geschäft betrifft Wolf und Grossraubtiere"),
  'fr': ("L'objet parlementaire suivant concerne-t-il le thème « loup et grands prédateurs » (loup, ours, lynx, chacal doré, "
         "régulation et tirs, protection des troupeaux, dégâts aux animaux de rente, statut de chasse et de protection) ?",
         "Oui, l'objet concerne le loup et les grands prédateurs"),
  'it': ("Il seguente oggetto parlamentare riguarda il tema «lupo e grandi predatori» (lupo, orso, lince, sciacallo dorato, "
         "regolazione e abbattimenti, protezione delle greggi, danni agli animali da reddito, statuto di caccia e di protezione)?",
         "Sì, l'oggetto riguarda il lupo e i grandi predatori")},
 'hitze': {
  'de': ("Betrifft das folgende parlamentarische Geschäft das Thema «Hitzeschutz / Hitzewellen» (Hitzewellen, Hitzeaktionspläne, "
         "Schutz der Bevölkerung und der Arbeitnehmenden vor Hitze, städtische Hitzeinseln, Kühlung, Beschattung und Begrünung gegen Hitze)?",
         "Ja, das Geschäft betrifft Hitzeschutz / Hitzewellen"),
  'fr': ("L'objet parlementaire suivant concerne-t-il le thème « protection contre la chaleur / canicules » (canicules, plans canicule, "
         "protection de la population et des travailleurs contre la chaleur, îlots de chaleur urbains, rafraîchissement, ombrage et "
         "végétalisation contre la chaleur) ?",
         "Oui, l'objet concerne la protection contre la chaleur / les canicules"),
  'it': ("Il seguente oggetto parlamentare riguarda il tema «protezione dal caldo / ondate di calore» (ondate di calore, piani canicola, "
         "protezione della popolazione e dei lavoratori dal caldo, isole di calore urbane, raffrescamento, ombreggiamento e "
         "inverdimento contro il caldo)?",
         "Sì, l'oggetto riguarda la protezione dal caldo / le ondate di calore")},
 'ki_schule': {
  'de': ("Betrifft das folgende parlamentarische Geschäft das Thema «Künstliche Intelligenz an Schulen» (KI im Unterricht, KI-Werkzeuge "
         "wie ChatGPT für Schülerinnen, Schüler und Lehrpersonen, Prüfungen und Plagiate mit KI, KI-Kompetenzen im Lehrplan, "
         "Datenschutz beim KI-Einsatz in der Bildung)?",
         "Ja, das Geschäft betrifft Künstliche Intelligenz an Schulen"),
  'fr': ("L'objet parlementaire suivant concerne-t-il le thème « intelligence artificielle à l'école » (IA dans l'enseignement, outils "
         "d'IA comme ChatGPT pour les élèves et les enseignants, examens et plagiat avec l'IA, compétences en IA dans le plan d'études, "
         "protection des données lors de l'usage de l'IA dans la formation) ?",
         "Oui, l'objet concerne l'intelligence artificielle à l'école"),
  'it': ("Il seguente oggetto parlamentare riguarda il tema «intelligenza artificiale nelle scuole» (IA nell'insegnamento, strumenti "
         "di IA come ChatGPT per allievi e docenti, esami e plagio con l'IA, competenze di IA nel piano di studio, protezione dei dati "
         "nell'uso dell'IA nella formazione)?",
         "Sì, l'oggetto riguarda l'intelligenza artificiale nelle scuole")},
}


def items():
    it = json.load(open(f'{S8}/items_cache.json'))
    return [x for x in it if '2026-09-30' <= x['date'] <= '2026-10-06' and x['in_window']]


def build(topic, x):
    lang = x['lang']; q, yes = TOPICS[topic][lang]
    _q, item, ti, tl, _yes, no, fmt, key = E6[lang]
    title, tlong = x['title'], x['title_long']
    blk = f"{ti}: {title[:400]}" + (f"\n{tl}: {tlong[:400]}" if tlong and tlong != title else '')
    u = f"{q}\n\nA = {yes}\nB = {no}\n\n{item}:\n{blk}\n\n{fmt}"
    return u, '{"' + key + '": "'


STOP = threading.Event()


def one(topic, x, t_start):
    if STOP.is_set():
        return None
    u, pre = build(topic, x)
    t0 = time.time()
    ch, meta = pai.chat([{"role": "user", "content": u}, {"role": "assistant", "content": pre}], model=MODEL, max_tokens=1,
                        tag=TAG, tag_cap_usd=TAG_CAP, nocache=True, logprobs=True, top_logprobs=20,
                        continue_final_message=True, add_generation_prompt=False)
    t1 = time.time()
    fp = meta['resp'].get('system_fingerprint')
    if fp != FP_EXPECTED:
        STOP.set()
    d = pai.read_codes(ch, ['A', 'B']); pa, pb = math.exp(d.get('A', -50)), math.exp(d.get('B', -50))
    return dict(topic=topic, id=x['id'], level=x['level'], lang=x['lang'], p_yes=pa / (pa + pb), codes=d, t_req=t0, t_done=t1,
                t_rel=round(t1 - t_start, 3), latency=round(t1 - t0, 3), pai_secs=meta['secs'], http=meta['http'],
                served=meta['resp'].get('model'), fp=fp, pt=meta['prompt_tokens'], usd=meta['usd'], cached=meta['cached'])


def run(topic):
    X = items(); out = f'{H}/raw/s13_{topic}.jsonl'
    try:
        n_done = sum(1 for _ in open(out))
    except FileNotFoundError:
        n_done = 0
    if n_done >= len(X):
        print(topic, 'done already'); return
    assert n_done == 0, f'{out} partial ({n_done}); delete it to re-time cleanly'
    assert pai.spent(TAG) + pai.spent('bern2-s8b-text') < TOTAL_CAP - 0.05, 'total cap'
    t_start = time.time(); lock = threading.Lock()
    with open(f'{H}/raw/s13_runs.jsonl', 'a') as f:
        f.write(json.dumps(dict(topic=topic, event='start', t=t_start, n=len(X), workers=3)) + '\n')
    with ThreadPoolExecutor(3) as ex, open(out, 'a') as f:
        futs = [ex.submit(one, topic, x, t_start) for x in X]
        for fu in as_completed(futs):
            r = fu.result()
            if r is None:
                continue
            with lock:
                f.write(json.dumps(r) + '\n'); f.flush()
            if r['fp'] != FP_EXPECTED:
                print('FINGERPRINT MISMATCH', r['fp']); break
    t_end = time.time()
    with open(f'{H}/raw/s13_runs.jsonl', 'a') as f:
        f.write(json.dumps(dict(topic=topic, event='end', t=t_end, wall=round(t_end - t_start, 3))) + '\n')
    print(topic, 'wall', round(t_end - t_start, 1))
    if STOP.is_set():
        raise SystemExit('stopped (fp or cap)')


if __name__ == '__main__':
    for t in (sys.argv[1:] or list(TOPICS)):
        run(t)
