"""
Compute participant-level C2C and C2M statistics from ASC distance files.

The script processes one or more directories containing Cloud-to-Cloud (C2C)
and Cloud-to-Mesh (C2M) distance outputs. For each participant, descriptive
distance statistics and tolerance percentages are calculated and exported to
an Excel spreadsheet.

Country-level summaries are balanced equally between CT and ST/M groups, and
the final global score assigns equal weight to Brazil and Colombia.
"""

import os
import re

import numpy as np
import pandas as pd


# Directories containing the ASC files generated for each evaluated method.
INPUT_DIRS = [

    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\ICP\HRN\HRN1\Mid",
    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\NoICP\HRN\HRN1\Mid",

    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\ICP\HRN\HRN3\Mid",
    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\NoICP\HRN\HRN3\Mid",

    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\ICP\HRN\HRN5\Mid",
    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\NoICP\HRN\HRN5\Mid",

    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\ICP\HRN\HRN10\Mid",
    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\NoICP\HRN\HRN10\Mid",

    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\ICP\HRN\HRN5\High",
    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\NoICP\HRN\HRN5\High",

    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\ICP\HRN\HRN10\High",
    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\NoICP\HRN\HRN10\High",

    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\ICP\MP",
    # r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results\NoICP\MP",

]


# Participant IDs excluded during quality control.
EXCLUDED_IDS = {
    "BRSTM0556",
    "BRCTC0542",
    "BRSTM0278",
    "BRSTM0294",
    "BRSTP0090",
    "BRSTP0370",
}


for INPUT_DIR in INPUT_DIRS:

    print("\n" + "=" * 70)
    print(INPUT_DIR)
    print("=" * 70)

    # Automatically determine the evaluated method from the directory path.
    parts = INPUT_DIR.split(os.sep)

    if "HRN" in parts:
        hrn = next(
            p for p in parts
            if re.fullmatch(r"HRN\d+", p)
        )  # HRN5 or HRN10
        mesh = os.path.basename(INPUT_DIR).lower()  # mid or high
        method = f"{hrn}_{mesh}"
    else:
        method = os.path.basename(INPUT_DIR)  # MP, SPG, etc.

    # Add an ICP identifier only when the input directory corresponds to
    # ICP-aligned outputs.
    if "ICP" in parts and "NoICP" not in parts:
        suffix = "_ICP"
    else:
        suffix = ""

    OUTPUT_PATH = os.path.join(
        INPUT_DIR,
        f"{method}{suffix}_C2C_C2M.xlsx"
    )

    # Distance tolerances used to quantify fine-scale correspondence.
    tolerance_1mm = 1.0
    tolerance_05mm = 0.5

    results = []

    for file_name in sorted(os.listdir(INPUT_DIR)):
        if not file_name.lower().endswith(".asc"):
            continue

        patient_id = re.split(
            r"[_-]",
            os.path.splitext(file_name)[0]
        )[0]

        # Exclude predefined quality-control cases and ST/P relatives.
        if (
            patient_id in EXCLUDED_IDS
            or patient_id.startswith(("BRSTP", "COSTP"))
        ):
            print(f"Skipping {patient_id}")
            continue

        file_path = os.path.join(INPUT_DIR, file_name)

        # Optional single-file selection for debugging purposes.
        # if file_name != "BRCTC0519_ICP_C2C_C2M.asc":
        #     continue

        print(f"Processing {file_name}")

        # Define the expected ASC structure according to the acquisition or
        # reconstruction configuration used to generate the model.
        if "MP" in parts:
            cols = [
                "X", "Y", "Z",
                "R", "G", "B", "A",
                "Approx_distances",
                "C2C_absolute_distances",
                "C2M_signed_distances"
            ]

        elif (
            "HRN" in parts
            and os.path.basename(INPUT_DIR).lower() == "mid"
        ):
            cols = [
                "X", "Y", "Z",
                "R", "G", "B", "A",
                "texture_u", "texture_v",
                "Approx_distances",
                "C2C_absolute_distances",
                "C2M_signed_distances"
            ]

        elif (
            "HRN" in parts
            and os.path.basename(INPUT_DIR).lower() == "high"
        ):
            cols = [
                "X", "Y", "Z",
                "Approx_distances",
                "C2C_absolute_distances",
                "C2M_signed_distances"
            ]

        else:
            raise ValueError("Unrecognized data type.")

        try:
            df = pd.read_csv(
                file_path,
                sep=r"\s+",
                skiprows=1,
                names=cols,
                engine="python"
            )
        except Exception as e:
            print(f"Error {file_name}: {e}")
            continue

        # Convert all imported columns to numeric values and replace invalid
        # entries with NaN.
        for c in cols:
            df[c] = pd.to_numeric(
                df[c],
                errors="coerce"
            )

        # Retain only samples with valid C2C and C2M measurements.
        df = df.dropna(
            subset=[
                "C2C_absolute_distances",
                "C2M_signed_distances"
            ]
        )

        if df.empty:
            continue

        c2c = df["C2C_absolute_distances"].to_numpy()

        # C2M statistics are computed from absolute magnitudes to prevent
        # positive and negative signed distances from cancelling each other.
        c2m = np.abs(
            df["C2M_signed_distances"].to_numpy()
        )

        # Optional diagnostic output retained for manual validation.
        # print(file_name)
        #
        # print("N =", len(c2c))
        #
        # print("C2C:", np.min(c2c), np.max(c2c))
        # print("C2M:", np.min(c2m), np.max(c2m))
        #
        # print("C2C Mean =", np.mean(c2c))
        # print("C2C points <=1 mm =", np.sum(c2c <= 1))
        # print("C2C % <=1 mm =", np.mean(c2c <= 1) * 100)
        #
        # print("C2M Mean =", np.mean(c2m))
        # print("C2M points <=1 mm =", np.sum(c2m <= 1))
        # print("C2M % <=1 mm =", np.mean(c2m <= 1) * 100)
        #
        # exit()

        # Store participant-level descriptive statistics and tolerance
        # percentages for both distance descriptors.
        results.append({
            "ID": (
                os.path.splitext(file_name)[0]
                .replace("_ICP_C2C_C2M", "")
                .replace("_C2C_C2M", "")
            ),
            "Total Samples": len(df),
            "C2C Mean (mm)": np.mean(c2c),
            # "C2C Std (mm)": (
            #     np.std(c2c, ddof=1)
            #     if len(c2c) > 1 else 0
            # ),
            "C2C Std (mm)": np.std(c2c),
            "C2C Max (mm)": np.max(c2c),
            "C2C Min (mm)": np.min(c2c),
            "C2C % <=1mm": (
                np.mean(
                    np.abs(c2c) <= tolerance_1mm
                ) * 100
            ),
            "C2C % <=0.5mm": (
                np.mean(
                    np.abs(c2c) <= tolerance_05mm
                ) * 100
            ),
            "C2M Mean (mm)": np.mean(c2m),
            # "C2M Std (mm)": (
            #     np.std(c2m, ddof=1)
            #     if len(c2m) > 1 else 0
            # ),
            "C2M Std (mm)": np.std(c2m),
            "C2M Max (mm)": np.max(c2m),
            "C2M Min (mm)": np.min(c2m),
            "C2M % <=1mm": (
                np.mean(
                    np.abs(c2m) <= tolerance_1mm
                ) * 100
            ),
            "C2M % <=0.5mm": (
                np.mean(
                    np.abs(c2m) <= tolerance_05mm
                ) * 100
            ),
        })

    df_results = pd.DataFrame(results)

    if df_results.empty:
        print("No results were found.")
        exit()

    df_results = df_results.sort_values("ID")
    df_results.reset_index(
        drop=True,
        inplace=True
    )

    # ============================================================
    # GLOBAL AND COUNTRY-LEVEL SUMMARY SCORES
    #
    # Within each country:
    #   CT   = 50%
    #   ST/M = 50%
    #
    # Overall:
    #   BR = 50%
    #   CO = 50%
    # ============================================================

    def balanced_country_mean(df, country):
        """Calculate the balanced mean for one country.

        CT and ST/M participants contribute equally to the country-level
        summary, independently of their respective sample sizes.

        Args:
            df: DataFrame containing participant-level results.
            country: Country prefix used in participant identifiers.

        Returns:
            A pandas Series containing the balanced numeric mean.

        Raises:
            ValueError: If either the CT or ST/M group is absent.
        """
        df_country = df[
            df["ID"].str.startswith(country)
        ]

        df_ct = df_country[
            df_country["ID"].str.startswith(
                country + "CT"
            )
        ]

        df_stm = df_country[
            df_country["ID"].str.startswith(
                country + "STM"
            )
        ]

        if df_ct.empty or df_stm.empty:
            raise ValueError(
                f"CT or ST/M is missing for {country}"
            )

        mean_ct = df_ct.mean(
            numeric_only=True
        )
        mean_stm = df_stm.mean(
            numeric_only=True
        )

        # Equal weighting: 50% CT + 50% ST/M.
        balanced_mean = (
            mean_ct + mean_stm
        ) / 2

        return balanced_mean

    # Brazil: CT and ST/M contribute equally.
    global_mean_br = balanced_country_mean(
        df_results,
        "BR"
    )

    # Colombia: CT and ST/M contribute equally.
    global_mean_co = balanced_country_mean(
        df_results,
        "CO"
    )

    # Overall summary: Brazil and Colombia contribute equally.
    global_mean = (
        global_mean_br
        + global_mean_co
    ) / 2

    df_export = df_results.copy()

    separator = {
        col: ""
        for col in df_export.columns
    }
    separator["ID"] = "------------------------------------"

    def create_global_row(name, values):
        """Create a summary row compatible with the export DataFrame.

        Args:
            name: Label assigned to the summary row.
            values: Numeric values to insert into the corresponding columns.

        Returns:
            A dictionary containing the formatted summary row.
        """
        row = {
            col: ""
            for col in df_export.columns
        }
        row["ID"] = name

        for col in values.index:
            row[col] = values[col]

        return row

    global_row = create_global_row(
        "GLOBAL_SCORE",
        global_mean
    )

    global_br_row = create_global_row(
        "GLOBAL_SCORE_BR",
        global_mean_br
    )

    global_co_row = create_global_row(
        "GLOBAL_SCORE_CO",
        global_mean_co
    )

    # Append global and country-level summaries after participant results.
    df_export = pd.concat(
        [
            df_export,
            pd.DataFrame([separator]),
            pd.DataFrame([global_row]),
            pd.DataFrame([global_br_row]),
            pd.DataFrame([global_co_row])
        ],
        ignore_index=True
    )

    print(df_results.dtypes)

    df_export.to_excel(
        OUTPUT_PATH,
        index=False
    )

    print("\nSaved:")
    print(OUTPUT_PATH)