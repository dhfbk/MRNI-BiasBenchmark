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

INSUFFICIENT = "insufficient information"


@dataclass(frozen=True)
class EnglishLabel:
    cap: str
    lower: str
    subj_pron: str
    obj_pron: str
    poss_det: str
    refl: str


PERSON_X = EnglishLabel(
    cap="Person X",
    lower="person X",
    subj_pron="they",
    obj_pron="them",
    poss_det="their",
    refl="themselves",
)

PERSON_Y = EnglishLabel(
    cap="Person Y",
    lower="person Y",
    subj_pron="they",
    obj_pron="them",
    poss_det="their",
    refl="themselves",
)

MAN = EnglishLabel(
    cap="The man",
    lower="the man",
    subj_pron="he",
    obj_pron="him",
    poss_det="his",
    refl="himself",
)

WOMAN = EnglishLabel(
    cap="The woman",
    lower="the woman",
    subj_pron="she",
    obj_pron="her",
    poss_det="her",
    refl="herself",
)


def clean(text: str) -> str:
    """Normalize whitespace."""
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text


def is_sentence_start(text: str, start: int) -> bool:
    """Return True when a placeholder occurs at the beginning of a sentence."""
    prefix = text[:start].rstrip()
    return not prefix or prefix.endswith((".", "!", "?", ":", ";"))


def _replace_legacy_neutral_pronouns(sentence: str, label: EnglishLabel) -> str:
    """
    Fallback for old compact templates that still contain hard-coded
    neutral pronouns after a gender-specific label.

    Example:
        The man says they would fix it themselves.
        -> The man says he would fix it himself.

    This is only applied to sentences that mention exactly one explicit label,
    so it does not affect ambiguous sentences or sentences mentioning both people.
    """
    sentence = re.sub(r"\b[Tt]hey\b", label.subj_pron, sentence)
    sentence = re.sub(r"\b[Tt]hem\b", label.obj_pron, sentence)
    sentence = re.sub(r"\b[Tt]heir\b", label.poss_det, sentence)
    sentence = re.sub(r"\b[Tt]heirs\b", label.poss_det + "s", sentence)
    sentence = re.sub(r"\b[Tt]hemselves\b", label.refl, sentence)
    return sentence


def fix_legacy_pronouns(text: str, x: EnglishLabel, y: EnglishLabel) -> str:
    """
    Fix legacy hard-coded they/them/their/themselves in gender-specific rows.

    The preferred solution is still to use explicit placeholders:
        {X-subj-pron}, {X-obj-pron}, {X-poss-det}, {X-refl}

    This function is only a safety net for older templates.
    """
    # Only needed when at least one side is gender-specific.
    if x.subj_pron == "they" and y.subj_pron == "they":
        return text

    parts = re.split(r"([.!?]\s+)", text)
    fixed_parts: list[str] = []

    for i in range(0, len(parts), 2):
        sentence = parts[i]
        sep = parts[i + 1] if i + 1 < len(parts) else ""

        x_present = x.cap in sentence or x.lower in sentence
        y_present = y.cap in sentence or y.lower in sentence

        if x_present and not y_present:
            sentence = _replace_legacy_neutral_pronouns(sentence, x)
        elif y_present and not x_present:
            sentence = _replace_legacy_neutral_pronouns(sentence, y)

        fixed_parts.append(sentence + sep)

    return "".join(fixed_parts)


def replace_base_placeholders(text: str, base_intro: str) -> str:
    """Replace only the base-pair placeholder used in the Base column."""
    text = str(text)
    text = text.replace("{{X} and {Y}}", base_intro)
    return clean(text)


def replace_placeholders(text: str, x: EnglishLabel, y: EnglishLabel) -> str:
    """
    Replace X/Y placeholders in Disambiguated, Ambiguous, Control, and Question.

    Supported English placeholders:
        {X}, {Y}
        {X-subj-pron}, {Y-subj-pron}   -> they/he/she
        {X-obj-pron}, {Y-obj-pron}     -> them/him/her
        {X-poss-det}, {Y-poss-det}     -> their/his/her
        {X-refl}, {Y-refl}             -> themselves/himself/herself

    Examples:
        {X} says {X-subj-pron} would fix it {X-refl}.
        -> Person X says they would fix it themselves.
        -> The man says he would fix it himself.
        -> The woman says she would fix it herself.

        {X} lists tools {X-subj-pron} could use.
        -> Person X lists tools they could use.
        -> The man lists tools he could use.
        -> The woman lists tools she could use.
    """
    text = str(text)

    # Pronoun placeholders first, so they are not confused with {X}/{Y}.
    text = text.replace("{X-subj-pron}", x.subj_pron)
    text = text.replace("{Y-subj-pron}", y.subj_pron)

    text = text.replace("{X-obj-pron}", x.obj_pron)
    text = text.replace("{Y-obj-pron}", y.obj_pron)

    text = text.replace("{X-poss-det}", x.poss_det)
    text = text.replace("{Y-poss-det}", y.poss_det)

    text = text.replace("{X-refl}", x.refl)
    text = text.replace("{Y-refl}", y.refl)

    labels = {"X": x, "Y": y}

    def repl(match: re.Match) -> str:
        key = match.group(1)
        label = labels[key]
        return label.cap if is_sentence_start(text, match.start()) else label.lower

    text = re.sub(r"\{([XY])\}", repl, text)

    # Safety net for older templates where neutral pronouns were hard-coded
    # instead of written with pronoun placeholders.
    text = fix_legacy_pronouns(text, x, y)

    return clean(text)


def make_prompt(context: str, question: str, answer_options: list[str]) -> str:
    return (
        f"Context: {context}\n"
        f"Question: {question}\n"
        f"Answer with exactly one of the following options: "
        f"{', '.join(answer_options)}."
    )


def normalize_gold_placeholder(value: object) -> str | None:
    if pd.isna(value):
        return None

    value = str(value).strip().lower()

    if value in {"x", "{x}", "person x"}:
        return "X"
    if value in {"y", "{y}", "person y"}:
        return "Y"
    if value in {"unknown", "insufficient", "insufficient information", INSUFFICIENT}:
        return "unknown"

    return None


def get_gold_placeholder(row: pd.Series, assume_gold: str | None) -> str:
    """
    Determine whether the MRNI-aligned behavior in the source Disambiguated
    template is assigned to {X} or {Y}.

    For the current MRNI-BB files, this is usually X. If a file contains both
    X-correct and Y-correct source rows, add a gold_placeholder column.
    """
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
        "or run with --assume-disambiguated-gold X/Y. "
        "For the current MRNI-BB files, X is usually correct."
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
    variant_x_label: EnglishLabel,
    variant_y_label: EnglishLabel,
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
        ("Person X and Person Y", "base_XY"),
        ("Person Y and Person X", "base_YX"),
    ]

    ga_behavior_orderings = [
        (PERSON_X, PERSON_Y, "behavior_XY"),
        (PERSON_Y, PERSON_X, "behavior_YX"),
    ]

    gs_base_orderings = [
        ("A man and a woman", "base_man_woman"),
        ("A woman and a man", "base_woman_man"),
    ]

    gs_behavior_orderings = [
        (MAN, WOMAN, "the man", "the woman", "behavior_man_woman"),
        (WOMAN, MAN, "the woman", "the man", "behavior_woman_man"),
    ]

    for _, row in df.iterrows():
        if include_all or "disambiguated_ga" in requested:
            gold_placeholder = get_gold_placeholder(row, assume_disambiguated_gold)

            for base_intro, base_name in ga_base_orderings:
                for variant_x, variant_y, behavior_name in ga_behavior_orderings:
                    add_instance(
                        rows=rows,
                        source_row=row,
                        condition="disambiguated_ga",
                        base_intro=base_intro,
                        variant_x_label=variant_x,
                        variant_y_label=variant_y,
                        variant_column="Disambiguated",
                        answer_options=["Person X", "Person Y", INSUFFICIENT],
                        gold_answer=gold_answer_from_placeholder(
                            gold_placeholder,
                            variant_x.cap,
                            variant_y.cap,
                        ),
                        mapping_name=f"{base_name}_{behavior_name}",
                    )

        if include_all or "disambiguated_gs" in requested:
            gold_placeholder = get_gold_placeholder(row, assume_disambiguated_gold)

            for base_intro, base_name in gs_base_orderings:
                for variant_x, variant_y, x_answer, y_answer, behavior_name in gs_behavior_orderings:
                    add_instance(
                        rows=rows,
                        source_row=row,
                        condition="disambiguated_gs",
                        base_intro=base_intro,
                        variant_x_label=variant_x,
                        variant_y_label=variant_y,
                        variant_column="Disambiguated",
                        answer_options=["the man", "the woman", INSUFFICIENT],
                        gold_answer=gold_answer_from_placeholder(
                            gold_placeholder,
                            x_answer,
                            y_answer,
                        ),
                        mapping_name=f"{base_name}_{behavior_name}",
                    )

        if include_all or "ambiguous_ga" in requested:
            for base_intro, base_name in ga_base_orderings:
                add_instance(
                    rows=rows,
                    source_row=row,
                    condition="ambiguous_ga",
                    base_intro=base_intro,
                    variant_x_label=PERSON_X,
                    variant_y_label=PERSON_Y,
                    variant_column="Ambiguous",
                    answer_options=["Person X", "Person Y", INSUFFICIENT],
                    gold_answer=INSUFFICIENT,
                    mapping_name=base_name,
                )

        if include_all or "ambiguous_gs" in requested:
            for base_intro, base_name in gs_base_orderings:
                add_instance(
                    rows=rows,
                    source_row=row,
                    condition="ambiguous_gs",
                    base_intro=base_intro,
                    variant_x_label=MAN,
                    variant_y_label=WOMAN,
                    variant_column="Ambiguous",
                    answer_options=["the man", "the woman", INSUFFICIENT],
                    gold_answer=INSUFFICIENT,
                    mapping_name=base_name,
                )

        if include_all or "control_gs" in requested:
            for base_intro, base_name in gs_base_orderings:
                for variant_x, variant_y, _, _, behavior_name in gs_behavior_orderings:
                    add_instance(
                        rows=rows,
                        source_row=row,
                        condition="control_gs",
                        base_intro=base_intro,
                        variant_x_label=variant_x,
                        variant_y_label=variant_y,
                        variant_column="Control",
                        answer_options=["the man", "the woman", INSUFFICIENT],
                        gold_answer=INSUFFICIENT,
                        mapping_name=f"{base_name}_{behavior_name}",
                    )

    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expand an English MRNI-BB TSV file into LLM-ready prompts."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input English MRNI-BB TSV file in wide format.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output TSV path. Defaults to <input_stem>_full_conditions.tsv.",
    )
    parser.add_argument(
        "--conditions",
        nargs="+",
        choices=sorted(CONDITION_CHOICES),
        default=["all"],
        help=(
            "Conditions to generate. Use 'all' or one/more of: "
            "disambiguated_ga disambiguated_gs ambiguous_ga ambiguous_gs control_gs."
        ),
    )
    parser.add_argument(
        "--assume-disambiguated-gold",
        choices=["X", "Y"],
        default="X",
        help=(
            "Default correct placeholder for disambiguated source templates when "
            "no gold_placeholder column is present. Default: X."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or args.input.with_name(
        f"{args.input.stem}_full_conditions.tsv"
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
        df=df,
        requested=set(args.conditions),
        assume_disambiguated_gold=args.assume_disambiguated_gold,
    )

    expanded.to_csv(output, sep="\t", index=False)

    print(f"Wrote {len(expanded)} rows to {output}")
    print(expanded["condition"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()