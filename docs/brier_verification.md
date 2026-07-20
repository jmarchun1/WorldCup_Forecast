# Brier Score Verification Report
## WC2026 LLM Forecast — 2026-06-26

## Formula

Multi-class Brier score across 3 mutually exclusive outcomes:

    Brier = [ (p_home - I_home)^2 + (p_draw - I_draw)^2 + (p_away - I_away)^2 ] / 3

Where I_x = 1 if x was the actual outcome, else 0.
Lower is better. Perfect calibration = 0.0, random 1/3 each = 0.222.

---

## Verification Summary

- Total scored records: 646
- Mismatches (stored vs recomputed): 0
- Overall mean Brier: 0.1701

---

## Per-Model Summary

| Model | Mean Brier | n | vs Random Baseline (0.222) |
|---|---|---|---|
| gem25flash | 0.1604 | 60 | -0.0618 |
| gem25pro | 0.1639 | 60 | -0.0583 |
| sonar | 0.1661 | 28 | -0.0561 |
| sonnet | 0.1671 | 60 | -0.0551 |
| gpt5 | 0.1697 | 60 | -0.0525 |
| gpt54 | 0.1697 | 60 | -0.0525 |
| gpt5mini | 0.1707 | 50 | -0.0515 |
| opus | 0.1711 | 60 | -0.0511 |
| sonarpro | 0.1713 | 28 | -0.0509 |
| gem31flashlite | 0.1744 | 60 | -0.0478 |
| haiku | 0.1770 | 60 | -0.0452 |
| gem25flashlite | 0.1781 | 60 | -0.0441 |

---

## Per-Model Detail with Sample Calculations

### gem25flash  (mean Brier = 0.1604)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Algeria 06-16 | home_win | 0.73 | 0.18 | 0.09 | 0.0378 | 1 (correct_result) |
| Argentina Austria 06-22 | home_win | 0.56 | 0.25 | 0.19 | 0.0974 | 4 (exact_score) |
| Australia Turkey 06-13 | home_win | 0.22 | 0.27 | 0.52 | 0.3146 | 0 (wrong_result) |
| Austria Jordan 06-16 | home_win | 0.70 | 0.18 | 0.12 | 0.0456 | 2 (correct_result_exact_gd) |
| Belgium Egypt 06-15 | draw | 0.61 | 0.23 | 0.16 | 0.3302 | 0 (wrong_result) |
| Belgium Iran 06-21 | draw | 0.65 | 0.23 | 0.12 | 0.3433 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.60 | 0.24 | 0.16 | 0.0795 | 1 (correct_result) |
| Brazil Haiti 06-19 | home_win | 0.87 | 0.09 | 0.04 | 0.0089 | 1 (correct_result) |
| Brazil Morocco 06-13 | draw | 0.58 | 0.24 | 0.18 | 0.3155 | 0 (wrong_result) |
| Canada Bosnia and Herzegovina 06-12 | draw | 0.53 | 0.26 | 0.21 | 0.2896 | 0 (wrong_result) |
| Canada Qatar 06-18 | home_win | 0.74 | 0.18 | 0.07 | 0.0343 | 1 (correct_result) |
| Colombia DR Congo 06-23 | home_win | 0.65 | 0.23 | 0.12 | 0.0633 | 1 (correct_result) |
| Curacao Ivory Coast 06-25 | away_win | 0.06 | 0.16 | 0.78 | 0.0259 | 1 (correct_result) |
| Czech Republic Mexico 06-24 | away_win | 0.50 | 0.28 | 0.22 | 0.3123 | 0 (wrong_result) |
| Czech Republic South Africa 06-18 | draw | 0.38 | 0.38 | 0.24 | 0.1955 | 4 (exact_score) |
| Ecuador Curacao 06-20 | draw | 0.48 | 0.28 | 0.25 | 0.2719 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.22 | 0.25 | 0.53 | 0.3173 | 0 (wrong_result) |
| England Croatia 06-17 | home_win | 0.56 | 0.24 | 0.20 | 0.0972 | 1 (correct_result) |
| England Ghana 06-23 | draw | 0.70 | 0.19 | 0.11 | 0.3861 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.88 | 0.09 | 0.03 | 0.0078 | 4 (exact_score) |
| France Senegal 06-16 | home_win | 0.65 | 0.22 | 0.13 | 0.0626 | 2 (correct_result_exact_gd) |
| Germany Curacao 06-14 | home_win | 0.94 | 0.04 | 0.01 | 0.0017 | 1 (correct_result) |
| Germany Ivory Coast 06-20 | home_win | 0.58 | 0.24 | 0.17 | 0.0873 | 4 (exact_score) |
| Ghana Panama 06-17 | home_win | 0.49 | 0.26 | 0.26 | 0.1321 | 4 (exact_score) |
| Haiti Scotland 06-13 | away_win | 0.15 | 0.20 | 0.65 | 0.0617 | 1 (correct_result) |
| Iran New Zealand 06-15 | draw | 0.40 | 0.38 | 0.22 | 0.1986 | 0 (wrong_result) |
| Iraq Norway 06-16 | away_win | 0.22 | 0.18 | 0.60 | 0.0810 | 2 (correct_result_exact_gd) |
| Ivory Coast Ecuador 06-14 | home_win | 0.27 | 0.34 | 0.39 | 0.2670 | 0 (wrong_result) |
| Japan Sweden 06-25 | draw | 0.33 | 0.35 | 0.32 | 0.2113 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.29 | 0.28 | 0.44 | 0.1591 | 0 (wrong_result) |
| Mexico South Africa 06-11 | home_win | 0.61 | 0.23 | 0.15 | 0.0771 | 4 (exact_score) |
| Mexico South Korea 06-18 | home_win | 0.53 | 0.26 | 0.21 | 0.1109 | 2 (correct_result_exact_gd) |
| Morocco Haiti 06-24 | home_win | 0.82 | 0.13 | 0.05 | 0.0173 | 1 (correct_result) |
| Netherlands Japan 06-14 | draw | 0.45 | 0.30 | 0.25 | 0.2517 | 0 (wrong_result) |
| Netherlands Sweden 06-20 | home_win | 0.52 | 0.28 | 0.20 | 0.1163 | 1 (correct_result) |
| New Zealand Egypt 06-21 | away_win | 0.20 | 0.28 | 0.52 | 0.1155 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.39 | 0.36 | 0.24 | 0.1878 | 2 (correct_result_exact_gd) |
| Panama Croatia 06-23 | away_win | 0.15 | 0.23 | 0.62 | 0.0733 | 2 (correct_result_exact_gd) |
| Paraguay Australia 06-25 | draw | 0.40 | 0.35 | 0.25 | 0.2150 | 1 (correct_draw) |
| Portugal DR Congo 06-17 | draw | 0.72 | 0.19 | 0.09 | 0.3942 | 0 (wrong_result) |
| Portugal Uzbekistan 06-23 | home_win | 0.73 | 0.17 | 0.10 | 0.0369 | 1 (correct_result) |
| Qatar Switzerland 06-13 | draw | 0.12 | 0.19 | 0.69 | 0.3822 | 0 (wrong_result) |
| Saudi Arabia Uruguay 06-15 | draw | 0.10 | 0.23 | 0.67 | 0.3506 | 0 (wrong_result) |
| Scotland Brazil 06-24 | away_win | 0.08 | 0.12 | 0.80 | 0.0203 | 4 (exact_score) |
| Scotland Morocco 06-19 | away_win | 0.22 | 0.33 | 0.45 | 0.1533 | 4 (exact_score) |
| South Africa South Korea 06-24 | home_win | 0.17 | 0.25 | 0.58 | 0.3626 | 0 (wrong_result) |
| South Korea Czech Republic 06-11 | home_win | 0.32 | 0.38 | 0.30 | 0.2323 | 0 (wrong_result) |
| Spain Cape Verde 06-15 | draw | 0.00 | 1.00 | 0.00 | 0.0000 | 4 (exact_score) |
| Spain Saudi Arabia 06-21 | home_win | 0.80 | 0.12 | 0.08 | 0.0203 | 1 (correct_result) |
| Sweden Tunisia 06-14 | home_win | 0.50 | 0.28 | 0.22 | 0.1256 | 1 (correct_result) |
| Switzerland Bosnia and Herzegovina 06-18 | home_win | 0.61 | 0.24 | 0.15 | 0.0766 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.47 | 0.28 | 0.25 | 0.1427 | 2 (correct_result_exact_gd) |
| Tunisia Japan 06-20 | away_win | 0.33 | 0.25 | 0.43 | 0.1652 | 0 (wrong_result) |
| Tunisia Netherlands 06-25 | away_win | 0.10 | 0.20 | 0.70 | 0.0467 | 1 (correct_result) |
| Turkey Paraguay 06-19 | away_win | 0.42 | 0.28 | 0.29 | 0.2520 | 0 (wrong_result) |
| USA Australia 06-19 | home_win | 0.60 | 0.23 | 0.17 | 0.0817 | 1 (correct_result) |
| USA Paraguay 06-12 | home_win | 0.39 | 0.38 | 0.23 | 0.1903 | 0 (wrong_result) |
| USA Turkey 06-25 | away_win | 0.30 | 0.35 | 0.35 | 0.2117 | 0 (wrong_result) |
| Uruguay Cape Verde 06-21 | draw | 0.65 | 0.25 | 0.10 | 0.3317 | 0 (wrong_result) |
| Uzbekistan Colombia 06-17 | away_win | 0.10 | 0.20 | 0.70 | 0.0473 | 1 (correct_result) |

**Worked example** — Argentina Algeria 2026-06-16:

    p_home=0.73, p_draw=0.18, p_away=0.09
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.73 - 1)^2 + (0.18 - 0)^2 + (0.09 - 0)^2] / 3
         = [0.0729 + 0.0324 + 0.0081] / 3
         = 0.0378  (stored: 0.0378)

### gem25pro  (mean Brier = 0.1639)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Algeria 06-16 | home_win | 0.68 | 0.22 | 0.10 | 0.0536 | 1 (correct_result) |
| Argentina Austria 06-22 | home_win | 0.55 | 0.30 | 0.15 | 0.1050 | 1 (correct_result) |
| Australia Turkey 06-13 | home_win | 0.20 | 0.28 | 0.52 | 0.3296 | 0 (wrong_result) |
| Austria Jordan 06-16 | home_win | 0.72 | 0.19 | 0.09 | 0.0409 | 2 (correct_result_exact_gd) |
| Belgium Egypt 06-15 | draw | 0.62 | 0.24 | 0.14 | 0.3272 | 0 (wrong_result) |
| Belgium Iran 06-21 | draw | 0.65 | 0.23 | 0.12 | 0.3433 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.62 | 0.23 | 0.15 | 0.0733 | 1 (correct_result) |
| Brazil Haiti 06-19 | home_win | 0.90 | 0.08 | 0.02 | 0.0056 | 4 (exact_score) |
| Brazil Morocco 06-13 | draw | 0.58 | 0.26 | 0.16 | 0.3032 | 0 (wrong_result) |
| Canada Bosnia and Herzegovina 06-12 | draw | 0.47 | 0.32 | 0.21 | 0.2425 | 0 (wrong_result) |
| Canada Qatar 06-18 | home_win | 0.77 | 0.16 | 0.07 | 0.0278 | 1 (correct_result) |
| Colombia DR Congo 06-23 | home_win | 0.66 | 0.22 | 0.12 | 0.0595 | 4 (exact_score) |
| Curacao Ivory Coast 06-25 | away_win | 0.05 | 0.15 | 0.80 | 0.0217 | 1 (correct_result) |
| Czech Republic Mexico 06-24 | away_win | 0.46 | 0.33 | 0.21 | 0.3149 | 0 (wrong_result) |
| Czech Republic South Africa 06-18 | draw | 0.52 | 0.27 | 0.21 | 0.2825 | 0 (wrong_result) |
| Ecuador Curacao 06-20 | draw | 0.58 | 0.25 | 0.17 | 0.3093 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.20 | 0.30 | 0.50 | 0.3267 | 0 (wrong_result) |
| England Croatia 06-17 | home_win | 0.54 | 0.27 | 0.19 | 0.1069 | 1 (correct_result) |
| England Ghana 06-23 | draw | 0.72 | 0.19 | 0.09 | 0.3942 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.88 | 0.10 | 0.02 | 0.0083 | 4 (exact_score) |
| France Senegal 06-16 | home_win | 0.66 | 0.21 | 0.13 | 0.0589 | 2 (correct_result_exact_gd) |
| Germany Curacao 06-14 | home_win | 0.92 | 0.06 | 0.02 | 0.0035 | 1 (correct_result) |
| Germany Ivory Coast 06-20 | home_win | 0.65 | 0.22 | 0.13 | 0.0626 | 1 (correct_result) |
| Ghana Panama 06-17 | home_win | 0.48 | 0.30 | 0.22 | 0.1363 | 4 (exact_score) |
| Haiti Scotland 06-13 | away_win | 0.12 | 0.18 | 0.70 | 0.0456 | 1 (correct_result) |
| Iran New Zealand 06-15 | draw | 0.50 | 0.30 | 0.20 | 0.2600 | 0 (wrong_result) |
| Iraq Norway 06-16 | away_win | 0.09 | 0.18 | 0.73 | 0.0378 | 1 (correct_result) |
| Ivory Coast Ecuador 06-14 | home_win | 0.29 | 0.36 | 0.35 | 0.2521 | 0 (wrong_result) |
| Japan Sweden 06-25 | draw | 0.35 | 0.40 | 0.25 | 0.1817 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.14 | 0.24 | 0.62 | 0.0739 | 2 (correct_result_exact_gd) |
| Mexico South Africa 06-11 | home_win | 0.65 | 0.23 | 0.12 | 0.0633 | 4 (exact_score) |
| Mexico South Korea 06-18 | home_win | 0.52 | 0.28 | 0.20 | 0.1163 | 4 (exact_score) |
| Morocco Haiti 06-24 | home_win | 0.83 | 0.14 | 0.03 | 0.0165 | 1 (correct_result) |
| Netherlands Japan 06-14 | draw | 0.32 | 0.38 | 0.30 | 0.1923 | 1 (correct_draw) |
| Netherlands Sweden 06-20 | home_win | 0.43 | 0.35 | 0.22 | 0.1653 | 0 (wrong_result) |
| New Zealand Egypt 06-21 | away_win | 0.15 | 0.30 | 0.55 | 0.1050 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.35 | 0.40 | 0.25 | 0.2150 | 0 (wrong_result) |
| Panama Croatia 06-23 | away_win | 0.15 | 0.23 | 0.62 | 0.0733 | 1 (correct_result) |
| Paraguay Australia 06-25 | draw | 0.38 | 0.34 | 0.28 | 0.2195 | 1 (correct_draw) |
| Portugal DR Congo 06-17 | draw | 0.74 | 0.18 | 0.08 | 0.4088 | 0 (wrong_result) |
| Portugal Uzbekistan 06-23 | home_win | 0.80 | 0.14 | 0.06 | 0.0211 | 1 (correct_result) |
| Qatar Switzerland 06-13 | draw | 0.10 | 0.18 | 0.72 | 0.4003 | 0 (wrong_result) |
| Saudi Arabia Uruguay 06-15 | draw | 0.10 | 0.20 | 0.70 | 0.3800 | 0 (wrong_result) |
| Scotland Brazil 06-24 | away_win | 0.12 | 0.18 | 0.70 | 0.0456 | 1 (correct_result) |
| Scotland Morocco 06-19 | away_win | 0.25 | 0.30 | 0.45 | 0.1517 | 4 (exact_score) |
| South Africa South Korea 06-24 | home_win | 0.15 | 0.25 | 0.60 | 0.3817 | 0 (wrong_result) |
| South Korea Czech Republic 06-11 | home_win | 0.30 | 0.36 | 0.34 | 0.2451 | 0 (wrong_result) |
| Spain Cape Verde 06-15 | draw | 0.00 | 1.00 | 0.00 | 0.0000 | 4 (exact_score) |
| Spain Saudi Arabia 06-21 | home_win | 0.78 | 0.16 | 0.06 | 0.0259 | 1 (correct_result) |
| Sweden Tunisia 06-14 | home_win | 0.46 | 0.31 | 0.23 | 0.1469 | 1 (correct_result) |
| Switzerland Bosnia and Herzegovina 06-18 | home_win | 0.62 | 0.25 | 0.13 | 0.0746 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.27 | 0.38 | 0.35 | 0.2666 | 0 (wrong_result) |
| Tunisia Japan 06-20 | away_win | 0.20 | 0.32 | 0.48 | 0.1376 | 1 (correct_result) |
| Tunisia Netherlands 06-25 | away_win | 0.17 | 0.25 | 0.58 | 0.0893 | 2 (correct_result_exact_gd) |
| Turkey Paraguay 06-19 | away_win | 0.45 | 0.30 | 0.25 | 0.2850 | 0 (wrong_result) |
| USA Australia 06-19 | home_win | 0.62 | 0.23 | 0.15 | 0.0733 | 1 (correct_result) |
| USA Paraguay 06-12 | home_win | 0.44 | 0.33 | 0.23 | 0.1585 | 1 (correct_result) |
| USA Turkey 06-25 | away_win | 0.25 | 0.35 | 0.40 | 0.1817 | 0 (wrong_result) |
| Uruguay Cape Verde 06-21 | draw | 0.68 | 0.22 | 0.10 | 0.3603 | 0 (wrong_result) |
| Uzbekistan Colombia 06-17 | away_win | 0.10 | 0.20 | 0.70 | 0.0467 | 2 (correct_result_exact_gd) |

**Worked example** — Argentina Algeria 2026-06-16:

    p_home=0.68, p_draw=0.22, p_away=0.1
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.68 - 1)^2 + (0.22 - 0)^2 + (0.1 - 0)^2] / 3
         = [0.1024 + 0.0484 + 0.0100] / 3
         = 0.0536  (stored: 0.0536)

### sonar  (mean Brier = 0.1661)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Austria 06-22 | home_win | 0.43 | 0.28 | 0.29 | 0.1625 | 1 (correct_result) |
| Belgium Iran 06-21 | draw | 0.54 | 0.25 | 0.21 | 0.2994 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.49 | 0.31 | 0.20 | 0.1321 | 1 (correct_result) |
| Colombia DR Congo 06-23 | home_win | 0.47 | 0.33 | 0.20 | 0.1433 | 4 (exact_score) |
| Curacao Ivory Coast 06-25 | away_win | 0.06 | 0.15 | 0.79 | 0.0234 | 1 (correct_result) |
| Czech Republic Mexico 06-24 | away_win | 0.42 | 0.26 | 0.32 | 0.2355 | 0 (wrong_result) |
| Ecuador Curacao 06-20 | draw | 0.63 | 0.23 | 0.14 | 0.3365 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.18 | 0.23 | 0.59 | 0.3578 | 0 (wrong_result) |
| England Ghana 06-23 | draw | 0.71 | 0.20 | 0.09 | 0.3841 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.84 | 0.13 | 0.03 | 0.0145 | 1 (correct_result) |
| Germany Ivory Coast 06-20 | home_win | 0.55 | 0.23 | 0.22 | 0.1013 | 4 (exact_score) |
| Japan Sweden 06-25 | draw | 0.34 | 0.32 | 0.34 | 0.2312 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.18 | 0.27 | 0.55 | 0.1026 | 2 (correct_result_exact_gd) |
| Morocco Haiti 06-24 | home_win | 0.78 | 0.18 | 0.04 | 0.0275 | 2 (correct_result_exact_gd) |
| Netherlands Sweden 06-20 | home_win | 0.55 | 0.27 | 0.18 | 0.1026 | 1 (correct_result) |
| New Zealand Egypt 06-21 | away_win | 0.27 | 0.27 | 0.46 | 0.1458 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.36 | 0.34 | 0.30 | 0.2051 | 0 (wrong_result) |
| Panama Croatia 06-23 | away_win | 0.17 | 0.25 | 0.58 | 0.0893 | 4 (exact_score) |
| Paraguay Australia 06-25 | draw | 0.35 | 0.37 | 0.28 | 0.1993 | 1 (correct_draw) |
| Portugal Uzbekistan 06-23 | home_win | 0.73 | 0.19 | 0.08 | 0.0385 | 1 (correct_result) |
| Scotland Brazil 06-24 | away_win | 0.15 | 0.20 | 0.65 | 0.0617 | 4 (exact_score) |
| South Africa South Korea 06-24 | home_win | 0.19 | 0.22 | 0.59 | 0.3509 | 0 (wrong_result) |
| Spain Saudi Arabia 06-21 | home_win | 0.78 | 0.17 | 0.05 | 0.0266 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.38 | 0.31 | 0.31 | 0.1922 | 0 (wrong_result) |
| Tunisia Japan 06-20 | away_win | 0.28 | 0.30 | 0.42 | 0.1683 | 1 (correct_result) |
| Tunisia Netherlands 06-25 | away_win | 0.10 | 0.15 | 0.75 | 0.0317 | 4 (exact_score) |
| USA Turkey 06-25 | away_win | 0.30 | 0.40 | 0.30 | 0.2467 | 0 (wrong_result) |
| Uruguay Cape Verde 06-21 | draw | 0.49 | 0.33 | 0.18 | 0.2405 | 0 (wrong_result) |

**Worked example** — Argentina Austria 2026-06-22:

    p_home=0.43, p_draw=0.28, p_away=0.29
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.43 - 1)^2 + (0.28 - 0)^2 + (0.29 - 0)^2] / 3
         = [0.3249 + 0.0784 + 0.0841] / 3
         = 0.1625  (stored: 0.1625)

### sonnet  (mean Brier = 0.1671)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Algeria 06-16 | home_win | 0.68 | 0.22 | 0.10 | 0.0536 | 1 (correct_result) |
| Argentina Austria 06-22 | home_win | 0.58 | 0.26 | 0.16 | 0.0899 | 4 (exact_score) |
| Australia Turkey 06-13 | home_win | 0.22 | 0.24 | 0.54 | 0.3192 | 0 (wrong_result) |
| Austria Jordan 06-16 | home_win | 0.68 | 0.21 | 0.11 | 0.0529 | 2 (correct_result_exact_gd) |
| Belgium Egypt 06-15 | draw | 0.55 | 0.30 | 0.15 | 0.2717 | 0 (wrong_result) |
| Belgium Iran 06-21 | draw | 0.62 | 0.23 | 0.15 | 0.3333 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.50 | 0.32 | 0.18 | 0.1283 | 1 (correct_result) |
| Brazil Haiti 06-19 | home_win | 0.82 | 0.12 | 0.06 | 0.0168 | 4 (exact_score) |
| Brazil Morocco 06-13 | draw | 0.54 | 0.30 | 0.16 | 0.2691 | 0 (wrong_result) |
| Canada Bosnia and Herzegovina 06-12 | draw | 0.42 | 0.34 | 0.24 | 0.2232 | 0 (wrong_result) |
| Canada Qatar 06-18 | home_win | 0.58 | 0.26 | 0.16 | 0.0899 | 1 (correct_result) |
| Colombia DR Congo 06-23 | home_win | 0.55 | 0.30 | 0.15 | 0.1050 | 4 (exact_score) |
| Curacao Ivory Coast 06-25 | away_win | 0.06 | 0.12 | 0.82 | 0.0168 | 4 (exact_score) |
| Czech Republic Mexico 06-24 | away_win | 0.47 | 0.27 | 0.26 | 0.2805 | 0 (wrong_result) |
| Czech Republic South Africa 06-18 | draw | 0.40 | 0.34 | 0.26 | 0.2211 | 4 (exact_score) |
| Ecuador Curacao 06-20 | draw | 0.58 | 0.26 | 0.16 | 0.3032 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.28 | 0.24 | 0.48 | 0.2688 | 0 (wrong_result) |
| England Croatia 06-17 | home_win | 0.50 | 0.30 | 0.20 | 0.1267 | 1 (correct_result) |
| England Ghana 06-23 | draw | 0.65 | 0.22 | 0.13 | 0.3493 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.82 | 0.13 | 0.05 | 0.0173 | 4 (exact_score) |
| France Senegal 06-16 | home_win | 0.58 | 0.28 | 0.14 | 0.0915 | 1 (correct_result) |
| Germany Curacao 06-14 | home_win | 0.93 | 0.05 | 0.02 | 0.0026 | 1 (correct_result) |
| Germany Ivory Coast 06-20 | home_win | 0.55 | 0.26 | 0.19 | 0.1021 | 4 (exact_score) |
| Ghana Panama 06-17 | home_win | 0.38 | 0.35 | 0.27 | 0.1933 | 0 (wrong_result) |
| Haiti Scotland 06-13 | away_win | 0.13 | 0.22 | 0.65 | 0.0626 | 1 (correct_result) |
| Iran New Zealand 06-15 | draw | 0.46 | 0.33 | 0.21 | 0.2349 | 0 (wrong_result) |
| Iraq Norway 06-16 | away_win | 0.10 | 0.18 | 0.72 | 0.0403 | 1 (correct_result) |
| Ivory Coast Ecuador 06-14 | home_win | 0.29 | 0.33 | 0.38 | 0.2525 | 0 (wrong_result) |
| Japan Sweden 06-25 | draw | 0.36 | 0.32 | 0.32 | 0.2315 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.17 | 0.26 | 0.57 | 0.0938 | 2 (correct_result_exact_gd) |
| Mexico South Africa 06-11 | home_win | 0.58 | 0.25 | 0.17 | 0.0893 | 4 (exact_score) |
| Mexico South Korea 06-18 | home_win | 0.42 | 0.32 | 0.26 | 0.1688 | 0 (wrong_result) |
| Morocco Haiti 06-24 | home_win | 0.75 | 0.18 | 0.07 | 0.0333 | 2 (correct_result_exact_gd) |
| Netherlands Japan 06-14 | draw | 0.46 | 0.26 | 0.28 | 0.2792 | 0 (wrong_result) |
| Netherlands Sweden 06-20 | home_win | 0.50 | 0.28 | 0.22 | 0.1256 | 1 (correct_result) |
| New Zealand Egypt 06-21 | away_win | 0.17 | 0.27 | 0.56 | 0.0985 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.42 | 0.30 | 0.28 | 0.1683 | 2 (correct_result_exact_gd) |
| Panama Croatia 06-23 | away_win | 0.14 | 0.22 | 0.64 | 0.0659 | 1 (correct_result) |
| Paraguay Australia 06-25 | draw | 0.36 | 0.32 | 0.32 | 0.2315 | 1 (correct_draw) |
| Portugal DR Congo 06-17 | draw | 0.68 | 0.22 | 0.10 | 0.3603 | 0 (wrong_result) |
| Portugal Uzbekistan 06-23 | home_win | 0.76 | 0.16 | 0.08 | 0.0299 | 1 (correct_result) |
| Qatar Switzerland 06-13 | draw | 0.12 | 0.22 | 0.66 | 0.3528 | 0 (wrong_result) |
| Saudi Arabia Uruguay 06-15 | draw | 0.10 | 0.22 | 0.68 | 0.3603 | 0 (wrong_result) |
| Scotland Brazil 06-24 | away_win | 0.18 | 0.22 | 0.60 | 0.0803 | 1 (correct_result) |
| Scotland Morocco 06-19 | away_win | 0.24 | 0.28 | 0.48 | 0.1355 | 4 (exact_score) |
| South Africa South Korea 06-24 | home_win | 0.17 | 0.24 | 0.59 | 0.3649 | 0 (wrong_result) |
| South Korea Czech Republic 06-11 | home_win | 0.34 | 0.34 | 0.32 | 0.2179 | 0 (wrong_result) |
| Spain Cape Verde 06-15 | draw | 0.62 | 0.26 | 0.12 | 0.3155 | 0 (wrong_result) |
| Spain Saudi Arabia 06-21 | home_win | 0.76 | 0.17 | 0.07 | 0.0305 | 1 (correct_result) |
| Sweden Tunisia 06-14 | home_win | 0.46 | 0.32 | 0.22 | 0.1475 | 1 (correct_result) |
| Switzerland Bosnia and Herzegovina 06-18 | home_win | 0.58 | 0.27 | 0.15 | 0.0906 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.42 | 0.31 | 0.27 | 0.1685 | 0 (wrong_result) |
| Tunisia Japan 06-20 | away_win | 0.20 | 0.25 | 0.55 | 0.1017 | 1 (correct_result) |
| Tunisia Netherlands 06-25 | away_win | 0.14 | 0.21 | 0.65 | 0.0621 | 2 (correct_result_exact_gd) |
| Turkey Paraguay 06-19 | away_win | 0.42 | 0.30 | 0.28 | 0.2616 | 0 (wrong_result) |
| USA Australia 06-19 | home_win | 0.52 | 0.30 | 0.18 | 0.1176 | 1 (correct_result) |
| USA Paraguay 06-12 | home_win | 0.42 | 0.34 | 0.24 | 0.1699 | 1 (correct_result) |
| USA Turkey 06-25 | away_win | 0.30 | 0.36 | 0.34 | 0.2184 | 0 (wrong_result) |
| Uruguay Cape Verde 06-21 | draw | 0.58 | 0.28 | 0.14 | 0.2915 | 0 (wrong_result) |
| Uzbekistan Colombia 06-17 | away_win | 0.10 | 0.20 | 0.70 | 0.0467 | 2 (correct_result_exact_gd) |

**Worked example** — Argentina Algeria 2026-06-16:

    p_home=0.68, p_draw=0.22, p_away=0.1
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.68 - 1)^2 + (0.22 - 0)^2 + (0.1 - 0)^2] / 3
         = [0.1024 + 0.0484 + 0.0100] / 3
         = 0.0536  (stored: 0.0536)

### gpt5  (mean Brier = 0.1697)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Algeria 06-16 | home_win | 0.68 | 0.21 | 0.11 | 0.0529 | 1 (correct_result) |
| Argentina Austria 06-22 | home_win | 0.57 | 0.26 | 0.17 | 0.0938 | 1 (correct_result) |
| Australia Turkey 06-13 | home_win | 0.22 | 0.27 | 0.51 | 0.3138 | 0 (wrong_result) |
| Austria Jordan 06-16 | home_win | 0.68 | 0.20 | 0.12 | 0.0523 | 2 (correct_result_exact_gd) |
| Belgium Egypt 06-15 | draw | 0.62 | 0.24 | 0.14 | 0.3272 | 0 (wrong_result) |
| Belgium Iran 06-21 | draw | 0.61 | 0.25 | 0.14 | 0.3181 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.58 | 0.26 | 0.16 | 0.0899 | 1 (correct_result) |
| Brazil Haiti 06-19 | home_win | 0.88 | 0.09 | 0.03 | 0.0078 | 4 (exact_score) |
| Brazil Morocco 06-13 | draw | 0.52 | 0.29 | 0.19 | 0.2702 | 0 (wrong_result) |
| Canada Bosnia and Herzegovina 06-12 | draw | 0.47 | 0.29 | 0.24 | 0.2609 | 0 (wrong_result) |
| Canada Qatar 06-18 | home_win | 0.73 | 0.18 | 0.09 | 0.0378 | 1 (correct_result) |
| Colombia DR Congo 06-23 | home_win | 0.64 | 0.23 | 0.13 | 0.0665 | 4 (exact_score) |
| Curacao Ivory Coast 06-25 | away_win | 0.08 | 0.17 | 0.75 | 0.0326 | 1 (correct_result) |
| Czech Republic Mexico 06-24 | away_win | 0.36 | 0.32 | 0.32 | 0.2315 | 0 (wrong_result) |
| Czech Republic South Africa 06-18 | draw | 0.46 | 0.30 | 0.24 | 0.2531 | 4 (exact_score) |
| Ecuador Curacao 06-20 | draw | 0.50 | 0.27 | 0.23 | 0.2786 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.19 | 0.26 | 0.55 | 0.3421 | 0 (wrong_result) |
| England Croatia 06-17 | home_win | 0.55 | 0.26 | 0.19 | 0.1021 | 1 (correct_result) |
| England Ghana 06-23 | draw | 0.69 | 0.20 | 0.11 | 0.3761 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.82 | 0.12 | 0.06 | 0.0168 | 1 (correct_result) |
| France Senegal 06-16 | home_win | 0.64 | 0.22 | 0.14 | 0.0659 | 2 (correct_result_exact_gd) |
| Germany Curacao 06-14 | home_win | 0.87 | 0.08 | 0.05 | 0.0086 | 1 (correct_result) |
| Germany Ivory Coast 06-20 | home_win | 0.62 | 0.23 | 0.15 | 0.0733 | 4 (exact_score) |
| Ghana Panama 06-17 | home_win | 0.44 | 0.30 | 0.26 | 0.1571 | 0 (wrong_result) |
| Haiti Scotland 06-13 | away_win | 0.16 | 0.23 | 0.61 | 0.0769 | 4 (exact_score) |
| Iran New Zealand 06-15 | draw | 0.49 | 0.28 | 0.23 | 0.2705 | 0 (wrong_result) |
| Iraq Norway 06-16 | away_win | 0.10 | 0.20 | 0.70 | 0.0467 | 1 (correct_result) |
| Ivory Coast Ecuador 06-14 | home_win | 0.31 | 0.35 | 0.34 | 0.2381 | 0 (wrong_result) |
| Japan Sweden 06-25 | draw | 0.34 | 0.33 | 0.33 | 0.2245 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.16 | 0.25 | 0.59 | 0.0854 | 2 (correct_result_exact_gd) |
| Mexico South Africa 06-11 | home_win | 0.60 | 0.24 | 0.16 | 0.0811 | 4 (exact_score) |
| Mexico South Korea 06-18 | home_win | 0.50 | 0.28 | 0.22 | 0.1256 | 4 (exact_score) |
| Morocco Haiti 06-24 | home_win | 0.78 | 0.15 | 0.07 | 0.0253 | 2 (correct_result_exact_gd) |
| Netherlands Japan 06-14 | draw | 0.45 | 0.29 | 0.26 | 0.2581 | 1 (correct_draw) |
| Netherlands Sweden 06-20 | home_win | 0.57 | 0.24 | 0.19 | 0.0929 | 1 (correct_result) |
| New Zealand Egypt 06-21 | away_win | 0.20 | 0.30 | 0.50 | 0.1267 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.38 | 0.32 | 0.30 | 0.1923 | 0 (wrong_result) |
| Panama Croatia 06-23 | away_win | 0.18 | 0.25 | 0.57 | 0.0933 | 1 (correct_result) |
| Paraguay Australia 06-25 | draw | 0.33 | 0.36 | 0.31 | 0.2049 | 1 (correct_draw) |
| Portugal DR Congo 06-17 | draw | 0.73 | 0.18 | 0.09 | 0.4045 | 0 (wrong_result) |
| Portugal Uzbekistan 06-23 | home_win | 0.74 | 0.18 | 0.08 | 0.0355 | 1 (correct_result) |
| Qatar Switzerland 06-13 | draw | 0.12 | 0.21 | 0.67 | 0.3625 | 0 (wrong_result) |
| Saudi Arabia Uruguay 06-15 | draw | 0.12 | 0.27 | 0.61 | 0.3065 | 0 (wrong_result) |
| Scotland Brazil 06-24 | away_win | 0.33 | 0.34 | 0.33 | 0.2245 | 0 (wrong_result) |
| Scotland Morocco 06-19 | away_win | 0.27 | 0.31 | 0.42 | 0.1685 | 0 (wrong_result) |
| South Africa South Korea 06-24 | home_win | 0.20 | 0.26 | 0.54 | 0.3331 | 0 (wrong_result) |
| South Korea Czech Republic 06-11 | home_win | 0.36 | 0.34 | 0.30 | 0.2051 | 0 (wrong_result) |
| Spain Cape Verde 06-15 | draw | 0.73 | 0.18 | 0.09 | 0.4045 | 0 (wrong_result) |
| Spain Saudi Arabia 06-21 | home_win | 0.78 | 0.14 | 0.08 | 0.0248 | 1 (correct_result) |
| Sweden Tunisia 06-14 | home_win | 0.48 | 0.29 | 0.23 | 0.1358 | 1 (correct_result) |
| Switzerland Bosnia and Herzegovina 06-18 | home_win | 0.60 | 0.25 | 0.15 | 0.0817 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.44 | 0.30 | 0.26 | 0.1571 | 0 (wrong_result) |
| Tunisia Japan 06-20 | away_win | 0.22 | 0.28 | 0.50 | 0.1256 | 1 (correct_result) |
| Tunisia Netherlands 06-25 | away_win | 0.13 | 0.23 | 0.64 | 0.0665 | 2 (correct_result_exact_gd) |
| Turkey Paraguay 06-19 | away_win | 0.41 | 0.29 | 0.30 | 0.2474 | 0 (wrong_result) |
| USA Australia 06-19 | home_win | 0.59 | 0.25 | 0.16 | 0.0854 | 1 (correct_result) |
| USA Paraguay 06-12 | home_win | 0.39 | 0.33 | 0.28 | 0.1865 | 0 (wrong_result) |
| USA Turkey 06-25 | away_win | 0.34 | 0.35 | 0.31 | 0.2381 | 0 (wrong_result) |
| Uruguay Cape Verde 06-21 | draw | 0.66 | 0.22 | 0.12 | 0.3528 | 0 (wrong_result) |
| Uzbekistan Colombia 06-17 | away_win | 0.13 | 0.22 | 0.65 | 0.0626 | 1 (correct_result) |

**Worked example** — Argentina Algeria 2026-06-16:

    p_home=0.68, p_draw=0.21, p_away=0.11
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.68 - 1)^2 + (0.21 - 0)^2 + (0.11 - 0)^2] / 3
         = [0.1024 + 0.0441 + 0.0121] / 3
         = 0.0529  (stored: 0.0529)

### gpt54  (mean Brier = 0.1697)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Algeria 06-16 | home_win | 0.69 | 0.21 | 0.10 | 0.0501 | 1 (correct_result) |
| Argentina Austria 06-22 | home_win | 0.58 | 0.25 | 0.17 | 0.0893 | 4 (exact_score) |
| Australia Turkey 06-13 | home_win | 0.19 | 0.24 | 0.57 | 0.3462 | 0 (wrong_result) |
| Austria Jordan 06-16 | home_win | 0.69 | 0.21 | 0.10 | 0.0501 | 2 (correct_result_exact_gd) |
| Belgium Egypt 06-15 | draw | 0.63 | 0.24 | 0.13 | 0.3305 | 0 (wrong_result) |
| Belgium Iran 06-21 | draw | 0.64 | 0.23 | 0.13 | 0.3398 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.58 | 0.26 | 0.16 | 0.0899 | 1 (correct_result) |
| Brazil Haiti 06-19 | home_win | 0.84 | 0.11 | 0.05 | 0.0134 | 4 (exact_score) |
| Brazil Morocco 06-13 | draw | 0.59 | 0.25 | 0.16 | 0.3121 | 0 (wrong_result) |
| Canada Bosnia and Herzegovina 06-12 | draw | 0.41 | 0.31 | 0.28 | 0.2409 | 4 (exact_score) |
| Canada Qatar 06-18 | home_win | 0.72 | 0.19 | 0.09 | 0.0409 | 1 (correct_result) |
| Colombia DR Congo 06-23 | home_win | 0.64 | 0.23 | 0.13 | 0.0665 | 4 (exact_score) |
| Curacao Ivory Coast 06-25 | away_win | 0.07 | 0.17 | 0.76 | 0.0305 | 1 (correct_result) |
| Czech Republic Mexico 06-24 | away_win | 0.48 | 0.27 | 0.25 | 0.2886 | 0 (wrong_result) |
| Czech Republic South Africa 06-18 | draw | 0.42 | 0.32 | 0.26 | 0.2355 | 4 (exact_score) |
| Ecuador Curacao 06-20 | draw | 0.50 | 0.27 | 0.23 | 0.2786 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.21 | 0.26 | 0.53 | 0.3242 | 0 (wrong_result) |
| England Croatia 06-17 | home_win | 0.55 | 0.26 | 0.19 | 0.1021 | 1 (correct_result) |
| England Ghana 06-23 | draw | 0.69 | 0.20 | 0.11 | 0.3761 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.81 | 0.14 | 0.05 | 0.0194 | 4 (exact_score) |
| France Senegal 06-16 | home_win | 0.66 | 0.22 | 0.12 | 0.0595 | 2 (correct_result_exact_gd) |
| Germany Curacao 06-14 | home_win | 0.91 | 0.07 | 0.02 | 0.0045 | 1 (correct_result) |
| Germany Ivory Coast 06-20 | home_win | 0.61 | 0.23 | 0.16 | 0.0769 | 4 (exact_score) |
| Ghana Panama 06-17 | home_win | 0.39 | 0.33 | 0.28 | 0.1865 | 0 (wrong_result) |
| Haiti Scotland 06-13 | away_win | 0.16 | 0.22 | 0.62 | 0.0728 | 1 (correct_result) |
| Iran New Zealand 06-15 | draw | 0.48 | 0.31 | 0.21 | 0.2502 | 0 (wrong_result) |
| Iraq Norway 06-16 | away_win | 0.13 | 0.21 | 0.66 | 0.0589 | 1 (correct_result) |
| Ivory Coast Ecuador 06-14 | home_win | 0.29 | 0.32 | 0.39 | 0.2529 | 0 (wrong_result) |
| Japan Sweden 06-25 | draw | 0.35 | 0.32 | 0.33 | 0.2313 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.17 | 0.24 | 0.59 | 0.0849 | 2 (correct_result_exact_gd) |
| Mexico South Africa 06-11 | home_win | 0.64 | 0.22 | 0.14 | 0.0659 | 4 (exact_score) |
| Mexico South Korea 06-18 | home_win | 0.42 | 0.31 | 0.27 | 0.1685 | 0 (wrong_result) |
| Morocco Haiti 06-24 | home_win | 0.78 | 0.17 | 0.05 | 0.0266 | 2 (correct_result_exact_gd) |
| Netherlands Japan 06-14 | draw | 0.41 | 0.29 | 0.30 | 0.2541 | 1 (correct_draw) |
| Netherlands Sweden 06-20 | home_win | 0.58 | 0.24 | 0.18 | 0.0888 | 1 (correct_result) |
| New Zealand Egypt 06-21 | away_win | 0.21 | 0.28 | 0.51 | 0.1209 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.38 | 0.33 | 0.29 | 0.1925 | 0 (wrong_result) |
| Panama Croatia 06-23 | away_win | 0.17 | 0.24 | 0.59 | 0.0849 | 1 (correct_result) |
| Paraguay Australia 06-25 | draw | 0.34 | 0.35 | 0.31 | 0.2114 | 1 (correct_draw) |
| Portugal DR Congo 06-17 | draw | 0.73 | 0.18 | 0.09 | 0.4045 | 0 (wrong_result) |
| Portugal Uzbekistan 06-23 | home_win | 0.74 | 0.18 | 0.08 | 0.0355 | 1 (correct_result) |
| Qatar Switzerland 06-13 | draw | 0.14 | 0.22 | 0.64 | 0.3459 | 0 (wrong_result) |
| Saudi Arabia Uruguay 06-15 | draw | 0.14 | 0.27 | 0.59 | 0.3002 | 0 (wrong_result) |
| Scotland Brazil 06-24 | away_win | 0.34 | 0.29 | 0.37 | 0.1989 | 0 (wrong_result) |
| Scotland Morocco 06-19 | away_win | 0.27 | 0.31 | 0.42 | 0.1685 | 4 (exact_score) |
| South Africa South Korea 06-24 | home_win | 0.19 | 0.27 | 0.54 | 0.3402 | 0 (wrong_result) |
| South Korea Czech Republic 06-11 | home_win | 0.36 | 0.33 | 0.31 | 0.2049 | 0 (wrong_result) |
| Spain Cape Verde 06-15 | draw | 0.36 | 0.31 | 0.33 | 0.2382 | 1 (correct_draw) |
| Spain Saudi Arabia 06-21 | home_win | 0.79 | 0.15 | 0.06 | 0.0234 | 1 (correct_result) |
| Sweden Tunisia 06-14 | home_win | 0.42 | 0.32 | 0.26 | 0.1688 | 1 (correct_result) |
| Switzerland Bosnia and Herzegovina 06-18 | home_win | 0.62 | 0.24 | 0.14 | 0.0739 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.41 | 0.31 | 0.28 | 0.1742 | 0 (wrong_result) |
| Tunisia Japan 06-20 | away_win | 0.24 | 0.29 | 0.47 | 0.1409 | 1 (correct_result) |
| Tunisia Netherlands 06-25 | away_win | 0.14 | 0.24 | 0.62 | 0.0739 | 2 (correct_result_exact_gd) |
| Turkey Paraguay 06-19 | away_win | 0.41 | 0.29 | 0.30 | 0.2474 | 0 (wrong_result) |
| USA Australia 06-19 | home_win | 0.58 | 0.25 | 0.17 | 0.0893 | 1 (correct_result) |
| USA Paraguay 06-12 | home_win | 0.39 | 0.33 | 0.28 | 0.1865 | 0 (wrong_result) |
| USA Turkey 06-25 | away_win | 0.31 | 0.37 | 0.32 | 0.2318 | 0 (wrong_result) |
| Uruguay Cape Verde 06-21 | draw | 0.67 | 0.22 | 0.11 | 0.3565 | 0 (wrong_result) |
| Uzbekistan Colombia 06-17 | away_win | 0.11 | 0.24 | 0.65 | 0.0641 | 1 (correct_result) |

**Worked example** — Argentina Algeria 2026-06-16:

    p_home=0.69, p_draw=0.21, p_away=0.1
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.69 - 1)^2 + (0.21 - 0)^2 + (0.1 - 0)^2] / 3
         = [0.0961 + 0.0441 + 0.0100] / 3
         = 0.0501  (stored: 0.0501)

### gpt5mini  (mean Brier = 0.1707)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Algeria 06-16 | home_win | 0.70 | 0.20 | 0.10 | 0.0467 | 1 (correct_result) |
| Argentina Austria 06-22 | home_win | 0.40 | 0.36 | 0.24 | 0.1824 | 0 (wrong_result) |
| Australia Turkey 06-13 | home_win | 0.18 | 0.27 | 0.55 | 0.3493 | 0 (wrong_result) |
| Austria Jordan 06-16 | home_win | 0.65 | 0.22 | 0.13 | 0.0626 | 2 (correct_result_exact_gd) |
| Belgium Iran 06-21 | draw | 0.64 | 0.23 | 0.13 | 0.3398 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.55 | 0.30 | 0.15 | 0.1050 | 1 (correct_result) |
| Brazil Morocco 06-13 | draw | 0.58 | 0.26 | 0.16 | 0.3032 | 0 (wrong_result) |
| Canada Qatar 06-18 | home_win | 0.70 | 0.20 | 0.10 | 0.0467 | 1 (correct_result) |
| Curacao Ivory Coast 06-25 | away_win | 0.06 | 0.20 | 0.74 | 0.0371 | 1 (correct_result) |
| Czech Republic South Africa 06-18 | draw | 0.46 | 0.34 | 0.20 | 0.2291 | 0 (wrong_result) |
| Ecuador Curacao 06-20 | draw | 0.60 | 0.25 | 0.15 | 0.3150 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.20 | 0.30 | 0.50 | 0.3267 | 0 (wrong_result) |
| England Croatia 06-17 | home_win | 0.43 | 0.40 | 0.17 | 0.1713 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.78 | 0.18 | 0.04 | 0.0275 | 1 (correct_result) |
| France Senegal 06-16 | home_win | 0.55 | 0.27 | 0.18 | 0.1026 | 2 (correct_result_exact_gd) |
| Germany Curacao 06-14 | home_win | 0.75 | 0.18 | 0.07 | 0.0333 | 1 (correct_result) |
| Germany Ivory Coast 06-20 | home_win | 0.60 | 0.25 | 0.15 | 0.0817 | 1 (correct_result) |
| Ghana Panama 06-17 | home_win | 0.40 | 0.38 | 0.22 | 0.1843 | 0 (wrong_result) |
| Iran New Zealand 06-15 | draw | 0.40 | 0.38 | 0.22 | 0.1976 | 1 (correct_draw) |
| Iraq Norway 06-16 | away_win | 0.10 | 0.18 | 0.72 | 0.0403 | 1 (correct_result) |
| Ivory Coast Ecuador 06-14 | home_win | 0.30 | 0.36 | 0.34 | 0.2451 | 0 (wrong_result) |
| Japan Sweden 06-25 | draw | 0.34 | 0.36 | 0.30 | 0.2051 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.14 | 0.23 | 0.63 | 0.0698 | 1 (correct_result) |
| Mexico South Africa 06-11 | home_win | 0.60 | 0.26 | 0.14 | 0.0824 | 1 (correct_result) |
| Morocco Haiti 06-24 | home_win | 0.78 | 0.17 | 0.05 | 0.0266 | 2 (correct_result_exact_gd) |
| Netherlands Japan 06-14 | draw | 0.48 | 0.28 | 0.24 | 0.2688 | 0 (wrong_result) |
| Netherlands Sweden 06-20 | home_win | 0.52 | 0.28 | 0.20 | 0.1163 | 1 (correct_result) |
| New Zealand Egypt 06-21 | away_win | 0.18 | 0.30 | 0.52 | 0.1176 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.36 | 0.42 | 0.22 | 0.2115 | 0 (wrong_result) |
| Panama Croatia 06-23 | away_win | 0.17 | 0.24 | 0.59 | 0.0849 | 4 (exact_score) |
| Paraguay Australia 06-25 | draw | 0.34 | 0.36 | 0.30 | 0.2051 | 1 (correct_draw) |
| Portugal DR Congo 06-17 | draw | 0.72 | 0.18 | 0.10 | 0.4003 | 0 (wrong_result) |
| Qatar Switzerland 06-13 | draw | 0.10 | 0.18 | 0.72 | 0.4003 | 0 (wrong_result) |
| Saudi Arabia Uruguay 06-15 | draw | 0.13 | 0.22 | 0.65 | 0.3493 | 0 (wrong_result) |
| Scotland Brazil 06-24 | away_win | 0.19 | 0.26 | 0.55 | 0.1021 | 1 (correct_result) |
| Scotland Morocco 06-19 | away_win | 0.25 | 0.40 | 0.35 | 0.2150 | 0 (wrong_result) |
| South Africa South Korea 06-24 | home_win | 0.16 | 0.26 | 0.58 | 0.3699 | 0 (wrong_result) |
| South Korea Czech Republic 06-11 | home_win | 0.34 | 0.36 | 0.30 | 0.2184 | 0 (wrong_result) |
| Spain Cape Verde 06-15 | draw | 0.34 | 0.42 | 0.24 | 0.1699 | 4 (exact_score) |
| Spain Saudi Arabia 06-21 | home_win | 0.80 | 0.13 | 0.07 | 0.0206 | 1 (correct_result) |
| Sweden Tunisia 06-14 | home_win | 0.45 | 0.34 | 0.21 | 0.1541 | 1 (correct_result) |
| Switzerland Bosnia and Herzegovina 06-18 | home_win | 0.58 | 0.27 | 0.15 | 0.0906 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.45 | 0.30 | 0.25 | 0.1517 | 0 (wrong_result) |
| Tunisia Japan 06-20 | away_win | 0.26 | 0.34 | 0.40 | 0.1811 | 0 (wrong_result) |
| Tunisia Netherlands 06-25 | away_win | 0.12 | 0.22 | 0.66 | 0.0595 | 1 (correct_result) |
| Turkey Paraguay 06-19 | away_win | 0.34 | 0.36 | 0.30 | 0.2451 | 0 (wrong_result) |
| USA Australia 06-19 | home_win | 0.55 | 0.30 | 0.15 | 0.1050 | 1 (correct_result) |
| USA Paraguay 06-12 | home_win | 0.40 | 0.42 | 0.18 | 0.1896 | 0 (wrong_result) |
| USA Turkey 06-25 | away_win | 0.36 | 0.34 | 0.30 | 0.2451 | 0 (wrong_result) |
| Uzbekistan Colombia 06-17 | away_win | 0.12 | 0.20 | 0.68 | 0.0523 | 1 (correct_result) |

**Worked example** — Argentina Algeria 2026-06-16:

    p_home=0.7, p_draw=0.2, p_away=0.1
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.7 - 1)^2 + (0.2 - 0)^2 + (0.1 - 0)^2] / 3
         = [0.0900 + 0.0400 + 0.0100] / 3
         = 0.0467  (stored: 0.0467)

### opus  (mean Brier = 0.1711)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Algeria 06-16 | home_win | 0.68 | 0.22 | 0.10 | 0.0536 | 1 (correct_result) |
| Argentina Austria 06-22 | home_win | 0.58 | 0.25 | 0.17 | 0.0893 | 4 (exact_score) |
| Australia Turkey 06-13 | home_win | 0.25 | 0.27 | 0.48 | 0.2886 | 0 (wrong_result) |
| Austria Jordan 06-16 | home_win | 0.68 | 0.22 | 0.10 | 0.0536 | 2 (correct_result_exact_gd) |
| Belgium Egypt 06-15 | draw | 0.55 | 0.28 | 0.17 | 0.2833 | 0 (wrong_result) |
| Belgium Iran 06-21 | draw | 0.63 | 0.22 | 0.15 | 0.3426 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.58 | 0.24 | 0.18 | 0.0888 | 2 (correct_result_exact_gd) |
| Brazil Haiti 06-19 | home_win | 0.92 | 0.06 | 0.02 | 0.0035 | 4 (exact_score) |
| Brazil Morocco 06-13 | draw | 0.55 | 0.27 | 0.18 | 0.2893 | 0 (wrong_result) |
| Canada Bosnia and Herzegovina 06-12 | draw | 0.42 | 0.32 | 0.26 | 0.2355 | 4 (exact_score) |
| Canada Qatar 06-18 | home_win | 0.62 | 0.23 | 0.15 | 0.0733 | 1 (correct_result) |
| Colombia DR Congo 06-23 | home_win | 0.52 | 0.31 | 0.17 | 0.1185 | 4 (exact_score) |
| Curacao Ivory Coast 06-25 | away_win | 0.08 | 0.18 | 0.74 | 0.0355 | 4 (exact_score) |
| Czech Republic Mexico 06-24 | away_win | 0.27 | 0.30 | 0.43 | 0.1626 | 1 (correct_result) |
| Czech Republic South Africa 06-18 | draw | 0.42 | 0.32 | 0.26 | 0.2355 | 4 (exact_score) |
| Ecuador Curacao 06-20 | draw | 0.62 | 0.23 | 0.15 | 0.3333 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.18 | 0.27 | 0.55 | 0.3493 | 0 (wrong_result) |
| England Croatia 06-17 | home_win | 0.50 | 0.28 | 0.22 | 0.1256 | 1 (correct_result) |
| England Ghana 06-23 | draw | 0.65 | 0.22 | 0.13 | 0.3493 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.82 | 0.13 | 0.05 | 0.0173 | 1 (correct_result) |
| France Senegal 06-16 | home_win | 0.58 | 0.25 | 0.17 | 0.0893 | 1 (correct_result) |
| Germany Curacao 06-14 | home_win | 0.88 | 0.09 | 0.03 | 0.0078 | 1 (correct_result) |
| Germany Ivory Coast 06-20 | home_win | 0.55 | 0.25 | 0.20 | 0.1017 | 4 (exact_score) |
| Ghana Panama 06-17 | home_win | 0.40 | 0.30 | 0.30 | 0.1800 | 0 (wrong_result) |
| Haiti Scotland 06-13 | away_win | 0.20 | 0.25 | 0.55 | 0.1017 | 4 (exact_score) |
| Iran New Zealand 06-15 | draw | 0.45 | 0.33 | 0.22 | 0.2333 | 0 (wrong_result) |
| Iraq Norway 06-16 | away_win | 0.12 | 0.18 | 0.70 | 0.0456 | 1 (correct_result) |
| Ivory Coast Ecuador 06-14 | home_win | 0.31 | 0.30 | 0.39 | 0.2394 | 0 (wrong_result) |
| Japan Sweden 06-25 | draw | 0.35 | 0.32 | 0.33 | 0.2313 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.20 | 0.27 | 0.53 | 0.1113 | 2 (correct_result_exact_gd) |
| Mexico South Africa 06-11 | home_win | 0.52 | 0.28 | 0.20 | 0.1163 | 1 (correct_result) |
| Mexico South Korea 06-18 | home_win | 0.42 | 0.30 | 0.28 | 0.1683 | 0 (wrong_result) |
| Morocco Haiti 06-24 | home_win | 0.78 | 0.17 | 0.05 | 0.0266 | 2 (correct_result_exact_gd) |
| Netherlands Japan 06-14 | draw | 0.50 | 0.26 | 0.24 | 0.2851 | 0 (wrong_result) |
| Netherlands Sweden 06-20 | home_win | 0.50 | 0.28 | 0.22 | 0.1256 | 1 (correct_result) |
| New Zealand Egypt 06-21 | away_win | 0.20 | 0.30 | 0.50 | 0.1267 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.41 | 0.32 | 0.27 | 0.1745 | 0 (wrong_result) |
| Panama Croatia 06-23 | away_win | 0.17 | 0.24 | 0.59 | 0.0849 | 1 (correct_result) |
| Paraguay Australia 06-25 | draw | 0.35 | 0.33 | 0.32 | 0.2246 | 1 (correct_draw) |
| Portugal DR Congo 06-17 | draw | 0.70 | 0.20 | 0.10 | 0.3800 | 0 (wrong_result) |
| Portugal Uzbekistan 06-23 | home_win | 0.74 | 0.18 | 0.08 | 0.0355 | 1 (correct_result) |
| Qatar Switzerland 06-13 | draw | 0.10 | 0.22 | 0.68 | 0.3603 | 0 (wrong_result) |
| Saudi Arabia Uruguay 06-15 | draw | 0.10 | 0.22 | 0.68 | 0.3603 | 0 (wrong_result) |
| Scotland Brazil 06-24 | away_win | 0.12 | 0.22 | 0.66 | 0.0595 | 1 (correct_result) |
| Scotland Morocco 06-19 | away_win | 0.27 | 0.31 | 0.42 | 0.1685 | 0 (wrong_result) |
| South Africa South Korea 06-24 | home_win | 0.20 | 0.25 | 0.55 | 0.3350 | 0 (wrong_result) |
| South Korea Czech Republic 06-11 | home_win | 0.36 | 0.31 | 0.33 | 0.2049 | 0 (wrong_result) |
| Spain Cape Verde 06-15 | draw | 0.68 | 0.22 | 0.10 | 0.3603 | 0 (wrong_result) |
| Spain Saudi Arabia 06-21 | home_win | 0.82 | 0.12 | 0.06 | 0.0168 | 1 (correct_result) |
| Sweden Tunisia 06-14 | home_win | 0.42 | 0.33 | 0.25 | 0.1693 | 1 (correct_result) |
| Switzerland Bosnia and Herzegovina 06-18 | home_win | 0.58 | 0.26 | 0.16 | 0.0899 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.45 | 0.30 | 0.25 | 0.1517 | 0 (wrong_result) |
| Tunisia Japan 06-20 | away_win | 0.24 | 0.28 | 0.48 | 0.1355 | 1 (correct_result) |
| Tunisia Netherlands 06-25 | away_win | 0.12 | 0.22 | 0.66 | 0.0595 | 2 (correct_result_exact_gd) |
| Turkey Paraguay 06-19 | away_win | 0.43 | 0.28 | 0.29 | 0.2558 | 0 (wrong_result) |
| USA Australia 06-19 | home_win | 0.55 | 0.27 | 0.18 | 0.1026 | 1 (correct_result) |
| USA Paraguay 06-12 | home_win | 0.40 | 0.33 | 0.27 | 0.1806 | 0 (wrong_result) |
| USA Turkey 06-25 | away_win | 0.33 | 0.36 | 0.31 | 0.2382 | 0 (wrong_result) |
| Uruguay Cape Verde 06-21 | draw | 0.58 | 0.27 | 0.15 | 0.2973 | 0 (wrong_result) |
| Uzbekistan Colombia 06-17 | away_win | 0.18 | 0.27 | 0.55 | 0.1026 | 1 (correct_result) |

**Worked example** — Argentina Algeria 2026-06-16:

    p_home=0.68, p_draw=0.22, p_away=0.1
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.68 - 1)^2 + (0.22 - 0)^2 + (0.1 - 0)^2] / 3
         = [0.1024 + 0.0484 + 0.0100] / 3
         = 0.0536  (stored: 0.0536)

### sonarpro  (mean Brier = 0.1713)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Austria 06-22 | home_win | 0.49 | 0.28 | 0.23 | 0.1305 | 1 (correct_result) |
| Belgium Iran 06-21 | draw | 0.62 | 0.23 | 0.15 | 0.3333 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.63 | 0.23 | 0.14 | 0.0698 | 1 (correct_result) |
| Colombia DR Congo 06-23 | home_win | 0.63 | 0.23 | 0.14 | 0.0698 | 4 (exact_score) |
| Curacao Ivory Coast 06-25 | away_win | 0.09 | 0.18 | 0.73 | 0.0378 | 1 (correct_result) |
| Czech Republic Mexico 06-24 | away_win | 0.34 | 0.30 | 0.36 | 0.2051 | 0 (wrong_result) |
| Ecuador Curacao 06-20 | draw | 0.55 | 0.26 | 0.19 | 0.2954 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.23 | 0.27 | 0.50 | 0.3053 | 0 (wrong_result) |
| England Ghana 06-23 | draw | 0.68 | 0.18 | 0.14 | 0.3848 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.78 | 0.15 | 0.07 | 0.0253 | 4 (exact_score) |
| Germany Ivory Coast 06-20 | home_win | 0.56 | 0.23 | 0.21 | 0.0969 | 4 (exact_score) |
| Japan Sweden 06-25 | draw | 0.37 | 0.30 | 0.33 | 0.2453 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.22 | 0.30 | 0.48 | 0.1363 | 2 (correct_result_exact_gd) |
| Morocco Haiti 06-24 | home_win | 0.68 | 0.19 | 0.13 | 0.0518 | 2 (correct_result_exact_gd) |
| Netherlands Sweden 06-20 | home_win | 0.52 | 0.27 | 0.21 | 0.1158 | 1 (correct_result) |
| New Zealand Egypt 06-21 | away_win | 0.27 | 0.29 | 0.44 | 0.1569 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.42 | 0.31 | 0.27 | 0.1685 | 2 (correct_result_exact_gd) |
| Panama Croatia 06-23 | away_win | 0.19 | 0.27 | 0.54 | 0.1069 | 4 (exact_score) |
| Paraguay Australia 06-25 | draw | 0.36 | 0.34 | 0.30 | 0.2184 | 1 (correct_draw) |
| Portugal Uzbekistan 06-23 | home_win | 0.73 | 0.17 | 0.10 | 0.0373 | 1 (correct_result) |
| Scotland Brazil 06-24 | away_win | 0.33 | 0.27 | 0.40 | 0.1806 | 1 (correct_result) |
| South Africa South Korea 06-24 | home_win | 0.18 | 0.26 | 0.56 | 0.3512 | 0 (wrong_result) |
| Spain Saudi Arabia 06-21 | home_win | 0.78 | 0.15 | 0.07 | 0.0253 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.37 | 0.33 | 0.30 | 0.1986 | 0 (wrong_result) |
| Tunisia Japan 06-20 | away_win | 0.27 | 0.28 | 0.45 | 0.1513 | 1 (correct_result) |
| Tunisia Netherlands 06-25 | away_win | 0.18 | 0.27 | 0.55 | 0.1026 | 1 (correct_result) |
| USA Turkey 06-25 | away_win | 0.34 | 0.33 | 0.33 | 0.2245 | 0 (wrong_result) |
| Uruguay Cape Verde 06-21 | draw | 0.68 | 0.20 | 0.12 | 0.3723 | 0 (wrong_result) |

**Worked example** — Argentina Austria 2026-06-22:

    p_home=0.49, p_draw=0.28, p_away=0.23
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.49 - 1)^2 + (0.28 - 0)^2 + (0.23 - 0)^2] / 3
         = [0.2601 + 0.0784 + 0.0529] / 3
         = 0.1305  (stored: 0.1305)

### gem31flashlite  (mean Brier = 0.1744)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Algeria 06-16 | home_win | 0.68 | 0.22 | 0.10 | 0.0536 | 1 (correct_result) |
| Argentina Austria 06-22 | home_win | 0.62 | 0.25 | 0.13 | 0.0746 | 4 (exact_score) |
| Australia Turkey 06-13 | home_win | 0.22 | 0.28 | 0.50 | 0.3123 | 0 (wrong_result) |
| Austria Jordan 06-16 | home_win | 0.72 | 0.18 | 0.10 | 0.0403 | 2 (correct_result_exact_gd) |
| Belgium Egypt 06-15 | draw | 0.58 | 0.27 | 0.15 | 0.2973 | 0 (wrong_result) |
| Belgium Iran 06-21 | draw | 0.68 | 0.22 | 0.10 | 0.3603 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.52 | 0.32 | 0.16 | 0.1195 | 1 (correct_result) |
| Brazil Haiti 06-19 | home_win | 0.92 | 0.06 | 0.02 | 0.0035 | 4 (exact_score) |
| Brazil Morocco 06-13 | draw | 0.55 | 0.28 | 0.17 | 0.2833 | 0 (wrong_result) |
| Canada Bosnia and Herzegovina 06-12 | draw | 0.42 | 0.35 | 0.23 | 0.2173 | 4 (exact_score) |
| Canada Qatar 06-18 | home_win | 0.72 | 0.18 | 0.10 | 0.0403 | 1 (correct_result) |
| Colombia DR Congo 06-23 | home_win | 0.62 | 0.26 | 0.12 | 0.0755 | 4 (exact_score) |
| Curacao Ivory Coast 06-25 | away_win | 0.08 | 0.14 | 0.78 | 0.0248 | 1 (correct_result) |
| Czech Republic Mexico 06-24 | away_win | 0.42 | 0.32 | 0.26 | 0.2755 | 0 (wrong_result) |
| Czech Republic South Africa 06-18 | draw | 0.42 | 0.35 | 0.23 | 0.2173 | 4 (exact_score) |
| Ecuador Curacao 06-20 | draw | 0.62 | 0.23 | 0.15 | 0.3333 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.28 | 0.35 | 0.37 | 0.2593 | 0 (wrong_result) |
| England Croatia 06-17 | home_win | 0.44 | 0.35 | 0.21 | 0.1601 | 0 (wrong_result) |
| England Ghana 06-23 | draw | 0.72 | 0.18 | 0.10 | 0.4003 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.85 | 0.12 | 0.03 | 0.0126 | 4 (exact_score) |
| France Senegal 06-16 | home_win | 0.62 | 0.24 | 0.14 | 0.0739 | 2 (correct_result_exact_gd) |
| Germany Curacao 06-14 | home_win | 0.92 | 0.06 | 0.02 | 0.0035 | 1 (correct_result) |
| Germany Ivory Coast 06-20 | home_win | 0.62 | 0.23 | 0.15 | 0.0733 | 4 (exact_score) |
| Ghana Panama 06-17 | home_win | 0.40 | 0.35 | 0.25 | 0.1817 | 0 (wrong_result) |
| Haiti Scotland 06-13 | away_win | 0.14 | 0.22 | 0.64 | 0.0659 | 1 (correct_result) |
| Iran New Zealand 06-15 | draw | 0.48 | 0.32 | 0.20 | 0.2443 | 0 (wrong_result) |
| Iraq Norway 06-16 | away_win | 0.12 | 0.20 | 0.68 | 0.0523 | 1 (correct_result) |
| Ivory Coast Ecuador 06-14 | home_win | 0.32 | 0.36 | 0.32 | 0.2315 | 0 (wrong_result) |
| Japan Sweden 06-25 | draw | 0.38 | 0.32 | 0.30 | 0.2323 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.18 | 0.32 | 0.50 | 0.1283 | 2 (correct_result_exact_gd) |
| Mexico South Africa 06-11 | home_win | 0.65 | 0.22 | 0.13 | 0.0626 | 4 (exact_score) |
| Mexico South Korea 06-18 | home_win | 0.42 | 0.35 | 0.23 | 0.1706 | 0 (wrong_result) |
| Morocco Haiti 06-24 | home_win | 0.82 | 0.13 | 0.05 | 0.0173 | 2 (correct_result_exact_gd) |
| Netherlands Japan 06-14 | draw | 0.42 | 0.32 | 0.26 | 0.2355 | 1 (correct_draw) |
| Netherlands Sweden 06-20 | home_win | 0.52 | 0.28 | 0.20 | 0.1163 | 1 (correct_result) |
| New Zealand Egypt 06-21 | away_win | 0.18 | 0.32 | 0.50 | 0.1283 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.42 | 0.32 | 0.26 | 0.1688 | 0 (wrong_result) |
| Panama Croatia 06-23 | away_win | 0.18 | 0.22 | 0.60 | 0.0803 | 2 (correct_result_exact_gd) |
| Paraguay Australia 06-25 | draw | 0.38 | 0.32 | 0.30 | 0.2323 | 1 (correct_draw) |
| Portugal DR Congo 06-17 | draw | 0.74 | 0.18 | 0.08 | 0.4088 | 0 (wrong_result) |
| Portugal Uzbekistan 06-23 | home_win | 0.78 | 0.16 | 0.06 | 0.0259 | 1 (correct_result) |
| Qatar Switzerland 06-13 | draw | 0.12 | 0.19 | 0.69 | 0.3822 | 0 (wrong_result) |
| Saudi Arabia Uruguay 06-15 | draw | 0.10 | 0.20 | 0.70 | 0.3800 | 0 (wrong_result) |
| Scotland Brazil 06-24 | away_win | 0.15 | 0.20 | 0.65 | 0.0617 | 4 (exact_score) |
| Scotland Morocco 06-19 | away_win | 0.28 | 0.38 | 0.34 | 0.2195 | 0 (wrong_result) |
| South Africa South Korea 06-24 | home_win | 0.15 | 0.25 | 0.60 | 0.3817 | 0 (wrong_result) |
| South Korea Czech Republic 06-11 | home_win | 0.36 | 0.34 | 0.30 | 0.2051 | 0 (wrong_result) |
| Spain Cape Verde 06-15 | draw | 0.82 | 0.12 | 0.06 | 0.4835 | 4 (exact_score) |
| Spain Saudi Arabia 06-21 | home_win | 0.82 | 0.13 | 0.05 | 0.0173 | 1 (correct_result) |
| Sweden Tunisia 06-14 | home_win | 0.42 | 0.35 | 0.23 | 0.1706 | 0 (wrong_result) |
| Switzerland Bosnia and Herzegovina 06-18 | home_win | 0.62 | 0.25 | 0.13 | 0.0746 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.42 | 0.32 | 0.26 | 0.1688 | 0 (wrong_result) |
| Tunisia Japan 06-20 | away_win | 0.22 | 0.31 | 0.47 | 0.1418 | 1 (correct_result) |
| Tunisia Netherlands 06-25 | away_win | 0.15 | 0.20 | 0.65 | 0.0617 | 1 (correct_result) |
| Turkey Paraguay 06-19 | away_win | 0.42 | 0.32 | 0.26 | 0.2755 | 0 (wrong_result) |
| USA Australia 06-19 | home_win | 0.52 | 0.30 | 0.18 | 0.1176 | 1 (correct_result) |
| USA Paraguay 06-12 | home_win | 0.38 | 0.34 | 0.28 | 0.1928 | 0 (wrong_result) |
| USA Turkey 06-25 | away_win | 0.35 | 0.35 | 0.30 | 0.2450 | 0 (wrong_result) |
| Uruguay Cape Verde 06-21 | draw | 0.65 | 0.25 | 0.10 | 0.3317 | 0 (wrong_result) |
| Uzbekistan Colombia 06-17 | away_win | 0.12 | 0.22 | 0.66 | 0.0595 | 2 (correct_result_exact_gd) |

**Worked example** — Argentina Algeria 2026-06-16:

    p_home=0.68, p_draw=0.22, p_away=0.1
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.68 - 1)^2 + (0.22 - 0)^2 + (0.1 - 0)^2] / 3
         = [0.1024 + 0.0484 + 0.0100] / 3
         = 0.0536  (stored: 0.0536)

### haiku  (mean Brier = 0.1770)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Algeria 06-16 | home_win | 0.62 | 0.22 | 0.16 | 0.0728 | 1 (correct_result) |
| Argentina Austria 06-22 | home_win | 0.62 | 0.22 | 0.16 | 0.0728 | 4 (exact_score) |
| Australia Turkey 06-13 | home_win | 0.28 | 0.22 | 0.50 | 0.2723 | 0 (wrong_result) |
| Austria Jordan 06-16 | home_win | 0.68 | 0.18 | 0.14 | 0.0515 | 2 (correct_result_exact_gd) |
| Belgium Egypt 06-15 | draw | 0.62 | 0.22 | 0.16 | 0.3395 | 0 (wrong_result) |
| Belgium Iran 06-21 | draw | 0.62 | 0.22 | 0.16 | 0.3395 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.48 | 0.32 | 0.20 | 0.1376 | 1 (correct_result) |
| Brazil Haiti 06-19 | home_win | 0.72 | 0.16 | 0.12 | 0.0395 | 1 (correct_result) |
| Brazil Morocco 06-13 | draw | 0.58 | 0.26 | 0.16 | 0.3032 | 0 (wrong_result) |
| Canada Bosnia and Herzegovina 06-12 | draw | 0.42 | 0.35 | 0.23 | 0.2173 | 4 (exact_score) |
| Canada Qatar 06-18 | home_win | 0.62 | 0.22 | 0.16 | 0.0728 | 1 (correct_result) |
| Colombia DR Congo 06-23 | home_win | 0.52 | 0.28 | 0.20 | 0.1163 | 4 (exact_score) |
| Curacao Ivory Coast 06-25 | away_win | 0.04 | 0.12 | 0.84 | 0.0139 | 4 (exact_score) |
| Czech Republic Mexico 06-24 | away_win | 0.38 | 0.32 | 0.30 | 0.2456 | 0 (wrong_result) |
| Czech Republic South Africa 06-18 | draw | 0.42 | 0.35 | 0.23 | 0.2173 | 0 (wrong_result) |
| Ecuador Curacao 06-20 | draw | 0.62 | 0.22 | 0.16 | 0.3395 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.12 | 0.22 | 0.66 | 0.4195 | 0 (wrong_result) |
| England Croatia 06-17 | home_win | 0.52 | 0.28 | 0.20 | 0.1163 | 1 (correct_result) |
| England Ghana 06-23 | draw | 0.62 | 0.22 | 0.16 | 0.3395 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.68 | 0.18 | 0.14 | 0.0515 | 1 (correct_result) |
| France Senegal 06-16 | home_win | 0.62 | 0.22 | 0.16 | 0.0728 | 2 (correct_result_exact_gd) |
| Germany Curacao 06-14 | home_win | 0.78 | 0.12 | 0.10 | 0.0243 | 1 (correct_result) |
| Germany Ivory Coast 06-20 | home_win | 0.62 | 0.22 | 0.16 | 0.0728 | 1 (correct_result) |
| Ghana Panama 06-17 | home_win | 0.42 | 0.35 | 0.23 | 0.1706 | 0 (wrong_result) |
| Haiti Scotland 06-13 | away_win | 0.12 | 0.22 | 0.66 | 0.0595 | 1 (correct_result) |
| Iran New Zealand 06-15 | draw | 0.42 | 0.38 | 0.20 | 0.2003 | 0 (wrong_result) |
| Iraq Norway 06-16 | away_win | 0.18 | 0.22 | 0.60 | 0.0803 | 1 (correct_result) |
| Ivory Coast Ecuador 06-14 | home_win | 0.33 | 0.34 | 0.33 | 0.2245 | 0 (wrong_result) |
| Japan Sweden 06-25 | draw | 0.36 | 0.32 | 0.32 | 0.2315 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.28 | 0.32 | 0.40 | 0.1803 | 0 (wrong_result) |
| Mexico South Africa 06-11 | home_win | 0.42 | 0.28 | 0.30 | 0.1683 | 1 (correct_result) |
| Mexico South Korea 06-18 | home_win | 0.42 | 0.32 | 0.26 | 0.1688 | 0 (wrong_result) |
| Morocco Haiti 06-24 | home_win | 0.72 | 0.18 | 0.10 | 0.0403 | 2 (correct_result_exact_gd) |
| Netherlands Japan 06-14 | draw | 0.52 | 0.24 | 0.24 | 0.3019 | 0 (wrong_result) |
| Netherlands Sweden 06-20 | home_win | 0.52 | 0.28 | 0.20 | 0.1163 | 1 (correct_result) |
| New Zealand Egypt 06-21 | away_win | 0.18 | 0.32 | 0.50 | 0.1283 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.42 | 0.28 | 0.30 | 0.1683 | 2 (correct_result_exact_gd) |
| Panama Croatia 06-23 | away_win | 0.18 | 0.24 | 0.58 | 0.0888 | 2 (correct_result_exact_gd) |
| Paraguay Australia 06-25 | draw | 0.38 | 0.36 | 0.26 | 0.2072 | 1 (correct_draw) |
| Portugal DR Congo 06-17 | draw | 0.68 | 0.18 | 0.14 | 0.3848 | 0 (wrong_result) |
| Portugal Uzbekistan 06-23 | home_win | 0.68 | 0.18 | 0.14 | 0.0515 | 1 (correct_result) |
| Qatar Switzerland 06-13 | draw | 0.18 | 0.28 | 0.54 | 0.2808 | 0 (wrong_result) |
| Saudi Arabia Uruguay 06-15 | draw | 0.12 | 0.24 | 0.64 | 0.3339 | 0 (wrong_result) |
| Scotland Brazil 06-24 | away_win | 0.08 | 0.12 | 0.80 | 0.0203 | 4 (exact_score) |
| Scotland Morocco 06-19 | away_win | 0.28 | 0.38 | 0.34 | 0.2195 | 0 (wrong_result) |
| South Africa South Korea 06-24 | home_win | 0.18 | 0.28 | 0.54 | 0.3475 | 0 (wrong_result) |
| South Korea Czech Republic 06-11 | home_win | 0.38 | 0.35 | 0.27 | 0.1933 | 0 (wrong_result) |
| Spain Cape Verde 06-15 | draw | 0.68 | 0.22 | 0.10 | 0.3603 | 4 (exact_score) |
| Spain Saudi Arabia 06-21 | home_win | 0.72 | 0.18 | 0.10 | 0.0403 | 1 (correct_result) |
| Sweden Tunisia 06-14 | home_win | 0.42 | 0.32 | 0.26 | 0.1688 | 1 (correct_result) |
| Switzerland Bosnia and Herzegovina 06-18 | home_win | 0.58 | 0.26 | 0.16 | 0.0899 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.42 | 0.32 | 0.26 | 0.1688 | 0 (wrong_result) |
| Tunisia Japan 06-20 | away_win | 0.28 | 0.30 | 0.42 | 0.1683 | 1 (correct_result) |
| Tunisia Netherlands 06-25 | away_win | 0.12 | 0.24 | 0.64 | 0.0672 | 1 (correct_result) |
| Turkey Paraguay 06-19 | away_win | 0.42 | 0.28 | 0.30 | 0.2483 | 0 (wrong_result) |
| USA Australia 06-19 | home_win | 0.52 | 0.28 | 0.20 | 0.1163 | 1 (correct_result) |
| USA Paraguay 06-12 | home_win | 0.42 | 0.30 | 0.28 | 0.1683 | 1 (correct_result) |
| USA Turkey 06-25 | away_win | 0.32 | 0.38 | 0.30 | 0.2456 | 0 (wrong_result) |
| Uruguay Cape Verde 06-21 | draw | 0.62 | 0.22 | 0.16 | 0.3395 | 0 (wrong_result) |
| Uzbekistan Colombia 06-17 | away_win | 0.22 | 0.28 | 0.50 | 0.1256 | 1 (correct_result) |

**Worked example** — Argentina Algeria 2026-06-16:

    p_home=0.62, p_draw=0.22, p_away=0.16
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.62 - 1)^2 + (0.22 - 0)^2 + (0.16 - 0)^2] / 3
         = [0.1444 + 0.0484 + 0.0256] / 3
         = 0.0728  (stored: 0.0728)

### gem25flashlite  (mean Brier = 0.1781)

| Match | Actual | p_home | p_draw | p_away | Brier | Fantasy Pts |
|---|---|---|---|---|---|---|
| Argentina Algeria 06-16 | home_win | 0.68 | 0.22 | 0.10 | 0.0536 | 1 (correct_result) |
| Argentina Austria 06-22 | home_win | 0.48 | 0.27 | 0.25 | 0.1353 | 1 (correct_result) |
| Australia Turkey 06-13 | home_win | 0.25 | 0.25 | 0.50 | 0.2917 | 0 (wrong_result) |
| Austria Jordan 06-16 | home_win | 0.69 | 0.25 | 0.06 | 0.0541 | 2 (correct_result_exact_gd) |
| Belgium Egypt 06-15 | draw | 0.58 | 0.27 | 0.15 | 0.2973 | 0 (wrong_result) |
| Belgium Iran 06-21 | draw | 0.65 | 0.23 | 0.12 | 0.3433 | 0 (wrong_result) |
| Bosnia and Herzegovina Qatar 06-24 | home_win | 0.45 | 0.35 | 0.20 | 0.1550 | 1 (correct_result) |
| Brazil Haiti 06-19 | home_win | 0.89 | 0.10 | 0.01 | 0.0074 | 4 (exact_score) |
| Brazil Morocco 06-13 | draw | 0.58 | 0.27 | 0.15 | 0.2973 | 0 (wrong_result) |
| Canada Bosnia and Herzegovina 06-12 | draw | 0.48 | 0.32 | 0.20 | 0.2443 | 0 (wrong_result) |
| Canada Qatar 06-18 | home_win | 0.65 | 0.25 | 0.10 | 0.0650 | 1 (correct_result) |
| Colombia DR Congo 06-23 | home_win | 0.45 | 0.35 | 0.20 | 0.1550 | 4 (exact_score) |
| Curacao Ivory Coast 06-25 | away_win | 0.04 | 0.18 | 0.78 | 0.0275 | 1 (correct_result) |
| Czech Republic Mexico 06-24 | away_win | 0.30 | 0.35 | 0.35 | 0.2117 | 1 (correct_result) |
| Czech Republic South Africa 06-18 | draw | 0.35 | 0.40 | 0.25 | 0.1817 | 4 (exact_score) |
| Ecuador Curacao 06-20 | draw | 0.60 | 0.25 | 0.15 | 0.3150 | 0 (wrong_result) |
| Ecuador Germany 06-25 | home_win | 0.15 | 0.25 | 0.60 | 0.3817 | 0 (wrong_result) |
| England Croatia 06-17 | home_win | 0.39 | 0.41 | 0.20 | 0.1934 | 0 (wrong_result) |
| England Ghana 06-23 | draw | 0.68 | 0.22 | 0.10 | 0.3603 | 0 (wrong_result) |
| France Iraq 06-22 | home_win | 0.78 | 0.18 | 0.04 | 0.0275 | 1 (correct_result) |
| France Senegal 06-16 | home_win | 0.55 | 0.25 | 0.20 | 0.1017 | 1 (correct_result) |
| Germany Curacao 06-14 | home_win | 0.95 | 0.04 | 0.01 | 0.0014 | 1 (correct_result) |
| Germany Ivory Coast 06-20 | home_win | 0.52 | 0.28 | 0.20 | 0.1163 | 4 (exact_score) |
| Ghana Panama 06-17 | home_win | 0.34 | 0.38 | 0.28 | 0.2195 | 0 (wrong_result) |
| Haiti Scotland 06-13 | away_win | 0.15 | 0.22 | 0.63 | 0.0693 | 4 (exact_score) |
| Iran New Zealand 06-15 | draw | 0.47 | 0.35 | 0.18 | 0.2253 | 0 (wrong_result) |
| Iraq Norway 06-16 | away_win | 0.15 | 0.25 | 0.60 | 0.0817 | 1 (correct_result) |
| Ivory Coast Ecuador 06-14 | home_win | 0.31 | 0.35 | 0.34 | 0.2381 | 0 (wrong_result) |
| Japan Sweden 06-25 | draw | 0.35 | 0.35 | 0.30 | 0.2117 | 4 (exact_score) |
| Jordan Algeria 06-22 | away_win | 0.27 | 0.34 | 0.39 | 0.1869 | 2 (correct_result_exact_gd) |
| Mexico South Africa 06-11 | home_win | 0.45 | 0.30 | 0.25 | 0.1517 | 1 (correct_result) |
| Mexico South Korea 06-18 | home_win | 0.35 | 0.40 | 0.25 | 0.2150 | 0 (wrong_result) |
| Morocco Haiti 06-24 | home_win | 0.85 | 0.13 | 0.02 | 0.0133 | 2 (correct_result_exact_gd) |
| Netherlands Japan 06-14 | draw | 0.37 | 0.34 | 0.29 | 0.2189 | 1 (correct_draw) |
| Netherlands Sweden 06-20 | home_win | 0.38 | 0.37 | 0.25 | 0.1946 | 0 (wrong_result) |
| New Zealand Egypt 06-21 | away_win | 0.19 | 0.29 | 0.52 | 0.1169 | 1 (correct_result) |
| Norway Senegal 06-22 | home_win | 0.34 | 0.38 | 0.28 | 0.2195 | 0 (wrong_result) |
| Panama Croatia 06-23 | away_win | 0.15 | 0.25 | 0.60 | 0.0817 | 1 (correct_result) |
| Paraguay Australia 06-25 | draw | 0.34 | 0.35 | 0.31 | 0.2114 | 1 (correct_draw) |
| Portugal DR Congo 06-17 | draw | 0.71 | 0.22 | 0.07 | 0.3725 | 0 (wrong_result) |
| Portugal Uzbekistan 06-23 | home_win | 0.78 | 0.18 | 0.04 | 0.0275 | 1 (correct_result) |
| Qatar Switzerland 06-13 | draw | 0.10 | 0.25 | 0.65 | 0.3317 | 0 (wrong_result) |
| Saudi Arabia Uruguay 06-15 | draw | 0.05 | 0.20 | 0.75 | 0.4017 | 0 (wrong_result) |
| Scotland Brazil 06-24 | away_win | 0.07 | 0.18 | 0.75 | 0.0333 | 4 (exact_score) |
| Scotland Morocco 06-19 | away_win | 0.26 | 0.35 | 0.39 | 0.1874 | 0 (wrong_result) |
| South Africa South Korea 06-24 | home_win | 0.18 | 0.31 | 0.51 | 0.3429 | 0 (wrong_result) |
| South Korea Czech Republic 06-11 | home_win | 0.34 | 0.33 | 0.33 | 0.2178 | 0 (wrong_result) |
| Spain Cape Verde 06-15 | draw | 0.45 | 0.30 | 0.25 | 0.2517 | 0 (wrong_result) |
| Spain Saudi Arabia 06-21 | home_win | 0.80 | 0.15 | 0.05 | 0.0217 | 1 (correct_result) |
| Sweden Tunisia 06-14 | home_win | 0.55 | 0.28 | 0.17 | 0.1033 | 1 (correct_result) |
| Switzerland Bosnia and Herzegovina 06-18 | home_win | 0.58 | 0.27 | 0.15 | 0.0906 | 1 (correct_result) |
| Switzerland Canada 06-24 | home_win | 0.46 | 0.28 | 0.26 | 0.1459 | 2 (correct_result_exact_gd) |
| Tunisia Japan 06-20 | away_win | 0.25 | 0.30 | 0.45 | 0.1517 | 1 (correct_result) |
| Tunisia Netherlands 06-25 | away_win | 0.15 | 0.25 | 0.60 | 0.0817 | 2 (correct_result_exact_gd) |
| Turkey Paraguay 06-19 | away_win | 0.35 | 0.36 | 0.29 | 0.2521 | 0 (wrong_result) |
| USA Australia 06-19 | home_win | 0.51 | 0.27 | 0.22 | 0.1205 | 1 (correct_result) |
| USA Paraguay 06-12 | home_win | 0.35 | 0.40 | 0.25 | 0.2150 | 0 (wrong_result) |
| USA Turkey 06-25 | away_win | 0.35 | 0.40 | 0.25 | 0.2817 | 0 (wrong_result) |
| Uruguay Cape Verde 06-21 | draw | 0.55 | 0.30 | 0.15 | 0.2717 | 0 (wrong_result) |
| Uzbekistan Colombia 06-17 | away_win | 0.16 | 0.30 | 0.54 | 0.1091 | 1 (correct_result) |

**Worked example** — Argentina Algeria 2026-06-16:

    p_home=0.68, p_draw=0.22, p_away=0.1
    actual=home_win  =>  I_home=1, I_draw=0, I_away=0
    Brier = [(0.68 - 1)^2 + (0.22 - 0)^2 + (0.1 - 0)^2] / 3
         = [0.1024 + 0.0484 + 0.0100] / 3
         = 0.0536  (stored: 0.0536)

---

## Baseline Reference

| Strategy | Brier |
|---|---|
| Perfect prediction | 0.0000 |
| Uniform random (1/3 each) | 0.2222 |
| Always predict home win (p_home=1) | ~0.1852 (typical) |
| This ensemble (best: gem25flash) | 0.1604 |
| This ensemble (worst: gem25flashlite) | 0.1781 |
| Overall mean | 0.1701 |