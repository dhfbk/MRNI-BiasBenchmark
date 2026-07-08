# Italian MRNI-BB Data

This folder contains the Italian version of MRNI-BB.

For each MRNI-R subscale, we provide two versions of the data:

1. **Compact/template files**  
   These are the shorter and more easily inspectable files.

2. **Expanded all-condition files**  
   These are the fully expanded, evaluation-ready files used for model prompting.

The expanded files can be regenerated from the compact files using the provided Python script.

---

## Folder structure

```text
IT/
├── AF_MNRI-BB_it.tsv
├── D_MNRI-BB_it.tsv
├── IOS_MNRI-BB_it.tsv
├── NTSM_MNRI-BB_it.tsv
├── RE_MNRI-BB_it.tsv
├── SRTMS_MNRI-BB_it.tsv
├── T_MNRI-BB_it.tsv
├── get_all_conditions_it.py
├── README.md
└── all_conditions/
    ├── AF_MNRI-BB_it_all.tsv
    ├── D_MNRI-BB_it_all.tsv
    ├── IOS_MNRI-BB_it_all.tsv
    ├── NTSM_MNRI-BB_it_all.tsv
    ├── RE_MNRI-BB_it_all.tsv
    ├── SRTMS_MNRI-BB_it_all.tsv
    └── T_MNRI-BB_it_all.tsv
```
## What the generation script does

The script `get_all_conditions_it.py` expands the compact/template files into the full evaluation-ready files in `all_conditions/`.

In particular, it:

- replaces the base placeholder `{{X} e {Y}}` with all required introductions:
  - `Due persone, X e Y`
  - `Due persone, Y e X`
  - `Un uomo e una donna`
  - `Una donna e un uomo`

- replaces `{X}` and `{Y}` with the appropriate labels depending on the condition:
  - gender-agnostic: `La persona X`, `La persona Y`
  - gender-specified: `L'uomo`, `La donna`

- expands agreement placeholders such as `{X-end}` and `{Y-end}`:
  - `o` for masculine forms, e.g. `sentito`, `scosso`
  - `a` for feminine forms, e.g. `sentita`, `scossa`

- expands genitive placeholders:
  - `{X-of}` / `{Y-of}` → `dell'uomo`, `della donna`, `della persona X/Y`
  - `{X-apostrophe}` / `{Y-apostrophe}` → full forms such as `dell'uomo` or `della donna`

- generates all condition variants:
  - `disambiguated_ga`
  - `disambiguated_gs`
  - `ambiguous_ga`
  - `ambiguous_gs`
  - `control_gs`

- assigns the correct `gold_answer` and valid `answer_options` for each generated prompt.

The compact files are therefore the source version, while the files in `all_conditions/` are the generated evaluation-ready version.    