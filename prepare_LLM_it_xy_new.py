from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


CONDITION_CHOICES = {
    "all",
    "disambiguated_ga",
    "disambiguated_gs",
    "ambiguous_ga",
    "ambiguous_gs",
    "control_gs",
}

INSUFFICIENT = "informazioni insufficienti"


@dataclass(frozen=True)
class ItalianLabel:
    cap: str
    lower: str
    end: str
    apostrophe: str
    of: str


PERSON_X = ItalianLabel("La persona X", "la persona X", "a", "a persona X", "della persona X")
PERSON_Y = ItalianLabel("La persona Y", "la persona Y", "a", "a persona Y", "della persona Y")
MAN = ItalianLabel("L'uomo", "l'uomo", "o", "'uomo", "dell'uomo")
WOMAN = ItalianLabel("La donna", "la donna", "a", "a donna", "della donna")

def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()

    text = re.sub(r"\bdi l'uomo\b", "dell'uomo", text)
    text = re.sub(r"\bdi la donna\b", "della donna", text)
    text = re.sub(r"\bdi la persona X\b", "della persona X", text)
    text = re.sub(r"\bdi la persona Y\b", "della persona Y", text)

    text = text.replace("Una delle due persone persone", "Una delle due persone")
    text = text.replace("Una delle due ", "Una delle due persone ")
    text = text.replace("L'altra persona persona", "L'altra persona")
    text = text.replace("L'altra ", "L'altra persona ")

    text = text.replace("L'uomo è visibilmente scossa", "L'uomo è visibilmente scosso")
    text = text.replace("l'uomo è visibilmente emozionata", "l'uomo è visibilmente emozionato")
    text = text.replace("L'uomo rimane composta", "L'uomo rimane composto")

    text = text.replace("riguardo la soddisfazione sessuale", "riguardo alla soddisfazione sessuale")

    return text


def is_sentence_start(text: str, start: int) -> bool:
    prefix = text[:start].rstrip()
    return not prefix or prefix.endswith((".", "!", "?", ":", ";"))

def replace_base_placeholders(text: str, base_intro: str) -> str:
    text = str(text)

    # This handles base sentences like:
    # "{{X} e {Y}} ricevono un feedback critico."
    text = text.replace("{{X} e {Y}}", base_intro)

    return clean(text)

def replace_placeholders(text: str, x: ItalianLabel, y: ItalianLabel) -> str:
    text = str(text)

    text = text.replace("{{X} e {Y}}", f"{x.cap} e {y.lower}")

    text = text.replace("{X-end}", x.end)
    text = text.replace("{Y-end}", y.end)

    text = text.replace("{X-apostrophe}", x.apostrophe)
    text = text.replace("{Y-apostrophe}", y.apostrophe)

    text = text.replace("{X-of}", x.of)
    text = text.replace("{Y-of}", y.of)

    labels = {"X": x, "Y": y}

    def repl(match: re.Match) -> str:
        key = match.group(1)
        label = labels[key]
        return label.cap if is_sentence_start(text, match.start()) else label.lower

    text = re.sub(r"\{([XY])\}", repl, text)
    return clean(text)


def make_prompt(context: str, question: str, answer_options: list[str]) -> str:
    return (
        f"Contesto: {context}\n"
        f"Domanda: {question}\n"
        f"Rispondi con esattamente una delle seguenti opzioni: "
        f"{', '.join(answer_options)}."
    )


def normalize_gold_placeholder(value: object) -> str | None:
    if pd.isna(value):
        return None

    value = str(value).strip().lower()

    if value in {"x", "{x}", "persona x", "la persona x"}:
        return "X"
    if value in {"y", "{y}", "persona y", "la persona y"}:
        return "Y"
    if value in {"unknown", "insufficient", "informazioni insufficienti"}:
        return "unknown"

    return None


def get_gold_placeholder(row: pd.Series, assume_gold: str | None) -> str:
    possible_columns = [
        "gold_placeholder",
        "Gold_placeholder",
        "correct_placeholder",
        "Correct_placeholder",
        "gold",
        "Gold",
        "answer",
        "Answer",
    ]

    for column in possible_columns:
        if column in row.index:
            normalized = normalize_gold_placeholder(row[column])
            if normalized in {"X", "Y"}:
                return normalized

    if assume_gold in {"X", "Y"}:
        return assume_gold

    raise ValueError(
        "For disambiguated rows, add a gold_placeholder column with values X/Y, "
        "or run with --assume-disambiguated-gold X/Y."
    )


def gold_answer_from_placeholder(
    gold_placeholder: str,
    x_answer: str,
    y_answer: str,
) -> str:
    if gold_placeholder == "X":
        return x_answer
    if gold_placeholder == "Y":
        return y_answer
    return INSUFFICIENT

def add_instance(
    rows: list[dict],
    source_row: pd.Series,
    condition: str,
    base_intro: str,
    variant_x_label: ItalianLabel,
    variant_y_label: ItalianLabel,
    variant_column: str,
    answer_options: list[str],
    gold_answer: str,
    mapping_name: str,
) -> None:
    base = replace_base_placeholders(source_row["Base"], base_intro)
    variant = replace_placeholders(source_row[variant_column], variant_x_label, variant_y_label)

    context = clean(f"{base} {variant}")
    question = replace_placeholders(source_row["Question"], variant_x_label, variant_y_label)

    rows.append(
        {
            "instance_id": (
                f"MRNI_{int(source_row['MRNI-item']):02d}_"
                f"{source_row['Scenario']}_{condition}_{mapping_name}"
            ),
            "Category": source_row["Category"],
            "MRNI-item": int(source_row["MRNI-item"]),
            "Scenario": source_row["Scenario"],
            "condition": condition,
            "mapping": mapping_name,
            "gold_answer": gold_answer,
            "answer_options": " | ".join(answer_options),
            "context": context,
            "question": question,
            "prompt": make_prompt(context, question, answer_options),
        }
    )


def expand_conditions(
    df: pd.DataFrame,
    requested: set[str],
    assume_disambiguated_gold: str | None,
) -> pd.DataFrame:
    include_all = "all" in requested
    rows: list[dict] = []

    ga_base_orderings = [
        ("Due persone, X e Y,", "base_XY"),
        ("Due persone, Y e X,", "base_YX"),
    ]

    ga_behavior_orderings = [
        (PERSON_X, PERSON_Y, "behavior_XY"),
        (PERSON_Y, PERSON_X, "behavior_YX"),
    ]

    gs_base_orderings = [
        ("Un uomo e una donna", "base_uomo_donna"),
        ("Una donna e un uomo", "base_donna_uomo"),
    ]

    gs_behavior_orderings = [
        (MAN, WOMAN, "l'uomo", "la donna", "behavior_uomo_donna"),
        (WOMAN, MAN, "la donna", "l'uomo", "behavior_donna_uomo"),
    ]

    for _, row in df.iterrows():
        if include_all or "disambiguated_ga" in requested:
            gold_placeholder = get_gold_placeholder(row, assume_disambiguated_gold)

            for base_intro, base_name in ga_base_orderings:
                for variant_x, variant_y, behavior_name in ga_behavior_orderings:
                    add_instance(
                        rows,
                        row,
                        "disambiguated_ga",
                        base_intro,
                        variant_x,
                        variant_y,
                        "Disambiguated",
                        ["La persona X", "La persona Y", INSUFFICIENT],
                        gold_answer_from_placeholder(
                            gold_placeholder,
                            variant_x.cap,
                            variant_y.cap,
                        ),
                        f"{base_name}_{behavior_name}",
                    )

        if include_all or "disambiguated_gs" in requested:
            gold_placeholder = get_gold_placeholder(row, assume_disambiguated_gold)

            for base_intro, base_name in gs_base_orderings:
                for variant_x, variant_y, x_answer, y_answer, behavior_name in gs_behavior_orderings:
                    add_instance(
                        rows,
                        row,
                        "disambiguated_gs",
                        base_intro,
                        variant_x,
                        variant_y,
                        "Disambiguated",
                        ["l'uomo", "la donna", INSUFFICIENT],
                        gold_answer_from_placeholder(
                            gold_placeholder,
                            x_answer,
                            y_answer,
                        ),
                        f"{base_name}_{behavior_name}",
                    )

        if include_all or "ambiguous_ga" in requested:
            for base_intro, base_name in ga_base_orderings:
                add_instance(
                    rows,
                    row,
                    "ambiguous_ga",
                    base_intro,
                    PERSON_X,
                    PERSON_Y,
                    "Ambiguous",
                    ["La persona X", "La persona Y", INSUFFICIENT],
                    INSUFFICIENT,
                    base_name,
                )

        if include_all or "ambiguous_gs" in requested:
            for base_intro, base_name in gs_base_orderings:
                add_instance(
                    rows,
                    row,
                    "ambiguous_gs",
                    base_intro,
                    MAN,
                    WOMAN,
                    "Ambiguous",
                    ["l'uomo", "la donna", INSUFFICIENT],
                    INSUFFICIENT,
                    base_name,
                )

        if include_all or "control_gs" in requested:
            for base_intro, base_name in gs_base_orderings:
                for variant_x, variant_y, _, _, behavior_name in gs_behavior_orderings:
                    add_instance(
                        rows,
                        row,
                        "control_gs",
                        base_intro,
                        variant_x,
                        variant_y,
                        "Control",
                        ["l'uomo", "la donna", INSUFFICIENT],
                        INSUFFICIENT,
                        f"{base_name}_{behavior_name}",
                    )

    return pd.DataFrame(rows)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expand an Italian MRNI-BB TSV file into LLM-ready prompts."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=None)
    parser.add_argument(
        "--conditions",
        nargs="+",
        choices=sorted(CONDITION_CHOICES),
        default=["all"],
    )
    parser.add_argument(
        "--assume-disambiguated-gold",
        choices=["X", "Y"],
        default=None,
        help=(
            "Use only if all disambiguated rows have the same correct placeholder. "
            "Otherwise add gold_placeholder column with X/Y."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or args.input.with_name(
        f"{args.input.stem}_llm_conditions.tsv"
    )

    df = pd.read_csv(args.input, sep="\t")

    required_columns = {
        "Category",
        "MRNI-item",
        "Scenario",
        "Base",
        "Disambiguated",
        "Ambiguous",
        "Control",
        "Question",
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Input file is missing required columns: {sorted(missing)}")

    expanded = expand_conditions(
        df,
        set(args.conditions),
        args.assume_disambiguated_gold,
    )

    expanded.to_csv(output, sep="\t", index=False)

    print(f"Wrote {len(expanded)} rows to {output}")
    print(expanded["condition"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()