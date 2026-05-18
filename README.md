# Sotto Soglia Simulator

## Descrizione
Breve spiegazione del gioco e dello scopo del simulatore.

## Obiettivo del progetto
Simulare molte partite per analizzare bilanciamento, durata, eliminazioni e strategie.

## Regole sintetiche
Riassunto delle regole principali.

## Installazione
python -m venv .venv
pip install -r requirements.txt

## Uso
python run_simulation.py --players 4 --games 10000 --seed 42

## Output generati
- games_summary.csv
- rounds_log.csv
- aggregate_stats.json
- simulation_config.json

## Strategie disponibili
- random
- prudent
- anti_critical
- aggressive
- defensive
- mixed

## Metriche raccolte
Elenco delle metriche principali.

## Riproducibilità
Spiegazione del seed.

## Test
pytest

## Collegamento con il progetto d’esame
Come il simulatore supporta il design, il bilanciamento e il report tecnico.

## Stato del progetto
MVP / in sviluppo.

## Licenza
Da decidere.
