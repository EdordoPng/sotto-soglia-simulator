# Il Patto del Bosco Simulator

Simulatore statistico in Python per il gioco di carte **Il Patto del Bosco**, evoluzione del precedente progetto **Sotto Soglia**.

Il progetto nasce come supporto tecnico al bilanciamento del regolamento del gioco, sviluppato per l'esame di **Generative Artificial Intelligence**.  
L'obiettivo non è creare una GUI o un videogioco, ma uno strumento riproducibile per simulare migliaia di partite, confrontare strategie e valutare l'impatto delle regole.

Il nome del package Python resta `sotto_soglia` per compatibilità storica con il codice e i test già esistenti.

---

## Scopo del progetto

Il simulatore permette di analizzare:

- durata media delle partite;
- numero medio di round;
- frequenza degli Abbandoni del Patto per esaurimento Scorte;
- frequenza degli Abbandoni del Patto per troppe carte Affamato;
- frequenza dei pareggi;
- impatto degli effetti animale;
- impatto del Mazzo Affamato;
- differenze tra partite a 2, 3 e 4 giocatori;
- forza relativa delle strategie automatiche;
- configurazioni di gioco più bilanciate;
- decisioni delle strategie tramite telemetry dedicata;
- eventi degli effetti animale tramite export dedicato.

Il criterio principale usato per il bilanciamento è:

> rendere il più possibile rilevanti entrambe le condizioni di uscita dal gioco: esaurire le Scorte e accumulare troppe carte Affamato.

---

## Terminologia

La versione v0.5 usa la nuova terminologia di **Il Patto del Bosco**.

| Termine legacy / codice | Termine di gioco v0.5 |
|---|---|
| vite / `lives` | Scorte |
| Ferite Critiche / `critical_wounds` | carte Affamato |
| Mazzo Ferita Critica | Mazzo Affamato |
| eliminazione | Abbandono del Patto |
| effetti colore | effetti animale |
| colore tecnico | animale / cibo preferito |

I nomi interni del codice (`lives`, `critical_wounds`, `Color.BLUE`, ecc.) sono mantenuti per retrocompatibilità tecnica.

---

## Animali, colori tecnici e colori display

Nel codice restano quattro colori tecnici. Nella versione v0.5 questi colori corrispondono agli animali.

| Colore tecnico | Animale | Cibo preferito | Colore display |
|---|---|---|---|
| `BLUE` | Panda | Bambù | `green` |
| `RED` | Coniglio | Carote | `orange` |
| `GREEN` | Scimmia | Banane | `yellow` |
| `YELLOW` | Scoiattolo | Ghiande | `brown` |

Il colore tecnico è usato dal simulatore.  
Il colore display serve per export, analisi e materiali fisici del gioco.

---

## Stato attuale

Il progetto è in stato funzionante per la versione v0.5.

Sono implementati:

- motore completo del round;
- motore completo della partita;
- Abbandono per Scorte a 0;
- Abbandono per soglia Affamato;
- spareggi finali;
- strategie automatiche;
- simulazioni multiple;
- statistiche aggregate;
- esportazione CSV/JSON;
- tournament controbilanciato tra strategie;
- simulazioni parametriche;
- generazione di grafici;
- effetti animale v0.5;
- Mazzo Affamato v0.5;
- lineup animale esplicita tramite CLI;
- telemetry degli effetti animale;
- telemetry delle decisioni strategiche.

---

## Configurazione consigliata v0.5

Dopo simulazioni parametriche e contro-test sulle lineup, i preset v0.5 consigliati sono:

| Numero giocatori | Scorte iniziali | Soglia Abbandono per Affamato | Carte per giocatore | Effetti animale | Mazzo Affamato | Effetti colore legacy |
|---:|---:|---:|---:|:---:|:---:|:---:|
| 2 giocatori | 12 | 6 | 3 | ON | ON | OFF |
| 3 giocatori | 15 | 5 | 3 | ON | ON | OFF |
| 4 giocatori | 21 | 5 | 3 | ON | ON | OFF |

Questi valori sono stati scelti per mantenere il più possibile bilanciate le due cause di Abbandono:

- terminare tutte le Scorte;
- accumulare troppe carte Affamato.

Nota di bilanciamento: il Panda resta da monitorare nelle partite a 2 giocatori, soprattutto contro il Coniglio. Le configurazioni a 3 e 4 giocatori risultano più stabili.

---

## Configurazione legacy

La configurazione storica resta supportata internamente per compatibilità, ma non è il riferimento v0.5.

`GameConfig()` legacy mantiene:

```text
initial_lives = 18
critical_wounds_limit = 3
color_effects_enabled = True
animal_card_effects_enabled = False
critical_card_effects_enabled = False
critical_deck_profile_id = "legacy"
```

I vecchi preset legacy erano:

```text
2 giocatori: 12 vite / 5 Ferite Critiche / effetti colore ON
3 giocatori: 17 vite / 4 Ferite Critiche / effetti colore ON
4 giocatori: 24 vite / 4 Ferite Critiche / effetti colore ON
```

La v0.5 usa invece Scorte, Affamato, effetti animale e Mazzo Affamato.

---

## Effetti animale v0.5

Gli effetti animale si attivano solo quando il giocatore usa una carta del proprio animale.

### Panda

| Carta | Nome | Effetto sintetico |
|---:|---|---|
| 1 | Riposo Forzato | programma un recupero di Scorte se l'effetto si applica |
| 3 | Respiro Lento | se il Panda ha già almeno 2 carte Affamato, il consumo di questa carta diventa 2; altrimenti resta 3 |
| 5 | Grande Letargo | programma per il round successivo un confronto stabilizzato a 3 |

### Coniglio

| Carta | Nome | Effetto sintetico |
|---:|---|---|
| 1 | Scatto Improvviso | valore di confronto 2 e consumo 1 |
| 2 | Passo Leggero | se non riceve Affamato, il consumo diventa 1 |
| 4 | Grande Balzo | nel round corrente consuma 0; nel round successivo paga il triplo del consumo della carta scelta, anche se riceve Affamato |

Dettaglio Grande Balzo:

- nel round in cui viene giocato, il consumo è 0;
- viene programmato un debito per il round successivo;
- nel round successivo il consumo effettivo della carta scelta viene triplicato;
- il debito si applica anche se il Coniglio riceve Affamato;
- se il Coniglio gioca di nuovo Grande Balzo sotto debito, paga comunque il debito precedente e programma il nuovo.

### Scimmia

| Carta | Nome | Effetto sintetico |
|---:|---|---|
| 1 | Finta Innocente | può evitare l'assegnazione di Affamato se un altro giocatore ha giocato un 1 stampato |
| 2 | Buccia di Banana | riduce il valore di confronto di un bersaglio valido |
| 5 | Banana Rubata | programma un consumo extra su un bersaglio e può generare recupero per la Scimmia |

### Scoiattolo

| Carta | Nome | Effetto sintetico |
|---:|---|---|
| 1 | Ghianda Nascosta | prepara un beneficio per il round successivo |
| 3 | Piccola Riserva | programma un recupero di Scorte se lo Scoiattolo non riceve Affamato |
| 4 | Dispensa Ordinata | aumenta la mano del prossimo round, entro il limite massimo |

---

## Mazzo Affamato v0.5

Il profilo `v05_hunger` contiene 18 carte:

| Carta Affamato | Copie |
|---|---:|
| `briciola_nascosta` | 3 |
| `razione_risparmiata` | 3 |
| `fiuto_da_dispensa` | 3 |
| `pancia_brontolante` | 3 |
| `morso_della_fame` | 3 |
| `respiro_calmo` | 3 |

Il mazzo viene tracciato negli export tramite:

```text
critical_deck_orders.csv
critical_card_stats.csv
critical_events.csv
```

---

## Strategie disponibili

Il simulatore include strategie legacy e strategie v0.5.

| Nome CLI | Descrizione |
|---|---|
| `random` | sceglie casualmente una carta dalla mano |
| `prudent` | tende a scegliere carte basse per ridurre il consumo |
| `defensive` | strategia legacy legata agli effetti colore |
| `aggressive` | strategia legacy legata agli effetti colore avversari |
| `anti_critical` | evita carte troppo basse per ridurre il rischio Affamato/Ferita Critica |
| `mixed` | bilancia criteri legacy |
| `adaptive_pressure` | strategia euristica legacy avanzata |
| `critical_adaptive` | strategia sperimentale legacy consapevole delle carte critiche |
| `v05_basic` | baseline v0.5 semplice, basata su confronto e consumo effettivi |
| `v05_balanced` | baseline v0.5 più prudente sulle Scorte |
| `v05_animal_aware` | strategia v0.5 consapevole degli animali e di effetti come il debito di Grande Balzo |

La strategia consigliata per le analisi v0.5 è:

```text
v05_animal_aware
```

`v05_basic`, `v05_balanced` e `v05_animal_aware` generano anche telemetry in `strategy_decision_events.csv`.

---

## Installazione

Da PowerShell, nella cartella del progetto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Prima di eseguire test o comandi CLI:

```powershell
$env:PYTHONPATH = "src"
```

---

## Test automatici

Per eseguire tutti i test:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m pytest
```

I test coprono:

- costruzione del mazzo;
- risoluzione del round;
- consumo di Scorte;
- assegnazione Affamato;
- effetti animale;
- Mazzo Affamato;
- eliminazioni / Abbandono del Patto;
- spareggi;
- strategie;
- simulazioni multiple;
- export CSV/JSON;
- tournament controbilanciato;
- simulazioni parametriche;
- generazione dei grafici;
- telemetry degli effetti e delle decisioni.

---

## Uso base del simulatore

Eseguire una simulazione semplice con preset v0.5 default:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --strategy v05_animal_aware
```

Eseguire una simulazione con export:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --strategy v05_animal_aware --export --output-dir results/example_v05
```

Eseguire una simulazione con strategie diverse per giocatore:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --strategies v05_animal_aware v05_balanced v05_basic random
```

---

## Flag CLI principali

| Flag | Descrizione |
|---|---|
| `--players` | numero giocatori: 2, 3 o 4 |
| `--games` | numero di partite da simulare |
| `--seed` | seed base per riproducibilità |
| `--strategy` | strategia comune per tutti i giocatori |
| `--strategies` | strategie diverse per giocatore |
| `--export` | abilita export CSV/JSON |
| `--output-dir` | cartella di destinazione degli export |
| `--initial-lives` | override delle Scorte iniziali |
| `--critical-wounds-max` | override della soglia Affamato |
| `--animal-card-effects auto\|on\|off` | controllo effetti animale |
| `--critical-card-effects auto\|on\|off` | controllo effetti Mazzo Affamato / critici |
| `--color-effects on\|off\|both` | controllo effetti colore legacy o griglia parametrica |
| `--animal-lineup` | seleziona esplicitamente gli animali in partita |
| `--parametric` | abilita simulazione parametrica |
| `--lives-values` | valori di Scorte iniziali da testare in parametric |
| `--critical-wounds-values` | soglie Affamato da testare in parametric |

---

## Lineup animale esplicita

Il flag `--animal-lineup` permette di scegliere gli animali in partita.

Esempio 2 giocatori:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 2 --games 10000 --seed 42 --strategy v05_animal_aware --animal-lineup Panda Scoiattolo --export --output-dir results/panda_scoiattolo_2p
```

Esempio 3 giocatori:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 3 --games 10000 --seed 42 --strategy v05_animal_aware --animal-lineup Coniglio Scimmia Scoiattolo --export --output-dir results/coniglio_scimmia_scoiattolo_3p
```

Regole:

- il numero di animali deve coincidere con `--players`;
- animali ammessi: `Panda`, `Coniglio`, `Scimmia`, `Scoiattolo`;
- non sono ammessi duplicati;
- l'ordine indicato determina l'ordine dei giocatori.

Senza `--animal-lineup`, la lineup default è:

```text
2P: Panda, Coniglio
3P: Panda, Coniglio, Scimmia
4P: Panda, Coniglio, Scimmia, Scoiattolo
```

Nota export: `simulation_config.json` mostra `animal_lineup: []` quando la lineup è implicita/default. Se la lineup è specificata esplicitamente, viene esportata.

---

## Export CSV/JSON

Aggiungendo `--export`, il simulatore crea file nella cartella indicata da `--output-dir`.

Esempio:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --strategy v05_animal_aware --export --output-dir results/example_run
```

File standard generati:

```text
simulation_config.json
aggregate_stats.json
games_summary.csv
rounds_summary.csv
critical_events.csv
critical_deck_orders.csv
critical_card_stats.csv
animal_effect_events.csv
strategy_decision_events.csv
```

I CSV usano il delimitatore `;`, così sono leggibili correttamente da Excel in italiano/Windows.

### `simulation_config.json`

Contiene la configurazione della simulazione:

- numero giocatori;
- numero partite;
- seed;
- Scorte iniziali;
- soglia Affamato;
- effetti attivi;
- profilo Mazzo Affamato;
- carte per giocatore;
- file generati.

### `aggregate_stats.json`

Contiene le statistiche aggregate:

- round medi;
- pareggi;
- Abbandoni per Scorte;
- Abbandoni per Affamato;
- win rate per player;
- win rate per colore tecnico;
- win rate per animale;
- win rate per colore display;
- stato medio dei vincitori.

### `games_summary.csv`

Una riga per partita, con vincitori, durata, strategie, cause di Abbandono e riepilogo.

### `rounds_summary.csv`

Una riga per round, con carte giocate, consumo, Affamato, Abbandoni e stato del round.

### `critical_deck_orders.csv`

Ordine del Mazzo Affamato per ogni partita.

### `critical_card_stats.csv`

Statistiche aggregate sulle carte Affamato.

### `critical_events.csv`

Eventi legati al Mazzo Affamato.

### `animal_effect_events.csv`

Telemetry degli effetti animale.

Campi principali:

```text
game_index
round_number
player_id
animal
card_color
card_display_color
card_value
effect_id
effect_name
timing
status
target_player_id
value_before
value_after
amount
actual_amount
reason
```

Esempi di `effect_id`:

```text
panda_respiro_lento
coniglio_passo_leggero
coniglio_grande_balzo
scimmia_buccia_di_banana
scoiattolo_dispensa_ordinata
```

### `strategy_decision_events.csv`

Telemetry delle decisioni strategiche.

Una riga per ogni carta candidata valutata dalla strategia.

Campi principali:

```text
game_index
round_number
player_id
technical_color
animal
display_color
strategy_name
lives
critical_wounds
critical_wounds_limit
alive_players_count
candidate_card_color
candidate_card_display_color
candidate_card_animal
candidate_card_value
effective_comparison
effective_consumption
score
chosen
choice_rank
reason_flags
```

`random` e alcune strategie legacy possono produrre il file solo con header, perché non implementano `evaluate_candidates`.

---

## Tournament controbilanciato tra strategie

Il tournament serve a confrontare strategie evitando che una strategia sia sempre legata allo stesso colore o posizione.

Esempio:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --tournament-strategies v05_animal_aware v05_balanced v05_basic random --export --output-dir results/tournament_v05
```

Con 4 strategie vengono generate tutte le permutazioni:

```text
4! = 24 lineup
```

Se `--games 10000`, il totale è:

```text
24 × 10000 = 240000 partite
```

File esportati:

```text
strategy_tournament_stats.json
strategy_tournament_lineups.csv
```

---

## Simulazioni parametriche

Le simulazioni parametriche permettono di confrontare diverse configurazioni di Scorte iniziali e soglia Affamato.

Esempio v0.5:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --parametric --strategy v05_animal_aware --lives-values 16 18 20 21 22 24 --critical-wounds-values 4 5 6 --color-effects off --animal-card-effects on --critical-card-effects on --export --output-dir results/parametric_v05_4p
```

File esportati:

```text
parametric_stats.json
parametric_summary.csv
```

Per simulazioni v0.5 usare:

```text
--color-effects off
--animal-card-effects on
--critical-card-effects on
```

`--lives-values` corrisponde alle Scorte iniziali.  
`--critical-wounds-values` corrisponde alla soglia Affamato.

---

## Comandi di riferimento v0.5

### Smoke default preset

```powershell
$env:PYTHONPATH = "src"

.\.venv\Scripts\python.exe run_simulation.py --players 2 --games 100 --seed 42 --strategy v05_animal_aware --export --output-dir results/v05_smoke_2p

.\.venv\Scripts\python.exe run_simulation.py --players 3 --games 100 --seed 42 --strategy v05_animal_aware --export --output-dir results/v05_smoke_3p

.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 100 --seed 42 --strategy v05_animal_aware --export --output-dir results/v05_smoke_4p
```

### Validazione 4 giocatori

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --strategy v05_animal_aware --initial-lives 21 --critical-wounds-max 5 --animal-lineup Panda Coniglio Scimmia Scoiattolo --color-effects off --animal-card-effects on --critical-card-effects on --export --output-dir results/v05_4p_all_animals_21_5
```

### Test coppie 2 giocatori

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 2 --games 10000 --seed 42 --strategy v05_animal_aware --initial-lives 12 --critical-wounds-max 6 --animal-lineup Panda Coniglio --color-effects off --animal-card-effects on --critical-card-effects on --export --output-dir results/v05_2p_panda_coniglio_12_6
```

### Test terne 3 giocatori

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 3 --games 10000 --seed 42 --strategy v05_animal_aware --initial-lives 15 --critical-wounds-max 5 --animal-lineup Panda Coniglio Scimmia --color-effects off --animal-card-effects on --critical-card-effects on --export --output-dir results/v05_3p_panda_coniglio_scimmia_15_5
```

---

## Grafici generati

Per ogni simulazione parametrica possono essere generati:

```text
average_rounds_by_config.png
draw_rate_by_config.png
eliminations_by_config.png
winner_status_by_config.png
color_effects_comparison.png
```

Il grafico più importante per il bilanciamento è:

```text
eliminations_by_config.png
```

Questo grafico confronta:

- Abbandoni per esaurimento Scorte;
- Abbandoni per troppe carte Affamato.

La configurazione più bilanciata è quella in cui le due barre sono più vicine.

---

## Interpretazione attuale

Le simulazioni hanno confermato che non è ideale usare un unico valore fisso di Scorte e soglia Affamato per ogni numero di giocatori.

Il setup consigliato cambia in base al numero di partecipanti:

```text
2 giocatori: 12 Scorte / soglia 6 Affamato
3 giocatori: 15 Scorte / soglia 5 Affamato
4 giocatori: 21 Scorte / soglia 5 Affamato
```

Questa scelta mantiene rilevanti entrambe le meccaniche principali:

```text
- sopravvivenza tramite Scorte;
- rischio di Abbandono per Affamato.
```

Nota di tuning: Panda resta leggermente forte in alcune coppie a 2 giocatori. Non è considerato bloccante, ma resta un punto da monitorare in future iterazioni.

---

## Project structure

```text
sotto-soglia-simulator/
├── docs/
│   ├── regolamento_sotto_soglia_v0_2.md
│   ├── simulation_design.md
│   ├── metrics.md
│   └── prompts_used.md
│
├── data/
│   ├── raw/
│   └── processed/
│
├── results/
│   └── output CSV, JSON e grafici generati localmente
│
├── src/
│   └── sotto_soglia/
│       ├── __init__.py
│       ├── animal_effects.py
│       ├── cli.py
│       ├── config.py
│       ├── critical.py
│       ├── deck.py
│       ├── exporters.py
│       ├── game.py
│       ├── models.py
│       ├── parametric.py
│       ├── plots.py
│       ├── round.py
│       ├── rules.py
│       ├── simulation.py
│       ├── statistics.py
│       ├── strategies.py
│       └── tournament.py
│
├── tests/
│   └── test automatici
│
├── run_simulation.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Dipendenze

Le dipendenze principali sono:

```text
pytest
matplotlib
```

`pytest` serve per i test automatici.  
`matplotlib` serve per generare i grafici del report.

---

## Note sui file generati

La cartella `results/` contiene output generati localmente:

- CSV;
- JSON;
- immagini PNG.

Questi file sono pensati per analisi e report, ma non devono necessariamente essere versionati nel repository.

---

## Collegamento con il report tecnico

I risultati del simulatore possono essere usati nel report tecnico per mostrare:

1. come è stato validato il bilanciamento del gioco;
2. perché la configurazione finale cambia in base al numero di giocatori;
3. come le strategie automatiche hanno supportato il playtesting;
4. come i dati hanno guidato le iterazioni del regolamento;
5. come l'uso di strumenti GenAI ha supportato progettazione, sviluppo e analisi;
6. come la telemetry degli effetti e delle decisioni rende tracciabili le scelte di bilanciamento.
