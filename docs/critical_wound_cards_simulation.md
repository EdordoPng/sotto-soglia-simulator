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

| ID | Name | Timing |
| --- | --- | --- |
| `bendaggio_emergenza` | Bendaggio d'Emergenza | Immediate |
| `sangue_freddo` | Sangue Freddo | Next round |
| `mano_lucida` | Mano Lucida | Next round |
| `scudo_istintivo` | Scudo Istintivo | Next round |
| `mano_tremante` | Mano Tremante | Next round |
| `colpo_di_coda` | Colpo di Coda | Next round |
| `ferita_esposta` | Ferita Esposta | Next round |
| `sono_ancora_qui` | Sono ancora qui | Immediate |

The critical wound deck is shuffled once at the beginning of each game. It is
not reshuffled during the game. If the deck is exhausted, new critical wounds
are still counted but no extra effect is drawn.

## CLI Flags

```powershell
--critical-card-effects off/on
--critical-deck-seed 123
--critical-deck-order bendaggio_emergenza,bendaggio_emergenza,sangue_freddo,sangue_freddo,mano_lucida,mano_lucida,scudo_istintivo,scudo_istintivo,mano_tremante,mano_tremante,colpo_di_coda,colpo_di_coda,ferita_esposta,ferita_esposta,sono_ancora_qui,sono_ancora_qui
```

`--critical-deck-seed` controls only the critical wound deck order. If it is not
provided, the game seed controls the critical deck order.

`--critical-deck-order` must contain exactly 16 card IDs with exactly 2 copies
of every effect. When provided, the same fixed order is used for every game.

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
