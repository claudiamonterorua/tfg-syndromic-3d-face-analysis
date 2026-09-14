"""
Preprocess and reconstruct MP facial meshes.

For each input PLY mesh, vertices with zero-valued normals are removed,
the geometry is scaled and rotated, the mesh is centred at the origin, and
a screened Poisson surface reconstruction is applied. The processed mesh is
temporarily saved locally before being moved to the designated output folder.
"""

import os
import shutil
import tempfile

import numpy as np
import pymeshlab as ml


def process_mesh(input_path, output_folder):
    """Apply geometric preprocessing and surface reconstruction to a mesh.

    Args:
        input_path: Path to the input PLY mesh.
        output_folder: Directory where the processed mesh will be stored.
    """
    ms = ml.MeshSet()
    ms.load_new_mesh(input_path)

    # Remove vertices whose normal components are all equal to zero.
    ms.compute_selection_by_condition_per_vertex(
        condselect='(nx==0.0) && (ny==0.0) && (nz==0.0)'
    )
    ms.meshing_remove_selected_vertices()

    # Apply the predefined spatial scaling.
    scale_factors = {
        'x': 1000.0,
        'y': 1.0,
        'z': 1.0
    }
    ms.compute_matrix_from_scaling_or_normalization(
        axisx=scale_factors['x'],
        axisy=scale_factors['y']
    )

    # Apply the predefined LSA rotation.
    rotation_values = {
        'axis': 1,
        'angle': 180.0
    }
    ms.compute_matrix_from_rotation(
        rotaxis=rotation_values['axis'],
        angle=rotation_values['angle']
    )

    # Determine the geometric centre from the mesh bounding box.
    vertices = ms.current_mesh().vertex_matrix()
    bbox_min = np.min(vertices, axis=0)
    bbox_max = np.max(vertices, axis=0)
    center = (bbox_min + bbox_max) / 2.0

    # Translate the mesh centre to the coordinate origin.
    ms.compute_matrix_from_translation(
        axisx=-center[0],
        axisy=-center[1],
        axisz=-center[2]
    )

    # Reconstruct the facial surface using screened Poisson reconstruction.
    ms.generate_surface_reconstruction_screened_poisson(
        depth=10
    )

    # Define the final path for the processed mesh.
    filename, ext = os.path.splitext(
        os.path.basename(input_path)
    )
    output_path = os.path.join(
        output_folder,
        filename + ext
    )

    # Define a temporary local path.
    temp_folder = tempfile.gettempdir()
    temp_path = os.path.join(
        temp_folder,
        filename + ext
    )

    # Save the processed mesh locally before transfer.
    ms.save_current_mesh(
        temp_path,
        binary=False
    )

    # Move the processed mesh to the OneDrive output directory.
    shutil.move(
        temp_path,
        output_path
    )

    # ms.save_current_mesh(output_path, binary=False)

    print(f"Saved: {output_path}")


input_folder = (
    "C:\\path\\to\project\\02_Dades\\MP\\01_Filtrades"
)

output_folder = (
    "C:\\path\\to\project\\02_Dades\\MP\\02_Models3D"
)

# Process every PLY mesh in the input directory.
for filename in os.listdir(input_folder):
    if filename.endswith(".ply"):
        input_path = os.path.join(
            input_folder,
            filename
        )

        # Process the current mesh.
        process_mesh(
            input_path,
            output_folder
        )