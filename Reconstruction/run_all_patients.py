"""
Run batch HRN facial reconstruction for multiple image configurations.

The script initializes the HRN reconstructor once and sequentially processes
all participant directories available for HRN3, HRN5, and HRN10. Existing
outputs are skipped only when the complete expected file set is present.
Incomplete or inconsistent outputs are removed and regenerated.

Any reconstruction errors are recorded in a dedicated log file without
interrupting the remaining batch-processing workflow.
"""

import os
from types import SimpleNamespace

from demo import create_reconstructor, process_patient


HRN_ROOT = "/path/to/HRN"

INPUT_ROOT = os.path.join(
    HRN_ROOT,
    "assets/examples/00_Pre"
)

OUTPUT_ROOT = os.path.join(
    HRN_ROOT,
    "assets/examples/01_Post"
)

LOG_FILE = os.path.join(
    HRN_ROOT,
    "run_errors.log"
)

# Clear the error log before starting a new processing run.
open(LOG_FILE, "w").close()

# Define the HRN reconstruction parameters once for the complete batch.
args = SimpleNamespace(
    checkpoints_dir="assets/pretrained_models",
    name="hrn_v1.1",
    epoch="10"
)

print("Loading HRN...")
reconstructor = create_reconstructor(args)
print("HRN loaded.\n")


# Process each configured HRN image-set size sequentially.
for hrn in ["HRN3", "HRN5", "HRN10"]:

    input_hrn = os.path.join(
        INPUT_ROOT,
        hrn
    )

    output_hrn = os.path.join(
        OUTPUT_ROOT,
        hrn
    )

    os.makedirs(
        output_hrn,
        exist_ok=True
    )

    # Identify participant directories available for the current HRN setting.
    pacientes = sorted(
        p for p in os.listdir(input_hrn)
        if os.path.isdir(
            os.path.join(
                input_hrn,
                p
            )
        )
    )

    print(
        f"\n===== {hrn} ({len(pacientes)} participants) ====="
    )

    for paciente in pacientes:

        input_patient = os.path.join(
            input_hrn,
            paciente
        )

        output_patient = os.path.join(
            output_hrn,
            paciente
        )

        os.makedirs(
            output_patient,
            exist_ok=True
        )

        # Exact set of files expected from a successful HRN reconstruction.
        esperado = {
            f"{paciente}.jpg",
            f"{paciente}.gif",
            f"{paciente}_mid.obj",
            f"{paciente}_high.obj",
            f"{paciente}_mid.mtl",
            f"{paciente}_mid.jpg",
        }

        archivos = {
            f for f in os.listdir(output_patient)
            if os.path.isfile(
                os.path.join(
                    output_patient,
                    f
                )
            )
        }

        # Skip the participant only when exactly the six expected files exist.
        if archivos == esperado:
            print(
                f"{paciente} already completed. Skipping..."
            )
            continue

        # Remove all existing outputs when files are missing or unexpected
        # files are present, ensuring complete regeneration.
        if archivos:
            print(
                f"{paciente}: incomplete or incorrect results. "
                "Regenerating..."
            )

            for f in archivos:
                os.remove(
                    os.path.join(
                        output_patient,
                        f
                    )
                )

        print(
            f"Processing {paciente}..."
        )

        try:
            process_patient(
                input_patient,
                output_patient,
                reconstructor
            )

        except Exception as e:
            # Record the participant-specific error while allowing the
            # remaining batch to continue processing.
            with open(LOG_FILE, "a") as f:
                f.write(
                    f"\n===== {hrn} - {paciente} =====\n"
                )
                f.write(
                    str(e)
                )
                f.write(
                    "\n"
                )


print("\nProcess completed.")

if os.path.getsize(LOG_FILE) == 0:
    print("No errors.")
else:
    print(
        f"Review: {LOG_FILE}"
    )