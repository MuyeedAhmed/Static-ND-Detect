import pandas as pd
import os

def GetList(df):
    functions = df["Function"].dropna().unique()
    filtered = [f for f in functions if "_add_taint" not in f]
    filtered = [f for f in filtered if "test" not in f]

    processed = [
        ".".join(f.split(".")[:-1])
        for f in filtered
        if "." in f
    ]

    result = sorted(set(processed))
    return result

def AddModule(file_path, l):
    df = pd.read_excel(file_path, engine="openpyxl")
    new_file_path = file_path[:-5] + "_modified.xlsx"

    df["Module"] = (
        df["Function"]
            .dropna()
            .where(~df["Function"].str.contains("_add_taint|test", case=False, na=False))
            .str.rsplit(".", n=1)
            .str[0]
        )
    df.to_excel(new_file_path, index=False)

def dropDuplicates(file_path):
    filtered_df = df[
        ~df["Function"].str.contains("_add_taint|test", case=False, na=False)
    ]

    new_df = (
        filtered_df[["Path", "File", "Function"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    new_file_path = os.path.join(os.path.dirname(file_path), os.path.basename(file_path)[:-5] + "_deduplicated.xlsx")
    new_df.to_excel(new_file_path, index=False)

for file in os.listdir("../Results"):
    if file.endswith(".xlsx"):
        df = pd.read_excel(os.path.join("../Results", file), engine="openpyxl")
        # l = GetList(df)
        # AddModule(os.path.join("../Results", file), l)
        dropDuplicates(os.path.join("../Results", file))