"""
Manage and organize photographs acquired in multi-camera shots for multiple
participants within an acquisition session.

The script groups photographs according to acquisition time, verifies that the
expected cameras contributed one image to each shot, displays the images for
manual quality review, and stores accepted photographs using a standardized
folder and filename structure.
"""

import os
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import shutil
from PIL import Image
from digiCamControlPython import Camera
from collections import defaultdict


def readConfig():
    """Load the acquisition configuration from the JSON file.

    Returns:
        dict: Configuration parameters stored in ``config/config.json``.
    """
    config_file = os.path.join("config", "config.json")
    with open(config_file, "r") as f:
        return json.load(f)


def createSessionFolder(destination_path):
    """Create the directory corresponding to the current acquisition session.

    Args:
        destination_path (str): Root directory where session data are stored.

    Returns:
        str: Path to the session directory.
    """
    session_name = f"SESION_{datetime.now().strftime('%Y_%m_%d')}"
    session_path = os.path.join(destination_path, session_name)
    os.makedirs(session_path, exist_ok=True)
    return session_path


def getLastShotNumber(participant_path):
    """Retrieve the highest existing shot number for a participant.

    Args:
        participant_path (str): Directory containing the participant's shots.

    Returns:
        int: Highest shot number found, or 0 when no previous shots exist.
    """
    existing_shots = [
        d for d in os.listdir(participant_path)
        if os.path.isdir(os.path.join(participant_path, d))
        and d.startswith("shot_")
    ]

    if existing_shots:
        return max(int(name.split("_")[1]) for name in existing_shots)
    return 0


def moveToShotFolder(
    participant_path,
    participant_name,
    camera_name_mapping,
    photo_group
):
    """Move an accepted image group to its corresponding shot directory.

    Each photograph is renamed according to the camera, shot number and coded
    participant identifier before being moved.

    Args:
        participant_path (str): Directory assigned to the participant.
        participant_name (str): Coded participant identifier.
        camera_name_mapping (dict): Mapping between camera IDs and labels.
        photo_group (list): Photographs belonging to the same acquisition shot.
    """
    last_shot_number = getLastShotNumber(participant_path)
    shot_number = last_shot_number + 1
    shot_name = f"shot_{str(shot_number).zfill(5)}"
    shot_path = os.path.join(participant_path, shot_name)
    os.makedirs(shot_path, exist_ok=True)

    for photo in photo_group:
        camera_id = next(
            (
                camera
                for camera in camera_name_mapping
                if camera in os.path.basename(photo)
            ),
            None
        )

        if camera_id:
            camera_name = camera_name_mapping[camera_id]
            new_name = (
                f"CAM_{camera_name}_SHOT_{str(shot_number).zfill(5)}"
                f"_PART_{participant_name}.jpg"
            )
            dest_path = os.path.join(shot_path, new_name)
            shutil.move(photo, dest_path)
            print(f"Photo renamed to {new_name}")
        else:
            dest_path = os.path.join(
                shot_path,
                os.path.basename(photo)
            )
            shutil.move(photo, dest_path)

    print(f"Photos are being moved to {shot_path}\n")


def showPhotos(photo_group, camera_name_mapping):
    """Display the photographs from one shot in a fixed camera arrangement.

    Missing photographs are represented by a neutral placeholder to preserve
    the expected multi-camera layout during manual review.

    Args:
        photo_group (list): Photographs belonging to the same shot.
        camera_name_mapping (dict): Mapping between camera IDs and labels.
    """
    label_order = [
        "1", "2", "3", "4", "5",
        "A", "B", "C", "D", "E"
    ]
    label_to_photo = {
        label: None
        for label in label_order
    }

    for photo in photo_group:
        basename = os.path.basename(photo)

        for cam_id, cam_label in camera_name_mapping.items():
            if cam_id in basename and cam_label in label_order:
                label_to_photo[cam_label] = photo

    fig, axes = plt.subplots(
        2,
        5,
        figsize=(10, 5)
    )
    axes = axes.flatten()

    for idx, label in enumerate(label_order):
        ax = axes[idx]
        photo_path = label_to_photo[label]

        if photo_path and os.path.exists(photo_path):
            img = Image.open(photo_path)
            ax.imshow(np.array(img))
        else:
            placeholder = np.full(
                (400, 600, 3),
                220,
                dtype=np.uint8
            )
            ax.imshow(placeholder)

        ax.set_title(
            f"Camera {label}",
            fontsize=12
        )
        ax.axis("off")

    plt.tight_layout()
    plt.show()


def deletePhotos(photo_paths):
    """Delete photographs associated with a rejected or invalid shot.

    Args:
        photo_paths (list): Paths of the photographs to remove.
    """
    for photo in photo_paths:
        try:
            os.remove(photo)
        except Exception as e:
            print(
                f"ERROR: The photo {photo} could not be deleted: {e}"
            )


def groupPhotosByTime(all_photos, max_delay=4):
    """Group photographs acquired within a common temporal window.

    Images are ordered by creation time and assigned to the same group when
    their acquisition time differs by no more than ``max_delay`` seconds from
    the first image of the current group.

    Args:
        all_photos (list): Paths of all photographs awaiting processing.
        max_delay (int, optional): Maximum temporal separation, in seconds,
            between photographs belonging to the same shot. Defaults to 4.

    Returns:
        list: Groups of photographs associated with individual shots.
    """
    all_photos.sort(
        key=lambda x: os.path.getctime(x)
    )

    groups = []
    current_group = []

    for i, photo in enumerate(all_photos):
        if not current_group:
            current_group.append(photo)
        else:
            diff = (
                os.path.getctime(photo)
                - os.path.getctime(current_group[0])
            )

            if diff <= max_delay:
                current_group.append(photo)
            else:
                groups.append(current_group)
                current_group = [photo]

    if current_group:
        groups.append(current_group)

    return groups


def processAllGroups(
    temp_path,
    session_path,
    participant_name,
    camera_name_mapping,
    ordered_detected_names
):
    """Review and process all image groups associated with one participant.

    Each group is checked to verify that every connected camera contributed
    exactly one photograph. Valid groups are displayed for manual acceptance;
    rejected or invalid images are deleted.

    Args:
        temp_path (str): Temporary directory containing captured photographs.
        session_path (str): Current acquisition-session directory.
        participant_name (str): Coded participant identifier.
        camera_name_mapping (dict): Mapping between camera IDs and labels.
        ordered_detected_names (list): Labels of currently detected cameras.
    """
    all_photos = [
        os.path.join(temp_path, f)
        for f in os.listdir(temp_path)
        if f.lower().endswith(
            ('.jpg', '.jpeg', '.png')
        )
    ]

    photo_groups = groupPhotosByTime(all_photos)

    print()
    print(
        f"📸 {len(photo_groups)} acquisition bursts were found.\n"
    )

    any_group_saved = False
    participant_path = os.path.join(
        session_path,
        participant_name
    )

    label_order = [
        "1", "2", "3", "4", "5",
        "A", "B", "C", "D", "E"
    ]

    for photo_group in photo_groups:
        print(
            f"Group containing {len(photo_group)} photo(s):"
        )

        errors = []

        detected_ids = [
            cam_id
            for cam_id, cam_label
            in camera_name_mapping.items()
            if cam_label in ordered_detected_names
        ]

        for cam_id, cam_label in camera_name_mapping.items():
            count = sum(
                1
                for photo in photo_group
                if cam_id in os.path.basename(photo)
            )

            if cam_label in ordered_detected_names:
                if count == 1:
                    print(
                        f"- Camera {cam_label}: 1."
                    )
                else:
                    print(
                        f"- ⚠️  ERROR: Camera {cam_label}: "
                        f"Expected 1, but found {count}."
                    )
                    errors.append(True)
            else:
                print(
                    f"- Camera {cam_label}: Not connected."
                )

        if not errors:
            showPhotos(
                photo_group,
                camera_name_mapping
            )

            confirm = input(
                "Accept? (Y/N): "
            ).strip().lower()

            if confirm == 'y':
                if not os.path.exists(participant_path):
                    os.makedirs(participant_path)

                print(
                    "✅ Group accepted. Saving photo(s)..."
                )

                moveToShotFolder(
                    participant_path,
                    participant_name,
                    camera_name_mapping,
                    photo_group
                )

                any_group_saved = True

            else:
                print(
                    "❌ Group not accepted. Deleting photo(s)...\n"
                )
                deletePhotos(photo_group)

        else:
            print(
                "❌ Group discarded. Deleting photo(s)...\n"
            )
            deletePhotos(photo_group)

    if (
        not any_group_saved
        and os.path.exists(participant_path)
    ):
        if not os.listdir(participant_path):
            os.rmdir(participant_path)


def initialize_parameters():
    """Initialize camera detection and acquisition parameters.

    The function loads the configured camera mapping, identifies connected
    cameras, reports missing devices, configures image filename templates and
    enables autofocus.

    Returns:
        tuple: Camera-name mapping and ordered labels of detected cameras.
    """
    config = readConfig()
    camera_name_mapping = config.get(
        "camera_name_mapping",
        {}
    )

    camera_control = Camera()
    cameras_detected = camera_control.list_cameras()

    ordered_detected_names = []

    for camera_id in camera_name_mapping.keys():
        if camera_id in cameras_detected:
            ordered_detected_names.append(
                camera_name_mapping[camera_id]
            )

    print(
        "Detected cameras:",
        ", ".join(ordered_detected_names),
        "\n"
    )

    expected_ids = set(
        camera_name_mapping.keys()
    )
    detected_ids = set(
        cameras_detected
    )

    missing = expected_ids - detected_ids

    ordered_missing_names = [
        camera_name_mapping[cam_id]
        for cam_id in camera_name_mapping
        if cam_id in missing
    ]

    if ordered_missing_names:
        print(
            f"⚠️  ERROR: Missing cameras: "
            f"{', '.join(ordered_missing_names)}\n"
        )

        confirm = input(
            "Do you want to continue the operation anyway? "
            "(Y/N): "
        ).strip().lower()

        print()

        if confirm != 'y':
            print("⛔ Operation cancelled.")
            exit()

    for camera_id in detected_ids:
        camera_control.select_camera(
            camera_id
        )

        file_name_template = (
            "CAM_[Camera Name]_IMG_[Camera Counter 4 digit]"
        )

        camera_control.set_image_name(
            file_name_template
        )

        camera_display_name = camera_name_mapping.get(
            camera_id,
            camera_id
        )

        print(
            f"Photo filename template configured for camera "
            f"{camera_display_name}: {file_name_template}"
        )

        camera_control.set_autofocus(True)

    return camera_name_mapping, ordered_detected_names


def main():
    """Run the multi-camera acquisition review workflow."""
    camera_name_mapping, ordered_detected_names = initialize_parameters()

    config = readConfig()

    temp_path = config[
        "temporary_folder"
    ].replace('"', '')

    final_path = config[
        "final_folder"
    ].replace('"', '')

    session_path = createSessionFolder(
        final_path
    )

    while True:
        participant_name = input(
            "👤 Enter the participant number "
            "(or press ENTER to exit): "
        ).strip()

        if not participant_name:
            break

        print()

        print(
            f"➡️  Participant '{participant_name}' registered.\n"
        )

        print(
            "📸 It is time to capture the image bursts.\n"
        )

        input(
            "🔍🗂️  Once all photographs have been captured, "
            "press ENTER to begin the review..."
        )

        processAllGroups(
            temp_path,
            session_path,
            participant_name,
            camera_name_mapping,
            ordered_detected_names
        )

        print("Participant completed.\n")


if __name__ == "__main__":
    main()