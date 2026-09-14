"""
Scale and convert HRN facial meshes to PLY format.

The script applies a uniform scaling factor to each HRN OBJ mesh, optionally
transfers texture information to per-vertex color, and exports the processed
mesh as a PLY file. Mid-resolution models retain texture-derived color
information, whereas High-resolution models are exported without this step.
"""

import os
import shutil
import tempfile

import pymeshlab as ml


# Uniform scaling factor applied to all meshes.
SCALE = 120.0


def process_mesh(mesh_path, use_texture):
    """Scale and export a single HRN mesh.

    Args:
        mesh_path: Path to the input OBJ mesh.
        use_texture: Whether texture information should be transferred to
            per-vertex color before export.
    """
    ms = ml.MeshSet()

    ms.load_new_mesh(mesh_path)

    # Apply uniform scaling to the complete mesh.
    ms.compute_matrix_from_scaling_or_normalization(
        axisx=SCALE,
        axisy=1.0,
        uniformflag=True
    )

    # Transfer texture information to vertex colors when required.
    if use_texture:
        ms.transfer_texture_to_color_per_vertex()

    # Define the final PLY output path.
    final_ply = os.path.splitext(mesh_path)[0] + ".ply"

    print(mesh_path)

    print(final_ply)

    print(ms.current_mesh().vertex_number(), "vertices")

    print(ms.current_mesh().face_number(), "faces")

    try:

        # ----------------------------------------------------
        # Temporary directory without accented characters
        # ----------------------------------------------------

        temp_dir = os.path.join(
            tempfile.gettempdir(),
            "HRN_TEMP"
        )

        os.makedirs(
            temp_dir,
            exist_ok=True
        )

        temp_ply = os.path.join(
            temp_dir,
            os.path.basename(final_ply)
        )

        # Save the processed mesh to a temporary local directory first.
        ms.save_current_mesh(
            temp_ply,
            binary=False,
            save_wedge_texcoord=False,
            save_wedge_color=False,
            save_face_color=False
        )

        # Copy the temporary file to its final destination.
        shutil.copy2(
            temp_ply,
            final_ply
        )

        # Remove the temporary copy after successful transfer.
        os.remove(temp_ply)

        print("Saved")

    except Exception as e:

        import traceback

        print(f"\nError: {mesh_path}")

        traceback.print_exc()

        print(repr(e))


# ==========================================
# Root directory
# ==========================================

folder_root = (
    r"C:\path\to\project\02_Dades\HRN\HRN3\01_Raw_Post"
)


# ==========================================
# Process all participant meshes
# ==========================================

for root, _, files in os.walk(folder_root):

    for file_name in files:

        mesh_path = os.path.join(
            root,
            file_name
        )

        if file_name.endswith("_mid.obj"):

            process_mesh(
                mesh_path,
                use_texture=True
            )

        elif file_name.endswith("_high.obj"):

            process_mesh(
                mesh_path,
                use_texture=False
            )


print("\nProcess completed!")