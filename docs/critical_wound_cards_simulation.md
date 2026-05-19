# Critical Wound Cards Simulation

This document describes the experimental critical wound card mode. The mode is
disabled by default and must be enabled explicitly from the CLI.

## Enable the Mode

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 100 --seed 42 --strategy critical_adaptive --critical-card-effects on --export --output-dir results/smoke_critical_cards_4p
```

Default behavior remains:

```powershell
--critical-card-effects off
```

With the flag off, critical wounds are counted normally and no critical wound
cards are drawn.

## Cards

The critical wound deck has 16 cards: 8 effects, 2 copies each.

| ID | Name | Timing | Effect |
| --- | --- | --- | --- |
| `bendaggio_emergenza` | Bendaggio d'Emergenza | Immediate | Recuperi 1 vita. Non puoi superare le vite iniziali. |
| `sangue_freddo` | Sangue Freddo | Next round | Se giochi una carta del tuo colore e non ricevi Ferita Critica, riduci il danno base di 2 invece di 1. |
| `mano_lucida` | Mano Lucida | Next round | Ricevi 4 carte invece di 3 e ne scegli 1. |
| `scudo_istintivo` | Scudo Istintivo | Next round | Se non ricevi Ferita Critica, ignori il primo danno extra causato da una carta del tuo colore giocata da un avversario. |
| `mano_tremante` | Mano Tremante | Next round | Ricevi 2 carte invece di 3 e ne scegli 1. |
| `colpo_di_coda` | Colpo di Coda | Next round | Se ricevi di nuovo Ferita Critica, scegli un avversario valido: perde 2 vite. |
| `ferita_esposta` | Ferita Esposta | Next round | Se non ricevi Ferita Critica, il primo danno extra subito vale 2 invece di 1. |
| `sono_ancora_qui` | Sono ancora qui | Immediate | Scegli un avversario valido: perde 2 vite. |

The critical wound deck is shuffled once at the beginning of each game. It is
not reshuffled during the game. If the deck is exhausted, new critical wounds
are still counted but no extra effect is drawn.

## CLI Flags

```powershell
--critical-card-effects off/on
--critical-deck-seed 123
--sono-ancora-qui-variant single_2
--critical-deck-order bendaggio_emergenza,bendaggio_emergenza,sangue_freddo,sangue_freddo,mano_lucida,mano_lucida,scudo_istintivo,scudo_istintivo,mano_tremante,mano_tremante,colpo_di_coda,colpo_di_coda,ferita_esposta,ferita_esposta,sono_ancora_qui,sono_ancora_qui
```

`--critical-deck-seed` controls only the critical wound deck order. If it is not
provided, the game seed controls the critical deck order.

`--critical-deck-order` must contain exactly 16 card IDs with exactly 2 copies
of every effect. When provided, the same fixed order is used for every game.

`--sono-ancora-qui-variant` is experimental and only matters when
`--critical-card-effects on` is enabled. The current v0.4 rules default is
`single_2`; the other values are kept for comparative simulations:

| Variant | Effect |
| --- | --- |
| `single_1` | Scegli un avversario valido: perde 1 vita. |
| `single_2` | Scegli un avversario valido: perde 2 vite. |
| `up_to_2_targets` | Scegli fino a 2 avversari validi: ognuno perde 1 vita. |

For `up_to_2_targets`, `critical_events.csv` stores multiple target ids in
`target_player_id` as a comma-separated value and records per-target deltas in
`life_delta_targets`.

## Strategy

The experimental strategy is:

```powershell
--strategy critical_adaptive
```

It starts from `adaptive_pressure` and adjusts its scoring for active critical
wound effects such as `sangue_freddo`, `scudo_istintivo`, `ferita_esposta`, and
`colpo_di_coda`.

## Exports

When `--export` and `--critical-card-effects on` are used, these additional
files are written:

| File | Content |
| --- | --- |
| `critical_events.csv` | Draws and triggered critical-card events |
| `critical_deck_orders.csv` | Initial critical deck order per game |
| `critical_card_stats.csv` | Aggregate per-card balancing metrics |

`aggregate_stats.json` also includes critical-card totals, trigger counts,
average life deltas, total life gained/lost, and prevented damage.

When `--critical-card-effects off`, the historical CSV exports are unchanged:
`games_summary.csv` and `rounds_summary.csv` keep their existing columns.

## Smoke Test

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 100 --seed 42 --strategy critical_adaptive --critical-card-effects on --export --output-dir results/smoke_critical_cards_4p
```

## Baseline vs Experimental

Baseline without critical wound cards:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 1000 --seed 42 --strategy adaptive_pressure --critical-card-effects off --export --output-dir results/baseline_no_critical_cards
```

Experimental mode:

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 1000 --seed 42 --strategy critical_adaptive --critical-card-effects on --export --output-dir results/critical_cards_4p
```

## Critical Deck Seed

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 1000 --seed 42 --critical-deck-seed 123 --strategy critical_adaptive --critical-card-effects on --export --output-dir results/critical_deck_seed_123
```

## Fixed Deck Order

```powershell
.\.venv\Scripts\python.exe run_simulation.py --players 4 --games 100 --seed 42 --strategy critical_adaptive --critical-card-effects on --critical-deck-order bendaggio_emergenza,bendaggio_emergenza,sangue_freddo,sangue_freddo,mano_lucida,mano_lucida,scudo_istintivo,scudo_istintivo,mano_tremante,mano_tremante,colpo_di_coda,colpo_di_coda,ferita_esposta,ferita_esposta,sono_ancora_qui,sono_ancora_qui --export --output-dir results/fixed_critical_deck_order
```
