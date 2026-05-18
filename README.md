# Sotto Soglia Simulator

Simulatore statistico in Python per il gioco di carte originale **Sotto Soglia**.

## Scopo

Il progetto ha l'obiettivo di simulare partite ripetute di Sotto Soglia per analizzare bilanciamento, durata media delle partite, eliminazioni, strategie e risultati statistici.

Stato attuale: **fase iniziale / scaffolding**. La struttura della repository e gli scheletri dei moduli sono pronti, ma il motore completo della partita non e' ancora implementato.

## Uso previsto

Esempio di comando CLI previsto:

```bash
python run_simulation.py --players 4 --games 10000 --seed 42
```

Per ora il comando stampa solo i parametri ricevuti e conferma che lo scaffold e' pronto.

## Obiettivi futuri

- Implementare il motore dei round e della partita.
- Supportare seed casuale riproducibile.
- Aggiungere strategie base e confronti tra strategie.
- Calcolare metriche aggregate sulle simulazioni.
- Esportare risultati in CSV e JSON.
- Aggiungere test progressivi sulle regole.

## Roadmap

1. Scaffolding iniziale del progetto.
2. Implementazione dei modelli, del mazzo e delle prime regole isolate.
3. Implementazione della risoluzione dei round.
4. Implementazione del motore partita e delle eliminazioni.
5. Implementazione del runner di simulazione.
6. Raccolta statistiche ed esportazione risultati.
7. Validazione con test e analisi di bilanciamento.

## Project structure

```text
sotto-soglia-simulator/
├── docs/                 # Documentazione del regolamento, design e metriche
├── data/                 # Dati grezzi e processati futuri
├── results/              # Output CSV/JSON futuri
├── src/sotto_soglia/     # Codice sorgente del simulatore
├── tests/                # Test automatici
├── run_simulation.py     # Entry point CLI provvisorio
├── requirements.txt      # Dipendenze minime
└── README.md
```
