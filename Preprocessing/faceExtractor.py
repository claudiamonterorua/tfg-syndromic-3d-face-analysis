"""
Crop facial meshes around the nose-tip landmark using a fixed spherical region.

For each input PLY mesh, the corresponding SPG landmark file is identified
from the coded participant ID. The facial surface is then restricted to a
spherical region centred on the nose tip, small disconnected components are
removed, and the resulting mesh is exported to the designated output folder.
"""

import os
import re
import shutil
import tempfile

import numpy as np
import open3d as o3d
import pymeshlab as ml


def process_mesh(mesh_path, landmarks_path):
    """Crop and clean a facial mesh using the nose-tip landmark.

    The third landmark is used as the centre of a spherical facial region.
    Vertices outside this region are removed, followed by elimination of
    disconnected components below the specified diameter threshold.

    Args:
        mesh_path: Path to the input PLY facial mesh.
        landmarks_path: Path to the corresponding landmark TXT file.
    """
    # Load the facial mesh.
    ms = ml.MeshSet()
    ms.load_new_mesh(mesh_path)

    # Load the corresponding landmark configuration.
    msl = ml.MeshSet()
    msl.load_new_mesh(
        landmarks_path,
        separator=2
    )

    # import pymeshlab
    # print(pymeshlab.filter_list())

    # Extract the nose-tip coordinates from the landmark configuration.
    nose_tip = msl.current_mesh().vertex_matrix()[2, :]

    # Define the spherical cropping radius around the nose tip.
    # A radius of 95 mm is used in the current processing configuration.
    radius = 95.0  # 95 mm / 120 mm for larger facial regions.

    ms.compute_selection_by_condition_per_vertex(
        condselect=(
            f"(x-{nose_tip[0]})^2 + "
            f"(y-{nose_tip[1]})^2 + "
            f"(z-{nose_tip[2]})^2 <= {radius**2}"
        )
    )

    # Invert the selection so that vertices outside the sphere are removed.
    ms.apply_selection_inverse(
        invverts=True
    )

    ms.meshing_remove_selected_vertices()

    # Remove small disconnected components remaining after cropping.
    ms.meshing_remove_connected_component_by_diameter(
        mincomponentdiag=ml.PercentageValue(50)
    )

    # Define the output filename while preserving the original extension.
    filename, ext = os.path.splitext(
        os.path.basename(mesh_path)
    )

    transformed_mesh_path = os.path.join(
        output_folder,
        filename + ext
    )

    # Create a temporary local path before transferring the final mesh.
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(
        temp_dir,
        filename + ext
    )

    # Save the processed mesh locally without additional texture or color data.
    ms.save_current_mesh(
        temp_path,
        binary=False,
        save_wedge_texcoord=False,
        save_wedge_color=False,
        save_face_color=False
    )

    # Move the processed mesh to the designated OneDrive output directory.
    shutil.move(
        temp_path,
        transformed_mesh_path
    )

    # ms.save_current_mesh(
    #     transformed_mesh_path,
    #     binary=False,
    #     save_wedge_texcoord=False,
    #     save_wedge_color=False,
    #     save_face_color=False
    # )

    print(
        f"Processed mesh saved to: {transformed_mesh_path}"
    )


# Alternative SPG input directory.
# input_folder = (
#     r"C:\path\to\project\02_Dades\SPG\01_Filtrades"
# )

input_folder = (
    r"C:\path\to\project\02_Dades\MP\03_Alineades"
)

# Alternative SPG output directory.
# output_folder = (
#     r"C:\path\to\project\02_Dades\SPG\02_Retallades"
# )

output_folder = (
    r"C:\path\to\project\02_Dades\MP\04_Retallades"
)

os.makedirs(
    output_folder,
    exist_ok=True
)

# Process every PLY mesh in the selected input directory.
for filename in os.listdir(input_folder):

    if filename.endswith(".ply"):

        mesh_path = os.path.join(
            input_folder,
            filename
        )

        landmarks_folder = (
            r"C:\path\to\project\02_Dades\SPG\21_landmarks"
        )

        # Extract the coded participant identifier from the mesh filename.
        base_filename = re.split(
            r"[_-]",
            os.path.splitext(filename)[0]
        )[0]

        landmarks_path = None

        # Search recursively for the corresponding landmark file.
        for root, _, files in os.walk(landmarks_folder):

            for f in files:

                if f.lower().endswith(".txt"):

                    landmark_id = re.split(
                        r"[_-]",
                        os.path.splitext(f)[0]
                    )[0]

                    if landmark_id == base_filename:
                        landmarks_path = os.path.join(
                            root,
                            f
                        )
                        break

            if landmarks_path is not None:
                break

        if landmarks_path is not None:
            print(
                f"Processing mesh: {mesh_path}"
            )

            process_mesh(
                mesh_path,
                landmarks_path
            )

        else:
            print(
                f"No landmarks were found for: {mesh_path}"
            )