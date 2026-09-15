"""
Perform the exploratory multimetric evaluation of 3D facial methods.

The workflow integrates geometric fidelity, morphometric correspondence,
phenotypic preservation, and descriptive EDMA information into a common
analytical framework. Compatible quantitative metrics are normalized to a
0-1 scale and combined into an Exploratory Global Score.

The script also generates country-specific summaries, sensitivity analyses,
ranking information, graphical outputs, and formatted Excel workbooks.
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import warnings


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(
    r"C:\path\to\project\03_Dades_Analitzades\C2C_C2M_results"
)

GEOMETRIC_DIR = BASE_DIR / "ICP"

OUT_DIR = Path(
    r"C:\path\to\project\03_Dades_Analitzades\Multimetric_results"
)

INPUT_FILE = OUT_DIR / "multimetric_values.xlsx"
OUTPUT_FILE = OUT_DIR / "multimetric_results.xlsx"

CS_PPD_FILE = Path(
    r"C:\path\to\project\03_Dades_Analitzades\CS_PPD_results\CS_PPD.xlsx"
)

COUNTRIES = [
    "BR",
    "CO"
]

METHODS = [
    "SPG",
    "MP",
    "HRN1 Mid",
    "HRN3 Mid",
    "HRN5 Mid",
    "HRN5 High",
    "HRN10 Mid",
    "HRN10 High",
]


# ============================================================
# V2.2 CONFIGURATION — MULTIMETRIC EVALUATION
# ============================================================

# Weights assigned to the Exploratory Global Score.
# The two values must sum to 1.0.
GEOMETRIC_WEIGHT = 0.50
MORPHOMETRIC_WEIGHT = 0.50

# Sensitivity-analysis scenarios used to determine whether the resulting
# ranking depends strongly on the selected block weights.
SENSITIVITY_WEIGHTS = [
    (0.40, 0.60),
    (0.50, 0.50),
    (0.60, 0.40),
]

# Main graphical outputs.
FIG_DIR = OUT_DIR / "Figures"
FIGURE_FILE = FIG_DIR / "01_multimetric_scores.png"
HEATMAP_FILE = FIG_DIR / "02_heatmap.png"
RADAR_FILE = FIG_DIR / "03_radar.png"
SENSITIVITY_FILE = FIG_DIR / "04_sensitivity.png"
RANKING_FILE = FIG_DIR / "05_ranking_exploratory_global_score.png"
BY_COUNTRY_FILE = FIG_DIR / "06_by_country_score.png"
PIPELINE_FILE = FIG_DIR / "07_pipeline.png"

# Components displayed in the radar chart.
RADAR_METRICS = [
    "Geometric_Fidelity",
    "Phenotypic_Preservation",
    "Size_and_Shape_Correlation",
    "Morphometric_Fidelity",
    "Exploratory_Global_Score",
]

# The heatmap displays the main conceptual components and final score.
# Morphometric_Fidelity is retained because it represents the integrated
# morphometric block derived from size/shape and phenotypic preservation.
HEATMAP_METRICS = [
    "Geometric_Fidelity",
    "Phenotypic_Preservation",
    "Size_and_Shape_Correlation",
    "Morphometric_Fidelity",
    "Exploratory_Global_Score",
]


# ============================================================
# GENERAL UTILITIES
# ============================================================

def safe_mean(values):
    """Calculate the mean while ignoring missing values.

    Args:
        values: Iterable containing numeric values or NaN entries.

    Returns:
        float: Mean of the available numeric values, or NaN if no valid
        observations are available.
    """
    values = [
        float(v)
        for v in values
        if pd.notna(v)
    ]

    if not values:
        return np.nan

    return float(np.mean(values))


def normalize_fixed(
    value,
    minimum,
    maximum,
    higher_is_better=True
):
    """Normalize a metric to the fixed interval [0, 1].

    The theoretical minimum and maximum of each metric are used instead of
    sample-dependent limits. The resulting value can optionally be inverted
    when lower raw values indicate better performance.

    Examples:
        C2C percentage:
            80% -> 0.80

        CS correlation:
            r = 0.90 -> 0.95

        GPA IoU:
            IoU = 0.20
            when lower values indicate stronger separation:
            score = 1 - 0.20 = 0.80

    Args:
        value: Raw metric value.
        minimum: Theoretical minimum of the metric.
        maximum: Theoretical maximum of the metric.
        higher_is_better: Whether larger raw values indicate better
            performance.

    Returns:
        float: Normalized score within [0, 1], or NaN when unavailable.
    """
    if pd.isna(value):
        return np.nan

    value = float(value)

    if maximum == minimum:
        return np.nan

    score = (
        value - minimum
    ) / (
        maximum - minimum
    )

    score = np.clip(
        score,
        0,
        1
    )

    if not higher_is_better:
        score = 1 - score

    return float(score)


def method_order(name):
    """Return the predefined display order of a method.

    Args:
        name: Method name.

    Returns:
        int: Position in METHODS, or 999 when the method is unknown.
    """
    try:
        return METHODS.index(name)

    except ValueError:
        return 999


# ============================================================
# INTERPRETATION RELATIVE TO SPG
# ============================================================

def add_relative_interpretation(df):
    """Add a descriptive summary of the main evaluation components.

    Args:
        df: DataFrame containing method-level or country-level scores.

    Returns:
        pandas.DataFrame: Copy of the input table including a Summary column.
    """
    result = df.copy()
    result["Summary"] = ""

    interpretations = []

    for _, row in result.iterrows():
        method = row["Method"]
        geometric = row.get("Geometric_Fidelity", np.nan)
        size_shape = row.get("Size_and_Shape_Correlation", np.nan)
        preservation = row.get("Phenotypic_Preservation", np.nan)

        if method == "SPG":
            text_summary = "Reference for relative comparison."
        else:
            pieces = []

            if pd.notna(geometric):
                pieces.append(
                    f"Geometric fidelity = {geometric:.3f}."
                )

            if pd.notna(size_shape):
                pieces.append(
                    f"Size and shape correlation = {size_shape:.3f}."
                )

            if pd.notna(preservation):
                pieces.append(
                    f"Phenotypic preservation = {preservation:.3f}."
                )
            else:
                pieces.append(
                    "Phenotypic preservation relative to reference unavailable."
                )

            text_summary = " ".join(pieces)

        interpretations.append(text_summary)

    result["Summary"] = interpretations
    return result


# ============================================================
# CREATE INPUT EXCEL FILE
# ============================================================

def create_template():
    """Create the manually completed multimetric input workbook.

    The workbook contains the MANUAL and INSTRUCTIONS worksheets. GPA IoU
    values are supplied manually, whereas EDMA is retained as descriptive
    evidence and is not transformed into a numerical global-score component.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    for country in COUNTRIES:
        for method in METHODS:
            rows.append({
                "Method": method,
                "Country": country,
                "GPA_IoU": np.nan,
                "EDMA": "",
            })

    manual_df = pd.DataFrame(rows)

    instructions = pd.DataFrame({
        "Field": [
            "Method",
            "Country",
            "GPA_IoU",
            "EDMA",
        ],
        "How_to_fill": [
            "Do not modify.",
            "BR or CO.",
            (
                "GPA IoU CT-ST for this method and country. "
                "Value between 0 and 1."
            ),
            (
                "Descriptive EDMA. Do not introduce "
                "an invented percentage."
            ),
        ],
    })

    with pd.ExcelWriter(
        INPUT_FILE,
        engine="openpyxl"
    ) as writer:
        manual_df.to_excel(
            writer,
            sheet_name="MANUAL",
            index=False
        )

        instructions.to_excel(
            writer,
            sheet_name="INSTRUCTIONS",
            index=False
        )

    print("\n" + "=" * 70)
    print("INPUT FILE CREATED")
    print("=" * 70)
    print(INPUT_FILE)
    print(
        "\nComplete the MANUAL worksheet following the INSTRUCTIONS "
        "and run the program again."
    )
    print("=" * 70)


# ============================================================
# IDENTIFY METHOD FROM FILE PATH
# ============================================================

def detect_method(filepath):
    """Identify the evaluated method from a file path.

    Args:
        filepath: Path containing the method-specific directory structure.

    Returns:
        str or None: Standardized method name, or None when unrecognized.
    """
    parts = [
        part.lower()
        for part in filepath.parts
    ]

    if "mp" in parts:
        return "MP"

    if "hrn1" in parts:
        if "mid" in parts:
            return "HRN1 Mid"

    if "hrn3" in parts:
        if "mid" in parts:
            return "HRN3 Mid"

    if "hrn5" in parts:

        if "mid" in parts:
            return "HRN5 Mid"

        if "high" in parts:
            return "HRN5 High"

    if "hrn10" in parts:

        if "mid" in parts:
            return "HRN10 Mid"

        if "high" in parts:
            return "HRN10 High"

    return None


# ============================================================
# IDENTIFY COUNTRY
# ============================================================

def detect_country(patient_id):
    """Identify the participant country from the coded identifier.

    Args:
        patient_id: Coded participant identifier.

    Returns:
        str or None: BR, CO, or None if the prefix is unrecognized.
    """
    patient_id = (
        str(patient_id)
        .upper()
        .strip()
    )

    if patient_id.startswith("BR"):
        return "BR"

    if patient_id.startswith("CO"):
        return "CO"

    return None


# ============================================================
# IDENTIFY CT / ST GROUP
# ============================================================

def detect_group(patient_id):
    """Identify whether a participant belongs to the CT or ST group.

    Args:
        patient_id: Coded participant identifier.

    Returns:
        str or None: CT, ST, or None when the code cannot be identified.
    """
    patient_id = (
        str(patient_id)
        .upper()
        .strip()
    )

    if len(patient_id) < 4:
        return None

    code = patient_id[2:4]

    if code == "CT":
        return "CT"

    if code == "ST":
        return "ST"

    return None


# ============================================================
# READ C2C / C2M FROM FINAL EXCEL FILES
# ============================================================

def read_geometric_metrics():
    """Read country-level geometric metrics from final C2C/C2M workbooks.

    Returns:
        pandas.DataFrame: Country-specific geometric metrics for each method.

    Raises:
        FileNotFoundError: If the geometric directory or expected workbooks
        cannot be found.
    """
    print(
        "\nReading C2C/C2M metrics from the final Excel files..."
    )

    if not GEOMETRIC_DIR.exists():
        raise FileNotFoundError(
            f"C2C/C2M directory does not exist:\n{GEOMETRIC_DIR}"
        )

    files = [
        f
        for f in GEOMETRIC_DIR.rglob("*.xlsx")
        if (
            "C2C_C2M" in f.name
            and "backup" not in f.name.lower()
            and "prueba" not in str(f).lower()
        )
    ]

    if not files:
        raise FileNotFoundError(
            "No C2C/C2M files were found."
        )

    rows = []

    country_rows = {
        "BR": "GLOBAL_SCORE_BR",
        "CO": "GLOBAL_SCORE_CO",
    }

    for file in files:

        method = detect_method(file)

        if method is None:
            continue

        try:
            df = pd.read_excel(
                file,
                engine="openpyxl"
            )
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue

        if "ID" not in df.columns:
            continue

        ids = (
            df["ID"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        for country, global_id in country_rows.items():

            selected = df[
                ids == global_id
            ]

            if selected.empty:
                print(
                    f"⚠ Missing {global_id} in "
                    f"{method}: {file.name}"
                )
                continue

            row = selected.iloc[0]

            rows.append({

                "Method": method,
                "Country": country,

                "C2C_pct_1mm": pd.to_numeric(
                    row["C2C % <=1mm"],
                    errors="coerce"
                ),

                "C2M_pct_1mm": pd.to_numeric(
                    row["C2M % <=1mm"],
                    errors="coerce"
                ),

                "C2C_pct_05mm": pd.to_numeric(
                    row["C2C % <=0.5mm"],
                    errors="coerce"
                ),

                "C2M_pct_05mm": pd.to_numeric(
                    row["C2M % <=0.5mm"],
                    errors="coerce"
                ),

                "C2C_mean_mm": pd.to_numeric(
                    row["C2C Mean (mm)"],
                    errors="coerce"
                ),

                "C2M_mean_mm": pd.to_numeric(
                    row["C2M Mean (mm)"],
                    errors="coerce"
                ),

                # Values are already balanced as 50% CT + 50% ST/M.
                "Groups_available": "CT, ST",
                "N_geometric": np.nan,
            })

        print(
            f"  ✓ {method}: {file.name}"
        )

    return pd.DataFrame(rows)


# ============================================================
# NORMALIZE PRECOMPUTED GEOMETRIC VALUES
# ============================================================

def calculate_geometric_scores(raw):
    """Convert C2C and C2M tolerance percentages to normalized scores.

    Args:
        raw: DataFrame containing country-level C2C and C2M metrics.

    Returns:
        tuple: Empty group-level DataFrame and country-level normalized
        geometric scores.
    """
    if raw.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame()
        )

    country_summary = raw.copy()

    # C2C within 1 mm: convert percentage from 0-100 to 0-1.
    country_summary[
        "P2P_C2C_score"
    ] = (
        country_summary["C2C_pct_1mm"]
        / 100
    )

    # C2M within 1 mm: convert percentage from 0-100 to 0-1.
    country_summary[
        "S2S_C2M_score"
    ] = (
        country_summary["C2M_pct_1mm"]
        / 100
    )

    # C2C and C2M contribute equally to Geometric Fidelity.
    country_summary[
        "Geometric_Fidelity"
    ] = (
        country_summary[
            [
                "P2P_C2C_score",
                "S2S_C2M_score",
            ]
        ]
        .mean(axis=1)
    )

    # CT/ST balancing has already been performed in the source workbooks.
    group_summary = pd.DataFrame()

    return (
        group_summary,
        country_summary
    )


# ============================================================
# READ CS / PPD AUTOMATICALLY
# ============================================================

def read_cs_ppd_metrics():
    """Read CS and PPD correlations from the corresponding workbook.

    The expected columns are:
        Method | Country | CS | PPD

    SPG does not need to be present because its internal CS and PPD reference
    scores are subsequently fixed to 1.

    Returns:
        pandas.DataFrame: Method-country CS and PPD values.

    Raises:
        FileNotFoundError: If the workbook cannot be found.
        RuntimeError: If the workbook cannot be read.
        ValueError: If required columns are missing or duplicated.
    """
    print(
        "\nSearching for CS/PPD metrics automatically..."
    )

    if not CS_PPD_FILE.exists():
        raise FileNotFoundError(
            "CS/PPD file was not found:\n"
            f"{CS_PPD_FILE}"
        )

    try:
        df = pd.read_excel(
            CS_PPD_FILE,
            engine="openpyxl"
        )

    except Exception as e:
        raise RuntimeError(
            f"Error reading CS/PPD: {CS_PPD_FILE}\n{e}"
        ) from e

    required = [
        "Method",
        "Country",
        "CS",
        "PPD",
    ]

    missing_columns = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns in CS_PPD.xlsx: "
            f"{missing_columns}. "
            "Expected: Method | Country | CS | PPD"
        )

    df = df[
        required
    ].copy()

    df["Method"] = (
        df["Method"]
        .astype(str)
        .str.strip()
    )

    df["Country"] = (
        df["Country"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    for col in [
        "CS",
        "PPD",
    ]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    duplicated = df.duplicated(
        subset=[
            "Method",
            "Country",
        ],
        keep=False
    )

    if duplicated.any():
        duplicate_rows = (
            df.loc[
                duplicated,
                [
                    "Method",
                    "Country",
                ]
            ]
            .drop_duplicates()
        )

        raise ValueError(
            "Duplicated rows were found in CS_PPD.xlsx for:\n"
            + duplicate_rows.to_string(index=False)
        )

    print(
        f"  ✓ All methods: {CS_PPD_FILE.name}"
    )

    return df


def merge_cs_ppd_metrics(
    manual,
    cs_ppd
):
    """Merge automatically calculated CS and PPD values with manual inputs.

    SPG is assigned an internal reference value of 1 for both CS and PPD.
    Missing method-country combinations remain as NaN and are reported in the
    terminal.

    Args:
        manual: Manual multimetric input DataFrame.
        cs_ppd: Automatically loaded CS/PPD DataFrame.

    Returns:
        pandas.DataFrame: Combined manual and CS/PPD information.
    """
    manual = manual.copy()

    # Ignore manually supplied CS/PPD columns from older input files to
    # preserve compatibility with previous workbook versions.
    manual = manual.drop(
        columns=[
            "CS",
            "PPD",
        ],
        errors="ignore"
    )

    combined = manual.merge(
        cs_ppd,
        on=[
            "Method",
            "Country",
        ],
        how="left"
    )

    mask_spg = (
        combined[
            "Method"
        ] == "SPG"
    )

    combined.loc[
        mask_spg,
        "CS"
    ] = 1.0

    combined.loc[
        mask_spg,
        "PPD"
    ] = 1.0

    expected_rows = combined[
        ~mask_spg
    ][
        [
            "Method",
            "Country",
            "CS",
            "PPD",
        ]
    ]

    missing_rows = expected_rows[
        expected_rows[
            [
                "CS",
                "PPD",
            ]
        ]
        .isna()
        .any(
            axis=1
        )
    ]

    if not missing_rows.empty:
        print(
            "\n"
            + "!" * 70
        )

        print(
            "Warning: Missing CS/PPD values in CS_PPD.xlsx"
        )

        print(
            "!" * 70
        )

        for _, row in missing_rows.iterrows():
            missing_metrics = []

            if pd.isna(
                row["CS"]
            ):
                missing_metrics.append(
                    "CS"
                )

            if pd.isna(
                row["PPD"]
            ):
                missing_metrics.append(
                    "PPD"
                )

            print(
                "  - "
                f"{row['Method']} | "
                f"{row['Country']} | "
                f"missing: {', '.join(missing_metrics)}"
            )

        print(
            "These values will remain as NaN."
        )

        print(
            "!" * 70
            + "\n"
        )

    return combined


# ============================================================
# READ MANUALLY SUPPLIED METRICS
# ============================================================

def read_manual_metrics():
    """Read manually supplied GPA IoU and descriptive EDMA information.

    Returns:
        pandas.DataFrame: Standardized manual input values.

    Raises:
        ValueError: If required workbook columns are missing.
    """
    df = pd.read_excel(
        INPUT_FILE,
        sheet_name="MANUAL",
        engine="openpyxl"
    )

    required = [
        "Method",
        "Country",
        "GPA_IoU",
    ]

    missing = [
        col for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns in MANUAL: {missing}"
        )

    # New/simple structure: descriptive EDMA column.
    # Compatibility with previous v2_4 workbooks containing EDMA is retained.
    if "EDMA" in df.columns:
        df["EDMA"] = df["EDMA"].apply(
            lambda x: "" if pd.isna(x) else str(x)
        )
    elif "EDMA" in df.columns:
        df["EDMA"] = (
            df["EDMA"]
            .fillna("")
            .astype(str)
        )
    else:
        df["EDMA"] = ""

    df["Country"] = (
        df["Country"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df["Method"] = (
        df["Method"]
        .astype(str)
        .str.strip()
    )

    df["GPA_IoU"] = pd.to_numeric(
        df["GPA_IoU"],
        errors="coerce"
    )

    df["EDMA"] = (
        df["EDMA"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return df


# ============================================================
# CALCULATE GPA / EDMA / CS / PPD COMPONENTS
# ============================================================

def calculate_manual_scores(manual):
    """Calculate the morphometric components used in the framework.

    Phenotypic Separation is defined as:
        1 - GPA IoU

    Phenotypic Preservation is defined as:
        1 - |GPA IoU_method - GPA IoU_SPG|

    EDMA is retained as descriptive/local evidence and is not converted into
    a 0-1 score or incorporated into Morphometric Fidelity.

    Args:
        manual: DataFrame containing GPA IoU, CS, PPD and EDMA information.

    Returns:
        pandas.DataFrame: Calculated morphometric indicators.
    """
    results = []

    for _, row in manual.iterrows():
        method = row["Method"]
        country = row["Country"]

        gpa_iou = row["GPA_IoU"]
        cs_r = row["CS"]
        ppd_r = row["PPD"]
        edma = row.get("EDMA", "")

        gpa_iou_score = normalize_fixed(
            gpa_iou,
            0,
            1,
            higher_is_better=False
        )

        phenotypic_separation = gpa_iou_score

        if method == "SPG":
            cs_score = 1.0
            ppd_score = 1.0
        else:
            cs_score = normalize_fixed(
                cs_r,
                -1,
                1,
                higher_is_better=True
            )
            ppd_score = normalize_fixed(
                ppd_r,
                -1,
                1,
                higher_is_better=True
            )

        size_and_shape_correlation = safe_mean(
            [cs_score, ppd_score]
        )

        results.append({
            "Method": method,
            "Country": country,
            "GPA_IoU": gpa_iou,
            "CS": cs_r,
            "PPD": ppd_r,
            "EDMA": edma,
            "GPA_IoU_score": gpa_iou_score,
            "Phenotypic_Separation": phenotypic_separation,
            "CS_score": cs_score,
            "PPD_score": ppd_score,
            "Size_and_Shape_Correlation": size_and_shape_correlation,
        })

    result = pd.DataFrame(results)

    spg_reference = (
        result[result["Method"] == "SPG"]
        .set_index("Country")["GPA_IoU"]
        .to_dict()
    )

    result["GPA_IoU_SPG"] = (
        result["Country"].map(spg_reference)
    )

    result["Phenotypic_Preservation"] = (
        1
        - (
            result["GPA_IoU"]
            - result["GPA_IoU_SPG"]
        ).abs()
    ).clip(0, 1)

    result.loc[
        result["Method"] == "SPG",
        "Phenotypic_Preservation"
    ] = 1.0

    result["Morphometric_Fidelity"] = result.apply(
        lambda row: safe_mean([
            row["Size_and_Shape_Correlation"],
            row["Phenotypic_Preservation"],
        ]),
        axis=1
    )

    result = result.drop(
        columns=["GPA_IoU_SPG"]
    )

    return result


# ============================================================
# COMBINE GEOMETRIC AND MORPHOMETRIC COMPONENTS
# ============================================================

def combine_scores(
    geometric_country,
    manual_scores
):
    """Combine geometric and morphometric evidence into the global framework.

    Args:
        geometric_country: Country-level geometric metrics.
        manual_scores: Morphometric and phenotypic indicators.

    Returns:
        pandas.DataFrame: Integrated method-country evaluation table.
    """
    combined = manual_scores.copy()

    if not geometric_country.empty:

        columns_to_merge = [

            "Method",

            "Country",

            "N_geometric",

            "Groups_available",

            "C2C_pct_1mm",

            "C2M_pct_1mm",

            "P2P_C2C_score",

            "S2S_C2M_score",

            "Geometric_Fidelity",
        ]

        optional = [

            "C2C_mean_mm",

            "C2M_mean_mm",

            "C2C_pct_05mm",

            "C2M_pct_05mm",
        ]

        for col in optional:

            if col in geometric_country.columns:

                columns_to_merge.append(
                    col
                )

        combined = combined.merge(

            geometric_country[
                columns_to_merge
            ],

            on=[
                "Method",
                "Country"
            ],

            how="left"
        )

    else:

        combined[
            "P2P_C2C_score"
        ] = np.nan

        combined[
            "S2S_C2M_score"
        ] = np.nan

        combined[
            "Geometric_Fidelity"
        ] = np.nan

    # ========================================================
    # SPG REFERENCE
    #
    # C2C and C2M quantify fidelity relative to SPG.
    # Therefore, SPG compared with itself is assigned a score of 1.
    # ========================================================

    mask_spg = (
        combined[
            "Method"
        ] == "SPG"
    )

    combined.loc[
        mask_spg,
        "P2P_C2C_score"
    ] = 1.0

    combined.loc[
        mask_spg,
        "S2S_C2M_score"
    ] = 1.0

    combined.loc[
        mask_spg,
        "Geometric_Fidelity"
    ] = 1.0

    # ========================================================
    # EXPLORATORY GLOBAL SCORE
    #
    # Morphometric_Fidelity already integrates:
    #   1. Size_and_Shape_Correlation
    #   2. Phenotypic_Preservation
    #
    # To avoid counting phenotypic information twice, the global score
    # therefore combines only:
    #
    #   1. Geometric_Fidelity
    #   2. Morphometric_Fidelity
    #
    # If either block is unavailable, the global score remains NaN.
    # ========================================================

    global_scores = []

    blocks_used = []

    for _, row in combined.iterrows():

        blocks = [

            row.get(
                "Geometric_Fidelity",
                np.nan
            ),

            row.get(
                "Morphometric_Fidelity",
                np.nan
            ),
        ]

        valid = [

            float(value)

            for value in blocks

            if pd.notna(value)
        ]

        blocks_used.append(
            len(valid)
        )

        if len(valid) == 2:

            weight_sum = GEOMETRIC_WEIGHT + MORPHOMETRIC_WEIGHT

            if not np.isclose(weight_sum, 1.0):
                raise ValueError(
                    "GEOMETRIC_WEIGHT + MORPHOMETRIC_WEIGHT must sum to 1.0."
                )

            global_scores.append(
                float(
                    GEOMETRIC_WEIGHT * blocks[0]
                    + MORPHOMETRIC_WEIGHT * blocks[1]
                )
            )

        else:

            global_scores.append(
                np.nan
            )

    combined[
        "Exploratory_Global_Score"
    ] = global_scores

    combined[
        "Blocks_used"
    ] = blocks_used

    combined = add_relative_interpretation(
        combined
    )

    return combined


# ============================================================
# CALCULATE OVERALL METHOD RESULTS
# ============================================================

def calculate_overall(combined):
    """Calculate the overall country-averaged result for each method.

    Args:
        combined: Country-level integrated score table.

    Returns:
        pandas.DataFrame: Overall method-level results.
    """
    numeric_cols_before_edma = [
        "P2P_C2C_score",
        "S2S_C2M_score",
        "Geometric_Fidelity",
        "GPA_IoU_score",
    ]

    numeric_cols_after_edma = [
        "Phenotypic_Separation",
        "Phenotypic_Preservation",
        "CS_score",
        "PPD_score",
        "Size_and_Shape_Correlation",
        "Morphometric_Fidelity",
        "Exploratory_Global_Score",
    ]

    rows = []

    for method, df in combined.groupby("Method"):
        row = {
            "Method": method,
            "Countries_used": df["Country"].nunique(),
        }

        for col in numeric_cols_before_edma:
            if col in df.columns:
                row[col] = df[col].mean()

        # EDMA remains descriptive; non-empty notes are concatenated.
        if "EDMA" in df.columns:
            notes = [
                str(v).strip()
                for v in df["EDMA"]
                if pd.notna(v) and str(v).strip()
            ]
            row["EDMA"] = " | ".join(dict.fromkeys(notes))

        for col in numeric_cols_after_edma:
            if col in df.columns:
                row[col] = df[col].mean()

        rows.append(row)

    overall = pd.DataFrame(rows)

    if overall.empty:
        return overall

    overall["_order"] = (
        overall["Method"].apply(method_order)
    )

    overall = (
        overall
        .sort_values("_order")
        .drop(columns="_order")
        .reset_index(drop=True)
    )

    overall = add_relative_interpretation(overall)

    return overall


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(combined, overall):
    """Export country-level, overall and methodological results to Excel.

    Args:
        combined: Country-level integrated score table.
        overall: Overall method-level results.
    """
    by_country_columns = [
        "Method",
        "Country",

        # Geometric components.
        "P2P_C2C_score",
        "S2S_C2M_score",
        "Geometric_Fidelity",

        # Phenotypic components.
        "GPA_IoU_score",
        "EDMA",
        "Phenotypic_Separation",
        "Phenotypic_Preservation",

        # Size and shape components.
        "CS_score",
        "PPD_score",
        "Size_and_Shape_Correlation",

        # Morphometric and global components.
        "Morphometric_Fidelity",
        "Exploratory_Global_Score",

        "Summary",
    ]

    by_country_columns = [
        col for col in by_country_columns
        if col in combined.columns
    ]

    by_country = combined[by_country_columns].copy()

    by_country["_order"] = (
        by_country["Method"].apply(method_order)
    )

    country_order = {
        "BR": 0,
        "CO": 1
    }

    by_country["_country_order"] = (
        by_country["Country"]
        .map(country_order)
        .fillna(999)
    )

    by_country = (
        by_country
        .sort_values(
            ["_country_order", "_order"]
        )
        .drop(
            columns=[
                "_order",
                "_country_order"
            ]
        )
        .reset_index(drop=True)
    )

    methodology = pd.DataFrame({
        "Metric_or_Block": [
            "P2P_C2C_score",
            "S2S_C2M_score",
            "Geometric Fidelity",
            "GPA_IoU_score",
            "EDMA",
            "Phenotypic Separation",
            "Phenotypic Preservation",
            "CS_score",
            "PPD_score",
            "Size and Shape Correlation",
            "Morphometric Fidelity",
            "Exploratory Global Score",
        ],
        "Normalization(0-1)_calculation": [
            "Mean(CT C2C % ≤ 1 mm, ST C2C % ≤ 1 mm) / 100",
            "Mean(CT C2M % ≤ 1 mm, ST C2M % ≤ 1 mm) / 100",
            "Mean(P2P_C2C_score, S2S_C2M_score)",
            "1 - GPA IoU",
            (
                "Descriptive analysis of inter-landmark "
                "distance differences. No forced 0-1 score."
            ),
            "1 - GPA IoU",
            "1 - |GPA IoU_method - GPA IoU_SPG|",
            "CS correlation r",
            "PPD correlation r",
            "Mean(CS_score, PPD_score)",
            (
                "Mean(Phenotypic_Preservation, "
                "Size_and_Shape_Correlation)"
            ),
            (
                "Mean(Geometric_Fidelity, Morphometric_Fidelity)"
            ),
        ],
        "Interpretation": [
            "Higher = better geometric fidelity",
            "Higher = better geometric fidelity",
            "Higher = better geometric fidelity",
            "Higher = stronger CT-ST phenotypic separation",
            (
                "Supporting CT-ST phenotypic separation analysis, interpreted "
                "only descriptively."
            ),
            "Higher = stronger CT-ST phenotypic separation",
            "Higher = better preservation of the SPG phenotypic pattern",
            "Higher = greater size and shape correlation",
            "Higher = greater size and shape correlation",
            "Higher = greater size and shape correlation",
            "Higher = better morphometric fidelity",
            (
                "Higher = better overall multimetric performance. "
                "Exploratory and not clinically validated."
            ),
        ],
    })

    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl"
    ) as writer:
        overall.to_excel(
            writer,
            sheet_name="OVERALL",
            index=False
        )

        by_country.to_excel(
            writer,
            sheet_name="BY_COUNTRY",
            index=False
        )

        methodology.to_excel(
            writer,
            sheet_name="PROTOCOL",
            index=False
        )


# ============================================================
# CREATE MAIN MULTIMETRIC FIGURE
# ============================================================

def create_figure(
    overall
):
    """Create the grouped bar chart of integrated multimetric scores.

    Args:
        overall: Overall method-level results.
    """
    if overall.empty:
        return

    plot_df = overall[
        overall[
            "Method"
        ] != "SPG"
    ].copy()

    if plot_df.empty:
        return

    columns = [

        col

        for col in [

            "Geometric_Fidelity",
            "Phenotypic_Preservation",
            "Size_and_Shape_Correlation",
            "Morphometric_Fidelity",
            "Exploratory_Global_Score",

        ]

        if (
            col in plot_df.columns
            and
            plot_df[
                col
            ].notna().any()
        )
    ]

    if not columns:
        return

    ax = plot_df.plot(

        x="Method",

        y=columns,

        kind="bar",

        figsize=(
            12,
            7
        )
    )

    ax.set_ylim(
        0,
        1
    )

    ax.set_ylabel(
        "Normalized score (0-1)"
    )

    ax.set_xlabel(
        "Method"
    )

    ax.set_title(
        "Multimetric Evaluation of 3D Facial Methods"
    )

    plt.xticks(
        rotation=30,
        ha="right"
    )

    plt.tight_layout()

    FIG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    plt.savefig(
        FIGURE_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


# ============================================================
# V2.0 — PRESENTATION AND ROBUSTNESS UTILITIES
# ============================================================

def _available_columns(df, columns):
    """Return columns that exist and contain at least one valid value."""
    return [
        col for col in columns
        if col in df.columns and df[col].notna().any()
    ]


def _non_spg(df):
    """Return a copy of a DataFrame excluding the SPG reference rows."""
    if "Method" not in df.columns:
        return df.copy()

    return df[df["Method"] != "SPG"].copy()


def _score_with_weights(
    df,
    geometric_weight,
    morphometric_weight
):
    """Recalculate the global score using alternative block weights.

    Args:
        df: DataFrame containing geometric and morphometric fidelity values.
        geometric_weight: Weight assigned to Geometric Fidelity.
        morphometric_weight: Weight assigned to Morphometric Fidelity.

    Returns:
        pandas.DataFrame: Copy including Weighted_Global_Score.

    Raises:
        ValueError: If the supplied weights do not sum to 1.
    """
    result = df.copy()
    weight_sum = geometric_weight + morphometric_weight

    if not np.isclose(weight_sum, 1.0):
        raise ValueError("Weights must sum to 1.0.")

    required = [
        "Geometric_Fidelity",
        "Morphometric_Fidelity"
    ]

    if any(col not in result.columns for col in required):
        result["Weighted_Global_Score"] = np.nan
        return result

    mask = result[required].notna().all(axis=1)
    result["Weighted_Global_Score"] = np.nan

    result.loc[mask, "Weighted_Global_Score"] = (
        geometric_weight
        * result.loc[mask, "Geometric_Fidelity"]
        + morphometric_weight
        * result.loc[mask, "Morphometric_Fidelity"]
    )

    return result


# ============================================================
# AUTOMATIC RANKING
# ============================================================

def calculate_ranking(overall):
    """Rank non-reference methods by Exploratory Global Score.

    Args:
        overall: Overall method-level results.

    Returns:
        pandas.DataFrame: Ranked methods and corresponding scores.
    """
    ranking = _non_spg(overall)

    if (
        ranking.empty
        or "Exploratory_Global_Score" not in ranking.columns
    ):
        return pd.DataFrame()

    ranking = ranking[
        ["Method", "Exploratory_Global_Score"]
    ].dropna().copy()

    ranking = ranking.sort_values(
        "Exploratory_Global_Score",
        ascending=False
    ).reset_index(drop=True)

    ranking["Rank"] = np.arange(
        1,
        len(ranking) + 1
    )

    ranking["Medal"] = ranking["Rank"].map({
        1: "1st",
        2: "2nd",
        3: "3rd",
    }).fillna("")

    ranking = ranking[
        [
            "Rank",
            "Medal",
            "Method",
            "Exploratory_Global_Score"
        ]
    ]

    return ranking


# ============================================================
# SENSITIVITY ANALYSIS
# ============================================================

def calculate_sensitivity(overall):
    """Assess ranking stability under alternative block weights.

    Args:
        overall: Overall method-level results.

    Returns:
        tuple: Sensitivity results and ranking-stability summary.
    """
    rows = []

    for geometric_weight, morphometric_weight in SENSITIVITY_WEIGHTS:
        weighted = _score_with_weights(
            _non_spg(overall),
            geometric_weight,
            morphometric_weight
        )

        weighted = weighted.dropna(
            subset=["Weighted_Global_Score"]
        ).sort_values(
            "Weighted_Global_Score",
            ascending=False
        ).reset_index(drop=True)

        for rank, (_, row) in enumerate(
            weighted.iterrows(),
            start=1
        ):
            rows.append({
                "Geometric_weight": geometric_weight,
                "Morphometric_weight": morphometric_weight,
                "Scenario": (
                    f"{int(geometric_weight * 100)}/"
                    f"{int(morphometric_weight * 100)}"
                ),
                "Rank": rank,
                "Method": row["Method"],
                "Weighted_Global_Score": row[
                    "Weighted_Global_Score"
                ],
            })

    sensitivity = pd.DataFrame(rows)

    if sensitivity.empty:
        return sensitivity, pd.DataFrame()

    stability_rows = []

    for method, df in sensitivity.groupby("Method"):
        ranks = df["Rank"].to_numpy(dtype=float)
        scores = df["Weighted_Global_Score"].to_numpy(dtype=float)

        stability_rows.append({
            "Method": method,
            "Best_rank": int(np.nanmin(ranks)),
            "Worst_rank": int(np.nanmax(ranks)),
            "Rank_range": int(
                np.nanmax(ranks) - np.nanmin(ranks)
            ),
            "Mean_rank": float(np.nanmean(ranks)),
            "Score_min": float(np.nanmin(scores)),
            "Score_max": float(np.nanmax(scores)),
            "Score_range": float(
                np.nanmax(scores) - np.nanmin(scores)
            ),
            "Ranking_stable": bool(
                np.nanmax(ranks) == np.nanmin(ranks)
            ),
        })

    stability = (
        pd.DataFrame(stability_rows)
        .sort_values(["Mean_rank", "Method"])
        .reset_index(drop=True)
    )

    return sensitivity, stability


# ============================================================
# RADAR CHART
# ============================================================

def create_radar_chart(overall):
    """Create a radar chart of the independent multimetric dimensions.

    Args:
        overall: Overall method-level results.
    """
    plot_df = _non_spg(overall)

    metrics = _available_columns(
        plot_df,
        RADAR_METRICS
    )

    if plot_df.empty or len(metrics) < 5:
        return

    plot_df = plot_df.dropna(
        subset=metrics,
        how="any"
    ).copy()

    if plot_df.empty:
        return

    label_map = {
        "Geometric_Fidelity": "Geometric fidelity",
        "Phenotypic_Preservation": "Phenotypic preservation",
        "Size_and_Shape_Correlation": "Size & shape correlation",
        "Morphometric_Fidelity": "Morphometric fidelity",
        "Exploratory_Global_Score": "Global score",
    }

    axis_labels = [
        label_map.get(m, m)
        for m in metrics
    ]

    n = len(metrics)

    angles = np.linspace(
        0,
        2 * np.pi,
        n,
        endpoint=False
    ).tolist()

    angles += angles[:1]

    # Explicitly center the polar axes within the full figure.
    fig = plt.figure(
        figsize=(10, 9)
    )

    ax = fig.add_axes(
        [0.14, 0.16, 0.72, 0.72],
        polar=True
    )

    for _, row in plot_df.iterrows():
        values = [
            float(row[m])
            for m in metrics
        ]

        values += values[:1]

        ax.plot(
            angles,
            values,
            linewidth=2,
            label=row["Method"]
        )

        ax.fill(
            angles,
            values,
            alpha=0.05
        )

    ax.set_xticks(
        angles[:-1]
    )

    ax.set_xticklabels(
        axis_labels,
        fontsize=11
    )

    ax.set_ylim(
        0,
        1
    )

    ax.set_yticks(
        [0.2, 0.4, 0.6, 0.8, 1.0]
    )

    ax.set_yticklabels(
        ["0.2", "0.4", "0.6", "0.8", "1.0"],
        fontsize=8
    )

    # Center the title relative to the complete figure.
    fig.suptitle(
        "Multimetric Profile",
        x=0.5,
        y=0.965,
        ha="center",
        fontsize=15,
        fontweight="bold"
    )

    # Position the legend in the lower-right area.
    handles, labels = ax.get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        loc="lower right",
        bbox_to_anchor=(0.97, 0.03),
        frameon=False,
        fontsize=10
    )

    plt.savefig(
        RADAR_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


# ============================================================
# HEATMAP
# ============================================================

def create_heatmap(overall):
    """Create the multimetric performance heatmap.

    Args:
        overall: Overall method-level results.
    """
    from matplotlib.colors import LinearSegmentedColormap

    plot_df = _non_spg(overall)

    metrics = _available_columns(
        plot_df,
        HEATMAP_METRICS
    )

    if plot_df.empty or not metrics:
        return

    matrix = (
        plot_df
        .set_index("Method")[metrics]
        .astype(float)
    )

    labels = {
        "Geometric_Fidelity": "Geometric Fidelity",
        "Phenotypic_Preservation": "Phenotypic Preservation",
        "Size_and_Shape_Correlation": "Size and Shape Correlation",
        "Morphometric_Fidelity": "Morphometric Fidelity",
        "Exploratory_Global_Score": "Exploratory Global Score",
    }

    # Formal pastel gradient progressing from lower to higher values.
    cmap = LinearSegmentedColormap.from_list(
        "pastel_red_aqua_olive",
        [
            (0.00, "#F08080"),
            (0.25, "#F3B0A8"),
            (0.50, "#79D7D3"),
            (0.75, "#7FD39B"),
            (1.00, "#BDDE26"),
        ]
    )

    fig, ax = plt.subplots(
        figsize=(10.5, 6)
    )

    image = ax.imshow(
        matrix.to_numpy(),
        aspect="auto",
        vmin=0,
        vmax=1,
        cmap=cmap
    )

    ax.set_xticks(
        np.arange(len(metrics))
    )

    ax.set_xticklabels(
        [
            labels.get(m, m)
            for m in metrics
        ],
        rotation=30,
        ha="right"
    )

    ax.set_yticks(
        np.arange(len(matrix.index))
    )

    ax.set_yticklabels(
        matrix.index
    )

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix.iloc[i, j]

            if pd.notna(value):
                ax.text(
                    j,
                    i,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=10,
                    fontweight="bold"
                )

    ax.set_title(
        "Multimetric Performance Heatmap",
        fontsize=15,
        fontweight="bold"
    )

    cbar = fig.colorbar(
        image,
        ax=ax
    )

    cbar.set_label(
        "Normalized score (0–1)"
    )

    plt.tight_layout()

    plt.savefig(
        HEATMAP_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


# ============================================================
# RANKING FIGURE
# ============================================================

def create_ranking_figure(ranking):
    """Create the horizontal bar chart of the method ranking.

    Args:
        ranking: Ranking table generated by calculate_ranking().
    """
    if ranking.empty:
        return

    df = ranking.sort_values(
        "Exploratory_Global_Score",
        ascending=True
    ).copy()

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    bars = ax.barh(
        df["Method"],
        df["Exploratory_Global_Score"]
    )

    ax.set_xlim(
        0,
        1
    )

    ax.set_xlabel(
        "Exploratory Global Score"
    )

    ax.set_title(
        "Multimetric Ranking",
        fontsize=14,
        fontweight="bold"
    )

    rank_lookup = (
        ranking
        .set_index("Method")["Rank"]
        .to_dict()
    )

    for bar, method, value in zip(
        bars,
        df["Method"],
        df["Exploratory_Global_Score"]
    ):
        ax.text(
            min(value + 0.015, 0.97),
            bar.get_y() + bar.get_height() / 2,
            f"{value:.3f}   #{rank_lookup[method]}",
            va="center",
            fontsize=10,
            fontweight="bold"
        )

    plt.tight_layout()

    plt.savefig(
        RANKING_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


# ============================================================
# SENSITIVITY FIGURE
# ============================================================

def create_sensitivity_figure(sensitivity):
    """Create the sensitivity plot and corresponding numerical table.

    Args:
        sensitivity: DataFrame generated by calculate_sensitivity().
    """
    if sensitivity.empty:
        return

    # Divide the figure into an upper plot and a lower numerical table.
    fig = plt.figure(
        figsize=(10, 8)
    )

    gs = fig.add_gridspec(
        2,
        1,
        height_ratios=[3.5, 1.4],
        hspace=0.25
    )

    ax = fig.add_subplot(
        gs[0]
    )

    ax_table = fig.add_subplot(
        gs[1]
    )

    scenario_order = [
        f"{int(g * 100)}/{int(m * 100)}"
        for g, m in SENSITIVITY_WEIGHTS
    ]

    # ========================================================
    # GRAPH
    # ========================================================

    for method, df in sensitivity.groupby("Method"):

        lookup = (
            df
            .set_index("Scenario")[
                "Weighted_Global_Score"
            ]
        )

        y = [
            lookup.get(
                scenario,
                np.nan
            )
            for scenario in scenario_order
        ]

        ax.plot(
            scenario_order,
            y,
            marker="o",
            linewidth=2,
            label=method
        )

    ax.set_ylim(
        0,
        1
    )

    ax.set_xlabel(
        "Geometric / Morphometric Weight (%)"
    )

    ax.set_ylabel(
        "Recalculated Exploratory Global Score"
    )

    ax.set_title(
        "Sensitivity of the Multimetric Global Score to Block Weighting",
        fontsize=14,
        fontweight="bold"
    )

    ax.legend(
        frameon=False,
        loc="lower right"
    )

    ax.grid(
        axis="y",
        alpha=0.25
    )

    # ========================================================
    # EXACT NUMERICAL VALUES
    # ========================================================

    table_df = (
        sensitivity
        .pivot(
            index="Method",
            columns="Scenario",
            values="Weighted_Global_Score"
        )
        .reindex(
            columns=scenario_order
        )
    )

    method_order_table = [
        method
        for method in METHODS
        if method != "SPG"
    ]

    table_df = table_df.reindex(
        method_order_table
    )

    cell_text = [
        [
            f"{value:.3f}"
            if pd.notna(value)
            else ""
            for value in row
        ]
        for row in table_df.to_numpy()
    ]

    ax_table.axis(
        "off"
    )

    table = ax_table.table(
        cellText=cell_text,
        rowLabels=table_df.index,
        colLabels=scenario_order,
        cellLoc="center",
        rowLoc="center",
        loc="center"
    )

    table.auto_set_font_size(
        False
    )

    table.set_fontsize(
        9
    )

    table.scale(
        1,
        1.25
    )

    plt.savefig(
        SENSITIVITY_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


# ============================================================
# PIPELINE FIGURE
# ============================================================

def create_pipeline_figure():
    """Create a schematic representation of the multimetric pipeline."""
    fig, ax = plt.subplots(
        figsize=(14, 7)
    )

    ax.set_xlim(
        0,
        1
    )

    ax.set_ylim(
        0,
        1
    )

    ax.axis(
        "off"
    )

    def add_box(x, y, w, h, text):
        """Add one labelled rectangular block to the pipeline figure."""
        rect = plt.Rectangle(
            (x, y),
            w,
            h,
            fill=False,
            linewidth=2
        )

        ax.add_patch(
            rect
        )

        ax.text(
            x + w / 2,
            y + h / 2,
            text,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold"
        )

    # ========================================================
    # POSITIONS
    #
    # Three input blocks are aligned on the left:
    #   Geometric Fidelity
    #   Size & Shape Correlation
    #   GPA Phenotypic Preservation
    #
    # Morphometric Fidelity integrates the latter two.
    # The Exploratory Global Score combines geometric and morphometric
    # evidence. EDMA remains descriptive and independent.
    # ========================================================

    left_x = 0.06
    middle_x = 0.41
    right_x = 0.75

    left_w = 0.22
    middle_w = 0.22
    right_w = 0.19

    box_h = 0.16

    y_geometric = 0.76
    y_size_shape = 0.53
    y_phenotypic = 0.30
    y_edma = 0.07

    y_morphometric = 0.415
    y_global = 0.47

    # --------------------------------------------------------
    # BLOCKS
    # --------------------------------------------------------

    add_box(
        left_x,
        y_geometric,
        left_w,
        box_h,
        "C2C + C2M\nGeometric Fidelity"
    )

    add_box(
        left_x,
        y_size_shape,
        left_w,
        box_h,
        "CS + PPD\nSize & Shape Correlation"
    )

    add_box(
        left_x,
        y_phenotypic,
        left_w,
        box_h,
        "GPA IoU\nPhenotypic Preservation"
    )

    add_box(
        left_x,
        y_edma,
        left_w,
        box_h,
        "EDMA\nDescriptive Analysis"
    )

    add_box(
        middle_x,
        y_morphometric,
        middle_w,
        box_h,
        "Morphometric Fidelity"
    )

    add_box(
        right_x,
        y_global,
        right_w,
        box_h,
        "Exploratory\nGlobal Score"
    )

    # --------------------------------------------------------
    # ARROWS
    # --------------------------------------------------------

    # Geometric Fidelity -> Exploratory Global Score.
    ax.annotate(
        "",
        xy=(
            right_x,
            y_global + box_h * 0.68
        ),
        xytext=(
            left_x + left_w,
            y_geometric + box_h / 2
        ),
        arrowprops=dict(
            arrowstyle="->",
            linewidth=2
        )
    )

    # Size & Shape Correlation -> Morphometric Fidelity.
    ax.annotate(
        "",
        xy=(
            middle_x,
            y_morphometric + box_h * 0.68
        ),
        xytext=(
            left_x + left_w,
            y_size_shape + box_h / 2
        ),
        arrowprops=dict(
            arrowstyle="->",
            linewidth=2
        )
    )

    # Phenotypic Preservation -> Morphometric Fidelity.
    ax.annotate(
        "",
        xy=(
            middle_x,
            y_morphometric + box_h * 0.32
        ),
        xytext=(
            left_x + left_w,
            y_phenotypic + box_h / 2
        ),
        arrowprops=dict(
            arrowstyle="->",
            linewidth=2
        )
    )

    # Morphometric Fidelity -> Exploratory Global Score.
    ax.annotate(
        "",
        xy=(
            right_x,
            y_global + box_h * 0.32
        ),
        xytext=(
            middle_x + middle_w,
            y_morphometric + box_h / 2
        ),
        arrowprops=dict(
            arrowstyle="->",
            linewidth=2
        )
    )

    fig.suptitle(
        "Multimetric Integration Pipeline",
        x=0.5,
        y=0.96,
        fontsize=16,
        fontweight="bold"
    )

    plt.tight_layout(
        rect=[0, 0.03, 1, 0.93]
    )

    plt.savefig(
        PIPELINE_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


# ============================================================
# BY-COUNTRY FIGURE
# ============================================================

def create_by_country_figure(combined):
    """Create the country-specific Exploratory Global Score comparison.

    Args:
        combined: Country-level integrated score table.
    """
    plot_df = combined[
        combined["Method"] != "SPG"
    ].copy()

    plot_df = plot_df[
        [
            "Method",
            "Country",
            "Exploratory_Global_Score"
        ]
    ].dropna()

    if plot_df.empty:
        return

    pivot = (
        plot_df
        .pivot(
            index="Method",
            columns="Country",
            values="Exploratory_Global_Score"
        )
        .reindex([
            method
            for method in METHODS
            if method != "SPG"
        ])
    )

    ax = pivot.plot(
        kind="bar",
        figsize=(11, 6)
    )

    ax.set_ylim(
        0,
        1
    )

    ax.set_xlabel(
        "Method"
    )

    ax.set_ylabel(
        "Exploratory Global Score"
    )

    ax.set_title(
        "Multimetric Exploratory Global Score by Country",
        fontsize=14,
        fontweight="bold"
    )

    plt.xticks(
        rotation=30,
        ha="right"
    )

    ax.legend(
        title="Country",
        frameon=False
    )

    # Display the exact score above each bar.
    for container in ax.containers:
        ax.bar_label(
            container,
            fmt="%.3f",
            padding=3,
            fontsize=8
        )

    plt.tight_layout()

    plt.savefig(
        BY_COUNTRY_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


# ============================================================
# EXCEL FORMATTING
# ============================================================

def style_excel_output():
    """Apply consistent visual formatting to both multimetric workbooks.

    The function modifies only workbook presentation. It does not alter
    numerical values, worksheet structure, rows or columns.
    """
    from openpyxl import load_workbook
    from openpyxl.styles import (
        Font,
        Alignment,
        PatternFill,
        Border,
        Side,
    )
    from openpyxl.formatting.rule import ColorScaleRule

    def _style_workbook(file_path: Path):
        """Apply the shared formatting scheme to one workbook."""
        if not file_path.exists():
            return

        wb = load_workbook(file_path)

        # Grey-blue header with red-yellow-green metric gradients.
        header_fill = PatternFill(
            fill_type="solid",
            fgColor="6F7C8E"
        )

        header_font = Font(
            bold=True,
            color="FFFFFF"
        )

        thin = Side(
            style="thin",
            color="D9DEE5"
        )

        medium = Side(
            style="medium",
            color="B8C2CC"
        )

        metric_keywords = [
            "score",
            "fidelity",
            "correlation",
            "separation",
            "phenotypic",
            "gpa",
            "iou",
            "cs",
            "ppd",
            "global",
        ]

        for ws in wb.worksheets:
            if ws.max_row == 0 or ws.max_column == 0:
                continue

            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            ws.sheet_view.showGridLines = False

            # Format the header row.
            for cell in ws[1]:
                cell.font = header_font
                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center",
                    wrap_text=True
                )
                cell.fill = header_fill
                cell.border = Border(
                    left=thin,
                    right=thin,
                    top=thin,
                    bottom=medium
                )

            ws.row_dimensions[1].height = 24

            # Apply subtle alternating row shading and thin borders.
            for row in ws.iter_rows(min_row=2):
                row_idx = row[0].row

                for cell in row:
                    cell.alignment = Alignment(
                        horizontal="center",
                        vertical="center",
                        wrap_text=True
                    )

                    cell.border = Border(
                        left=thin,
                        right=thin,
                        top=thin,
                        bottom=thin
                    )

                    if row_idx % 2 == 0:
                        cell.fill = PatternFill(
                            fill_type="solid",
                            fgColor="F7F9FC"
                        )

                    # Format numerical outputs consistently.
                    if (
                        isinstance(cell.value, (int, float))
                        and cell.value is not None
                    ):
                        if (
                            ws.cell(1, cell.column).value
                            == "Countries_used"
                        ):
                            cell.number_format = "0"
                        else:
                            cell.number_format = "0.0000"

            # Highlight SPG as the reference modality.
            if ws.max_row >= 2:
                headers = [
                    str(c.value).strip()
                    if c.value is not None
                    else ""
                    for c in ws[1]
                ]

                if "Method" in headers:
                    method_col = headers.index("Method") + 1

                    for r in range(
                        2,
                        ws.max_row + 1
                    ):
                        value = ws.cell(
                            r,
                            method_col
                        ).value

                        if str(value).strip().upper() == "SPG":
                            for c in range(
                                1,
                                ws.max_column + 1
                            ):
                                current_fill = ws.cell(
                                    r,
                                    c
                                ).fill

                                ws.cell(
                                    r,
                                    c
                                ).font = Font(
                                    bold=True
                                )

                                if c == method_col:
                                    ws.cell(
                                        r,
                                        c
                                    ).fill = PatternFill(
                                        fill_type="solid",
                                        fgColor="E8F1FB"
                                    )

            # Adjust column widths according to their content.
            for col_cells in ws.columns:
                col_letter = col_cells[0].column_letter
                max_len = 0

                for cell in col_cells:
                    if cell.value is not None:
                        max_len = max(
                            max_len,
                            len(str(cell.value))
                        )

                width = min(
                    max(
                        max_len + 2,
                        11
                    ),
                    45
                )

                # Allocate additional width to long-text columns.
                header_val = (
                    str(col_cells[0].value).strip().lower()
                    if col_cells[0].value is not None
                    else ""
                )

                if header_val in {
                    "summary",
                    "how_to_fill"
                }:
                    width = 65

                elif header_val in {
                    "method",
                    "country",
                    "field"
                }:
                    width = max(
                        width,
                        14
                    )

                ws.column_dimensions[
                    col_letter
                ].width = width

            # Apply conditional color scales to quantitative metric columns.
            if ws.max_row >= 2:
                for col_idx in range(
                    1,
                    ws.max_column + 1
                ):
                    header = ws.cell(
                        1,
                        col_idx
                    ).value

                    if header is None:
                        continue

                    header_text = (
                        str(header)
                        .strip()
                        .lower()
                    )

                    # Exclude clearly textual columns.
                    if header_text in {
                        "method",
                        "country",
                        "countries_used",
                        "summary",
                        "edma",
                        "field",
                        "how_to_fill"
                    }:
                        continue

                    if any(
                        keyword in header_text
                        for keyword in metric_keywords
                    ):
                        col_letter = ws.cell(
                            1,
                            col_idx
                        ).column_letter

                        ws.conditional_formatting.add(
                            f"{col_letter}2:"
                            f"{col_letter}{ws.max_row}",
                            ColorScaleRule(
                                start_type="num",
                                start_value=0,
                                start_color="F8696B",
                                mid_type="num",
                                mid_value=0.5,
                                mid_color="FFEB84",
                                end_type="num",
                                end_value=1,
                                end_color="63BE7B",
                            )
                        )

        wb.save(file_path)

    _style_workbook(INPUT_FILE)
    _style_workbook(OUTPUT_FILE)


def create_all_v2_outputs(
    combined,
    overall
):
    """Generate all supplementary V2.0/V2.2 analytical outputs.

    Args:
        combined: Country-level integrated score table.
        overall: Overall method-level results.

    Returns:
        dict: Ranking, sensitivity and stability tables.
    """
    FIG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    ranking = calculate_ranking(
        overall
    )

    sensitivity, stability = (
        calculate_sensitivity(
            overall
        )
    )

    create_radar_chart(
        overall
    )

    create_heatmap(
        overall
    )

    create_ranking_figure(
        ranking
    )

    create_sensitivity_figure(
        sensitivity
    )

    create_by_country_figure(
        combined
    )

    create_pipeline_figure()

    style_excel_output()

    return {
        "ranking": ranking,
        "sensitivity": sensitivity,
        "stability": stability,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    """Execute the complete multimetric evaluation workflow."""
    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # FIRST EXECUTION
    #
    # If the input workbook does not exist, create it and stop.
    # If it already exists, preserve it without overwriting it.
    # --------------------------------------------------------

    if not INPUT_FILE.exists():

        create_template()

        sys.exit(0)

    print(
        "\n"
        + "=" * 70
    )

    print(
        "MULTIMETRIC EVALUATION"
    )

    print(
        "=" * 70
    )

    # ========================================================
    # 1. GEOMETRIC EVALUATION
    # ========================================================

    raw_geometric = (
        read_geometric_metrics()
    )

    (
        geometric_group,
        geometric_country
    ) = (
        calculate_geometric_scores(
            raw_geometric
        )
    )

    # ========================================================
    # 2. GPA + DESCRIPTIVE EDMA / AUTOMATIC CS + PPD
    # ========================================================

    manual = (
        read_manual_metrics()
    )

    cs_ppd = (
        read_cs_ppd_metrics()
    )

    manual = (
        merge_cs_ppd_metrics(
            manual,
            cs_ppd
        )
    )

    manual_scores = (
        calculate_manual_scores(
            manual
        )
    )

    # ========================================================
    # 3. COMBINE COMPONENTS
    # ========================================================

    combined = (
        combine_scores(
            geometric_country,
            manual_scores
        )
    )

    # ========================================================
    # 4. OVERALL RESULTS
    # ========================================================

    overall = (
        calculate_overall(
            combined
        )
    )

    # ========================================================
    # 5. SAVE RESULTS
    # ========================================================

    save_results(
        combined,
        overall
    )

    # Generate the basic multimetric figure adapted to the current
    # V2.4 variable names.
    create_figure(
        overall
    )

    # ========================================================
    # 6. V2.2 — ROBUSTNESS AND PRESENTATION FIGURES
    # ========================================================

    v2_outputs = create_all_v2_outputs(
        combined,
        overall
    )

    # ========================================================
    # TERMINAL OUTPUT
    # ========================================================

    print(
        "\n"
        + "=" * 70
    )

    print(
        "Results"
    )

    print(
        "=" * 70
    )

    columns_to_show = [

        "Method",

        "P2P_C2C_score",

        "S2S_C2M_score",

        "Geometric_Fidelity",

        "GPA_IoU_score",

        "EDMA",

        "Phenotypic_Separation",

        "Phenotypic_Preservation",

        "CS_score",

        "PPD_score",

        "Size_and_Shape_Correlation",

        "Morphometric_Fidelity",

        "Exploratory_Global_Score",

        "Summary",
    ]

    columns_to_show = [

        col

        for col in columns_to_show

        if col in overall.columns
    ]

    if not overall.empty:

        print(

            overall[
                columns_to_show
            ]

            .round(3)

            .to_string(
                index=False
            )
        )

    print(
        "\nOUTPUT FILES CREATED:"
    )

    print(
        f"\nExcel file saved to:\n{OUTPUT_FILE}"
    )

    print(
        "  1. OVERALL"
    )

    print(
        "  2. BY_COUNTRY"
    )

    print(
        "  3. PROTOCOL"
    )

    print(
        f"\nFigures saved to:\n{FIG_DIR}"
    )

    print(
        "\n"
        + "=" * 70
    )


if __name__ == "__main__":
    main()
