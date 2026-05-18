# Sotto Soglia Simulator

Simulatore statistico in Python per il gioco di carte originale **Sotto Soglia**.

Il progetto nasce come supporto tecnico al bilanciamento del regolamento del gioco, sviluppato per l'esame di **Generative Artificial Intelligence**.  
L'obiettivo non è creare una GUI o un videogioco, ma uno strumento riproducibile per simulare migliaia di partite, confrontare strategie e valutare l'impatto delle regole.

---

## Scopo del progetto

Il simulatore permette di analizzare:

- durata media delle partite;
- numero medio di round;
- frequenza delle eliminazioni per vite;
- frequenza delle eliminazioni per Ferite Critiche;
- frequenza dei pareggi;
- impatto degli effetti colore;
- differenze tra partite a 2, 3 e 4 giocatori;
- forza relativa delle strategie automatiche;
- configurazioni di gioco più bilanciate.

Il criterio principale usato per il bilanciamento è stato:

> rendere il più possibile rilevanti entrambe le condizioni di eliminazione: perdita di tutte le vite e accumulo di Ferite Critiche.

---

## Stato attuale

Il progetto è ora in uno stato funzionante.

Sono implementati:

- motore completo del round;
- motore completo della partita;
- eliminazioni per vite e Ferite Critiche;
- spareggi finali;
- strategie automatiche;
- simulazioni multiple;
- statistiche aggregate;
- esportazione CSV/JSON;
- tournament controbilanciato tra strategie;
- simulazioni parametriche;
- generazione di grafici per il report.
- modalità sperimentale opzionale per carte Ferita Critica con effetti.

---

## Configurazione consigliata del regolamento

Dopo le simulazioni parametriche, la configurazione più bilanciata scelta è:

| Numero giocatori | Vite iniziali | Ferite Critiche massime | Effetti colore |
|---:|---:|---:|:---:|
| 2 giocatori | 12 | 5 | ON |
| 3 giocatori | 17 | 4 | ON |
| 4 giocatori | 24 | 4 | ON |

Questa configurazione è stata scelta perché produce un miglior equilibrio tra:

- eliminazioni per vite;
- eliminazioni per Ferite Critiche.

La configurazione iniziale storica:

```text
18 vite / 3 Ferite Critiche / effetti colore ON
```

risultava accettabile soprattutto a 4 giocatori, ma meno bilanciata a 2 e 3 giocatori.

---

## Strategie disponibili

Il simulatore include le seguenti strategie:

| Nome CLI | Descrizione |
|---|---|
| `random` | sceglie casualmente una carta dalla mano |
| `prudent` | tende a scegliere carte basse per ridurre la perdita di vite |
| `defensive` | preferisce carte del proprio colore |
| `aggressive` | preferisce carte del colore degli avversari |
| `anti_critical` | evita carte troppo basse per ridurre il rischio Ferita Critica |
| `mixed` | bilancia valore basso, colore proprio e colore avversario |
| `adaptive_pressure` | strategia euristica più avanzata: combina pressione offensiva, difesa e gestione del rischio Ferita Critica |
| `critical_adaptive` | strategia sperimentale basata su `adaptive_pressure`, consapevole degli effetti Ferita Critica attivi |

La strategia `adaptive_pressure` è risultata la più forte nei confronti controbilanciati tra strategie.

La modalità sperimentale delle carte Ferita Critica è disattivata di default e
si abilita con `--critical-card-effects on`. La documentazione operativa è in
[docs/critical_wound_cards_simulation.md](docs/critical_wound_cards_simulation.md).

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
- danni base;
- effetti colore;
- Ferite Critiche;
- eliminazioni;
- spareggi;
- strategie;
- simulazioni multiple;
- export CSV/JSON;
- tournament controbilanciato;
- simulazioni parametriche;
- generazione dei grafici.

---

## Uso base del simulatore

Eseguire una simulazione semplice:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42
```

Eseguire una simulazione usando una strategia specifica:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --strategy adaptive_pressure
```

Eseguire una simulazione con strategie diverse per giocatore:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --strategies adaptive_pressure random defensive aggressive
```

---

## Export CSV/JSON

Aggiungendo `--export`, il simulatore crea file nella cartella `results/`.

Esempio:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --strategy adaptive_pressure --export --output-dir results/example_run
```

File generati:

```text
simulation_config.json
aggregate_stats.json
games_summary.csv
rounds_summary.csv
```

I CSV usano il delimitatore `;`, così sono leggibili correttamente da Excel in italiano/Windows.

---

## Tournament controbilanciato tra strategie

Il tournament serve a confrontare strategie evitando che una strategia sia sempre legata allo stesso colore o posizione.

Esempio:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --tournament-strategies adaptive_pressure random defensive aggressive --export --output-dir results/tournament_4strategies_10000
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

Le simulazioni parametriche permettono di confrontare diverse configurazioni di vite, Ferite Critiche ed effetti colore.

Esempio generale:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --parametric --strategy adaptive_pressure --lives-values 18 19 20 21 22 --critical-wounds-values 3 4 5 --color-effects on --export --output-dir results/parametric_example
```

File esportati:

```text
parametric_stats.json
parametric_summary.csv
```

---

# Comandi usati per le simulazioni finali

I seguenti comandi sono stati usati per rigenerare i dataset finali, dopo aver svuotato la cartella `results/`.

---

## 1. Setup PowerShell

```powershell
$env:PYTHONPATH = "src"
```

---

# 2 giocatori

Obiettivo: dimostrare la scelta finale:

```text
12 vite / 5 Ferite Critiche / effetti colore ON
```

## Adaptive pressure

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 2 --games 10000 --seed 42 --parametric --strategy adaptive_pressure --lives-values 8 10 12 15 18 --critical-wounds-values 3 4 5 --color-effects on --export --output-dir results/final_adaptive_2p_balance
```

## Random

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 2 --games 10000 --seed 42 --parametric --strategy random --lives-values 8 10 12 15 18 --critical-wounds-values 3 4 5 --color-effects on --export --output-dir results/final_random_2p_balance
```

## Grafici 2 giocatori

```powershell
.\.venv\Scripts\python.exe run_simulation.py --plot-parametric results/final_adaptive_2p_balance/parametric_summary.csv --output-dir results/plots_final_adaptive_2p
```

```powershell
.\.venv\Scripts\python.exe run_simulation.py --plot-parametric results/final_random_2p_balance/parametric_summary.csv --output-dir results/plots_final_random_2p
```

---

# 3 giocatori

Obiettivo: dimostrare la scelta finale:

```text
17 vite / 4 Ferite Critiche / effetti colore ON
```

## Adaptive pressure

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 3 --games 10000 --seed 42 --parametric --strategy adaptive_pressure --lives-values 15 16 17 18 --critical-wounds-values 3 4 --color-effects on --export --output-dir results/final_adaptive_3p_balance
```

## Random

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 3 --games 10000 --seed 42 --parametric --strategy random --lives-values 15 16 17 18 --critical-wounds-values 3 4 --color-effects on --export --output-dir results/final_random_3p_balance
```

## Grafici 3 giocatori

```powershell
.\.venv\Scripts\python.exe run_simulation.py --plot-parametric results/final_adaptive_3p_balance/parametric_summary.csv --output-dir results/plots_final_adaptive_3p
```

```powershell
.\.venv\Scripts\python.exe run_simulation.py --plot-parametric results/final_random_3p_balance/parametric_summary.csv --output-dir results/plots_final_random_3p
```

---

# 4 giocatori

Obiettivo: dimostrare la scelta finale:

```text
24 vite / 4 Ferite Critiche / effetti colore ON
```

## Adaptive pressure

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --parametric --strategy adaptive_pressure --lives-values 18 22 23 24 25 26 --critical-wounds-values 3 4 --color-effects on --export --output-dir results/final_adaptive_4p_balance
```

## Random

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --parametric --strategy random --lives-values 18 22 23 24 25 26 --critical-wounds-values 3 4 --color-effects on --export --output-dir results/final_random_4p_balance
```

## Grafici 4 giocatori

```powershell
.\.venv\Scripts\python.exe run_simulation.py --plot-parametric results/final_adaptive_4p_balance/parametric_summary.csv --output-dir results/plots_final_adaptive_4p
```

```powershell
.\.venv\Scripts\python.exe run_simulation.py --plot-parametric results/final_random_4p_balance/parametric_summary.csv --output-dir results/plots_final_random_4p
```

---

# Test fine per 4 giocatori

Dopo una prima analisi, è stato fatto un test più fine sul caso a 4 giocatori con 4 Ferite Critiche.

## Adaptive pressure

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --parametric --strategy adaptive_pressure --lives-values 22 23 24 25 26 --critical-wounds-values 4 --color-effects on --export --output-dir results/parametric_adaptive_4p_22_26_cw4
```

## Random

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 10000 --seed 42 --parametric --strategy random --lives-values 22 23 24 25 26 --critical-wounds-values 4 --color-effects on --export --output-dir results/parametric_random_4p_22_26_cw4
```

## Grafici test fine 4 giocatori

```powershell
.\.venv\Scripts\python.exe run_simulation.py --plot-parametric results/parametric_adaptive_4p_22_26_cw4/parametric_summary.csv --output-dir results/plots_adaptive_4p_22_26_cw4
```

```powershell
.\.venv\Scripts\python.exe run_simulation.py --plot-parametric results/parametric_random_4p_22_26_cw4/parametric_summary.csv --output-dir results/plots_random_4p_22_26_cw4
```

---

## Grafici generati

Per ogni simulazione parametrica vengono creati:

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

- eliminazioni per vite;
- eliminazioni per Ferite Critiche.

La configurazione più bilanciata è quella in cui le due barre sono più vicine.

---

## Interpretazione finale

Le simulazioni hanno mostrato che non è ideale usare un unico valore fisso di vite e Ferite Critiche per ogni numero di giocatori.

Il setup consigliato cambia in base al numero di partecipanti:

```text
2 giocatori: 12 vite / 5 Ferite Critiche / ON
3 giocatori: 17 vite / 4 Ferite Critiche / ON
4 giocatori: 24 vite / 4 Ferite Critiche / ON
```

Questa scelta permette di mantenere rilevanti entrambe le meccaniche principali:

```text
- sopravvivenza tramite vite
- rischio da Ferite Critiche
```

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
│       ├── cli.py
│       ├── config.py
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
5. come l'uso di strumenti GenAI ha supportato progettazione, sviluppo e analisi.
