from pathlib import Path
import random
import pandas as pd

input_dir = Path("data/EN/expanded")
files = sorted(input_dir.glob("*.tsv"))

if not files:
    raise FileNotFoundError(f"No TSV files found in {input_dir.resolve()}")

df = pd.concat(
    [pd.read_csv(file, sep="\t") for file in files],
    ignore_index=True,
)
df = df.rename(
    columns={column: column.lower() for column in df.columns if column != "MRNI-item"}
)

affirmation_items = pd.read_csv(Path("data/MRNI_items/MRNI_EN.tsv"), sep="\t")
df["MRNI-item"] = df["MRNI-item"].astype(str).str.strip()
affirmation_items["id"] = affirmation_items["id"].astype(str).str.strip()
df = df.merge(
    affirmation_items[["id", "text"]].rename(
        columns={"id": "MRNI-item", "text": "MRNI-text"}
    ),
    on="MRNI-item",
    how="left",
    validate="many_to_one",
)
if df["MRNI-text"].isna().any():
    missing_ids = sorted(df.loc[df["MRNI-text"].isna(), "MRNI-item"].unique())
    raise ValueError(f"No MRNI text found for item IDs: {missing_ids}")

df.insert(df.columns.get_loc("MRNI-item") + 1, "MRNI-text", df.pop("MRNI-text"))
df["language"] = "en"
column_order = [
    "instance_id",
    "category",
    "MRNI-item",
    "MRNI-text",
    "scenario",
    "condition",
    "mapping",
    "context",
    "question",
    "answer_options",
    "gold_answer",
    "prompt",
    "language",
]
df = df[column_order + [column for column in df.columns if column not in column_order]]

rng = random.Random()
for row_index, options_text in enumerate(df["answer_options"]):
    options = options_text.split(" | ")
    rng.shuffle(options)
    df.at[row_index, "answer_options"] = " | ".join(options)
    df.at[row_index, "prompt"] = (
        f"Context: {df.at[row_index, 'context']}\n"
        f"Question: {df.at[row_index, 'question']}\n"
        f"Answer with exactly one of the following options: {', '.join(options)}."
    )

output_file = Path("data/EN/MNRI-BB_en_expanded_all_conditions.tsv")
df.to_csv(output_file, sep="\t", index=False)

print(f"Combined {len(files)} files: {df.shape[0]} rows, {df.shape[1]} columns")
print(f"Saved to {output_file.resolve()}")


it_input_dir = Path("data/IT/expanded")
it_files = sorted(it_input_dir.glob("*.tsv"))

if not it_files:
    raise FileNotFoundError(f"No TSV files found in {it_input_dir.resolve()}")

it_df = pd.concat(
    [pd.read_csv(file, sep="\t") for file in it_files],
    ignore_index=True,
)
it_df = it_df.rename(
    columns={
        column: column.lower()
        for column in it_df.columns
        if column != "MRNI-item"
    }
)

it_mrni_items = pd.read_csv(Path("data/MRNI_items/MRNI_IT.tsv"), sep="\t")
it_df["MRNI-item"] = it_df["MRNI-item"].astype(str).str.strip()
it_mrni_items["id"] = it_mrni_items["id"].astype(str).str.strip()
it_df = it_df.merge(
    it_mrni_items[["id", "text"]].rename(
        columns={"id": "MRNI-item", "text": "MRNI-text"}
    ),
    on="MRNI-item",
    how="left",
    validate="many_to_one",
)
if it_df["MRNI-text"].isna().any():
    missing_ids = sorted(it_df.loc[it_df["MRNI-text"].isna(), "MRNI-item"].unique())
    raise ValueError(f"No MRNI text found for item IDs: {missing_ids}")

it_df.insert(
    it_df.columns.get_loc("MRNI-item") + 1,
    "MRNI-text",
    it_df.pop("MRNI-text"),
)
it_df["language"] = "it"
it_column_order = [
    "instance_id",
    "category",
    "MRNI-item",
    "MRNI-text",
    "scenario",
    "condition",
    "mapping",
    "context",
    "question",
    "answer_options",
    "gold_answer",
    "prompt",
    "language",
]
it_df = it_df[
    it_column_order
    + [column for column in it_df.columns if column not in it_column_order]
]

it_rng = random.Random()
for row_index, options_text in enumerate(it_df["answer_options"]):
    options = options_text.split(" | ")
    it_rng.shuffle(options)
    it_df.at[row_index, "answer_options"] = " | ".join(options)
    it_df.at[row_index, "prompt"] = (
        f"Contesto: {it_df.at[row_index, 'context']}\n"
        f"Domanda: {it_df.at[row_index, 'question']}\n"
        f"Rispondi con una sola delle seguenti opzioni: {', '.join(options)}."
    )

it_output_file = Path("data/IT/MNRI-BB_it_expanded_all_conditions.tsv")
it_df.to_csv(it_output_file, sep="\t", index=False)

print(f"Combined {len(it_files)} files: {it_df.shape[0]} rows, {it_df.shape[1]} columns")
print(f"Saved to {it_output_file.resolve()}")