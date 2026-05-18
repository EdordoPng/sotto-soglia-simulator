# Simulation Design

Architettura prevista del simulatore:

- `models`: definisce colori, carte, giocatori e risultati base.
- `deck`: costruisce il mazzo comune in base ai colori attivi.
- `rules`: contiene le regole pure del gioco, separate dalle strategie.
- `round`: gestisce in futuro la risoluzione di un singolo round.
- `game`: gestisce in futuro il ciclo completo di una partita.
- `strategies`: contiene le strategie di scelta carta dei giocatori.
- `simulation`: coordina molte partite e controlla la riproducibilita' tramite seed.
- `statistics`: aggrega metriche e risultati.
- `exporters`: esporta risultati futuri in CSV e JSON.
- `cli`: espone un'interfaccia da terminale per lanciare simulazioni.
