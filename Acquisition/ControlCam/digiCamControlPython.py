"""
Python interface for controlling cameras through digiCamControl.

This module provides camera-selection, image-capture, transfer, exposure,
focus, and configuration utilities through CameraControlRemoteCmd.exe.
It extends the original digiCamControlPython workflow with functions required
for the multi-camera acquisition system used in this project.
"""

import json
import os
import subprocess
import time
import psutil
from typing import Union, List


def load_config():
    """Load acquisition parameters from the JSON configuration file.

    Returns:
        dict: Configuration data loaded from ``config/config.json``.
            An empty dictionary is returned if the file is not found.
    """
    config_file = os.path.join("config", "config.json")

    if not os.path.isfile(config_file):
        print(f"Error: Config file {config_file} not found.")
        return {}

    with open(config_file, "r") as f:
        config_data = json.load(f)

    return config_data


# Python interface for controlling digiCamControl through its command-line
# system. digiCamControl (https://digicamcontrol.com/) must be installed.
# Original project documentation:
# https://github.com/Eagleshot/digiCamControlPython


class Camera:
    """Provide a Python interface to digiCamControl.

    The class communicates with CameraControlRemoteCmd.exe to select cameras,
    acquire images, configure capture parameters, transfer files, and retrieve
    camera settings.

    If no installation directory is provided, the standard digiCamControl
    installation path is used.
    """

    def __init__(
        self,
        exe_dir: str = r'C:\Program Files (x86)\digiCamControl'
    ):
        """Initialize the digiCamControl interface.

        Args:
            exe_dir: Directory containing the digiCamControl executables.
        """
        self.capture_command = "Capture"  # Default capture command.

        # Verify that the digiCamControl command-line executable exists.
        if os.path.exists(exe_dir + r"/CameraControlRemoteCmd.exe"):
            self.exe_dir = exe_dir

            # Start digiCamControl automatically if it is not already running.
            if not "CameraControl.exe" in (
                i.name() for i in psutil.process_iter()
            ):
                subprocess.Popen(self.exe_dir + r"/CameraControl.exe")
                time.sleep(10)

        else:
            print("Error: digiCamControl not found.")

    # MODIFIED FOR MULTI-CAMERA ACQUISITION.
    def list_cameras(self):
        """Retrieve the identifiers of all cameras detected by digiCamControl.

        Returns:
            list: Camera identifiers reported by digiCamControl. An empty
                list is returned if the response cannot be parsed or the
                command fails.
        """
        try:
            command = (
                f'"{self.exe_dir}\\CameraControlRemoteCmd.exe" '
                f'/c list cameras'
            )
            output = (
                subprocess.check_output(command, shell=True)
                .decode()
                .strip()
            )

            # Extract camera identifiers from the response:[...]; structure.
            import re

            match = re.search(r'response:\[(.*?)\];', output)

            if match:
                raw_ids = match.group(1)
                camera_ids = [
                    cam.strip().strip('"')
                    for cam in raw_ids.split(",")
                    if cam.strip()
                ]
                return camera_ids

            print(
                "Error: Camera identifiers could not be extracted "
                f"from output: {output}"
            )
            return []

        except subprocess.CalledProcessError as e:
            print(f"Error while listing cameras: {e}")
            return []

    # MODIFIED FOR MULTI-CAMERA ACQUISITION.
    def select_camera(self, camera_id: str):
        """Select the camera to which subsequent commands are applied.

        Args:
            camera_id: digiCamControl identifier of the camera to select.
        """
        try:
            command = (
                f'"{self.exe_dir}\\CameraControlRemoteCmd.exe" '
                f'/c set camera {camera_id}'
            )
            subprocess.run(command, shell=True, check=True)
            print(f"Camera {camera_id} selected.")

        except subprocess.CalledProcessError as e:
            print(f"Error while selecting camera {camera_id}: {e}")

    # MODIFIED FOR MULTI-CAMERA ACQUISITION.
    def get_last_captured(
        self,
        camera_id: str
    ) -> Union[int, str]:
        """Retrieve the latest captured image associated with one camera.

        Images are searched within the session directory defined in the JSON
        configuration. The most recently modified JPEG file containing the
        specified camera identifier is returned.

        Args:
            camera_id: Identifier of the camera whose latest image is required.

        Returns:
            Union[int, str]: Path to the most recent image, or -1 if the image
                cannot be located or another error occurs.
        """
        try:
            config = load_config()

            # Retrieve the session directory from the JSON configuration.
            temp_folder = config.get(
                "session_folder",
                ""
            ).strip('"')

            if not temp_folder or not os.path.exists(temp_folder):
                print(
                    f"Error: Temporary folder {temp_folder} does not exist."
                )
                return -1

            # Select JPEG files containing the camera identifier.
            files = [
                f for f in os.listdir(temp_folder)
                if camera_id in f
                and f.lower().endswith(".jpg")
            ]

            if not files:
                print(
                    f"Error: No images found in {temp_folder} "
                    f"for camera {camera_id}.\n"
                )
                return -1

            # Sort by modification time and select the latest image.
            files.sort(
                key=lambda f: os.path.getmtime(
                    os.path.join(temp_folder, f)
                ),
                reverse=True
            )

            last_image_path = os.path.join(
                temp_folder,
                files[0]
            )

            print(
                f"Last captured image is {last_image_path} "
                f"for camera {camera_id}.\n"
            )
            return last_image_path

        except Exception as e:
            print(
                "Unexpected error during 'get last captured' "
                f"for camera {camera_id}: {e}"
            )
            return -1

        # %% Capture
    # def capture(
    #     self,
    #     location: str = ""
    # ) -> Union[int, str]:
    #     """
    #     Capture an image using the configured filename and destination.
    #
    #     Args:
    #         location: Optional output location and filename.
    #
    #     Returns:
    #         Union[int, str]: Capture result.
    #     """
    #     r = self.run_cmd(
    #         self.capture_command + " " + location
    #     )
    #
    #     if r == 0:
    #         print("Captured image.")
    #
    #     return self.__get_cmd("lastcaptured")

    def capture(
        self,
        location: str = ""
    ) -> Union[int, str]:
        """Capture an image through CameraControlRemoteCmd.exe.

        Args:
            location: Optional destination and filename for the captured image.
                If omitted, digiCamControl uses its configured defaults.

        Returns:
            Union[int, str]: Path associated with the last captured image,
                or -1 if the capture fails.
        """
        # Construct the full path to the digiCamControl executable.
        executable = os.path.join(
            self.exe_dir,
            "CameraControlRemoteCmd.exe"
        )

        # Ensure that the required executable is available.
        if not os.path.exists(executable):
            print(
                f"Error: Executable not found at {executable}"
            )
            return -1

        try:
            # Execute the image-capture command.
            full_command = (
                f'cd "{self.exe_dir}" && '
                f'"{executable}" /c capture {location}'
            ).strip()

            result = subprocess.check_output(
                full_command,
                shell=True
            ).decode()

            # A null or empty response indicates successful execution.
            if 'null' in result or '""' in result:
                print("Image captured.\n")
            else:
                print(f"Error: During capture {result}")
                return -1

            # Retrieve information associated with the latest image.
            return self.__get_last_captured()

        except subprocess.CalledProcessError as e:
            print(
                "Command failed with error code: "
                f"{e.returncode} "
                f"{e.output.decode() if e.output else 'No output'}"
            )
            return -1

        except Exception as e:
            print(
                f"Unexpected error during capture: {e}"
            )
            return -1

    def download_last_photo(
        self,
        save_directory_path: str,
        image_name: str
    ) -> Union[str, int]:
        """Download and rename the latest image captured by the camera.

        Args:
            save_directory_path: Destination directory for the image.
            image_name: Filename assigned to the downloaded image.

        Returns:
            Union[str, int]: Path to the renamed image if successful,
                or -1 if the operation fails.
        """
        try:
            # Create the destination directory when necessary.
            if not os.path.exists(save_directory_path):
                os.makedirs(save_directory_path)
                print(
                    f"Created save directory {save_directory_path}"
                )

            # Construct the executable path.
            executable = os.path.join(
                self.exe_dir,
                "CameraControlRemoteCmd.exe"
            )

            # Ensure that the executable is available.
            if not os.path.exists(executable):
                print(
                    f"Error: Executable not found at {executable}"
                )
                return -1

            # Configure the default destination directory.
            set_default_download_command = (
                f'cd "{self.exe_dir}" && '
                f'"{executable}" /c set defaultdownload '
                f'"{save_directory_path}"'
            )

            subprocess.check_call(
                set_default_download_command,
                shell=True
            )

            print(
                "Set default download directory to "
                f"{save_directory_path}\n"
            )

            # Retrieve the path of the most recently captured image.
            get_last_captured_command = (
                f'cd "{self.exe_dir}" && '
                f'"{executable}" /c get lastcaptured'
            )

            last_image_path = (
                subprocess.check_output(
                    get_last_captured_command,
                    shell=True
                )
                .decode()
                .strip()
            )

            if not last_image_path:
                print(
                    "Error: No image path received for the "
                    "last captured image."
                )
                return -1

            print(
                "Last captured image path on camera "
                f"{last_image_path}\n"
            )

            # Download the most recently captured image.
            download_command = (
                f'cd "{self.exe_dir}" && '
                f'"{executable}" /c download '
                f'{last_image_path} "{save_directory_path}"'
            )

            print('=============')
            print(
                f"Download command: {download_command}"
            )
            print('=============')

            subprocess.check_call(
                download_command,
                shell=True
            )

            # Rename the downloaded image using the requested filename.
            original_file_path = os.path.join(
                save_directory_path,
                os.path.basename(last_image_path)
            )

            target_file_path = os.path.join(
                save_directory_path,
                image_name
            )

            if os.path.exists(original_file_path):
                os.rename(
                    original_file_path,
                    target_file_path
                )
                print(
                    "Renamed downloaded image to "
                    f"{target_file_path}"
                )
                return target_file_path

            print(
                "Error: Image download failed or file not found."
            )
            return -1

        except subprocess.CalledProcessError as e:
            print(
                "Command failed with error code: "
                f"{e.returncode} "
                f"{e.output.decode() if e.output else 'No output'}"
            )
            return -1

        except Exception as e:
            print(
                f"Unexpected error during image download: {e}"
            )
            return -1

    # %% Folder
    def set_folder(self, folder: str):
        """Set the directory in which captured images are stored.

        Args:
            folder: Destination directory used by digiCamControl.
        """
        self.__set_cmd(
            "session.folder",
            folder
        )

    # MODIFIED FOR MULTI-CAMERA ACQUISITION.
    def set_image_name(self, name: str):
        """Set the filename template applied to captured images.

        Args:
            name: Filename template or prefix.
        """
        self.__set_cmd(
            "session.filenametemplate",
            name
        )

    def set_counter(self, counter: int = 0):
        """Set the digiCamControl image counter.

        Args:
            counter: Integer value assigned to the image counter.
                Defaults to 0.
        """
        self.__set_cmd(
            "session.Counter",
            str(counter)
        )

    # %% Transfer mode
    def set_transfer(self, location: str) -> int:
        """Configure where captured images are stored.

        Args:
            location: digiCamControl transfer mode, such as
                ``Save_to_camera_only``, ``Save_to_PC_only`` or
                ``Save:to_PC_and_camera``.

        Returns:
            int: Command status code.
        """
        print(
            f"Set the transfer to {location}."
        )
        return self.run_cmd(
            f"set transfer {location}"
        )

    # %% Autofocus
    def show_live_view(self) -> int:
        """Display the digiCamControl live-view window.

        Returns:
            int: Command status code.
        """
        print("Showing live view window.")
        return self.run_cmd(
            "do LiveViewWnd_Show"
        )

    def set_autofocus(self, status: bool = True):
        """Enable or disable autofocus for subsequent captures.

        Args:
            status: True to enable autofocus and False to disable it.
        """
        if status:
            self.capture_command = "Capture"
            print("Autofocus is on.\n")
        else:
            self.capture_command = "CaptureNoAf"
            print("Autofocus is off.\n")

    # %% Shutter speed
    def set_shutterspeed(
        self,
        shutter_speed: str
    ) -> int:
        """Set the camera shutter speed.

        Args:
            shutter_speed: Requested shutter speed, for example ``1/50``,
                ``1/250`` or ``1s``.

        Returns:
            int: Command status code.
        """
        return self.__set_cmd(
            "shutterspeed",
            shutter_speed
        )

    def get_shutterspeed(self):
        """Retrieve the current shutter speed.

        Returns:
            Union[int, str]: Current value or an error status.
        """
        return self.__get_cmd(
            "shutterspeed"
        )

    def list_shutterspeed(self):
        """List all shutter speeds supported by the selected camera.

        Returns:
            Union[int, List[str]]: Available values or an error status.
        """
        return self.__list_cmd(
            "shutterspeed"
        )

    # %% ISO
    def set_iso(self, iso: int = 100) -> int:
        """Set the camera ISO sensitivity.

        Args:
            iso: ISO value, for example 100, 200 or 400.

        Returns:
            int: Command status code.
        """
        return self.__set_cmd(
            "Iso",
            str(iso)
        )

    def get_iso(self):
        """Retrieve the current ISO value.

        Returns:
            Union[int, str]: Current ISO value or an error status.
        """
        return self.__get_cmd("Iso")

    def list_iso(self) -> list:
        """List all ISO values supported by the selected camera.

        Returns:
            list: Available ISO values.
        """
        return self.__list_cmd("Iso")

    # %% Aperture
    def set_aperture(
        self,
        aperture: float = 2.8
    ) -> int:
        """Set the camera aperture.

        Args:
            aperture: Requested aperture value, for example 2.8 or 8.0.

        Returns:
            int: Command status code.
        """
        return self.__set_cmd(
            "aperture",
            str(aperture)
        )

    def get_aperture(
        self
    ) -> Union[int, str]:
        """Retrieve the current aperture.

        Returns:
            Union[int, str]: Current aperture or an error status.
        """
        return self.__get_cmd(
            "aperture"
        )

    def list_aperture(self) -> list:
        """List all aperture values supported by the selected camera.

        Returns:
            list: Available aperture values.
        """
        return self.__list_cmd(
            "aperture"
        )

    # %% Exposure compensation
    def set_exposure_comp(
        self,
        ec: str = "0.0"
    ) -> int:
        """Set exposure compensation.

        Args:
            ec: Exposure-compensation value, for example ``-1.0`` or ``+2.3``.

        Returns:
            int: Command status code.
        """
        return self.__set_cmd(
            "exposurecompensation",
            ec
        )

    def get_exposure_comp(
        self
    ) -> Union[int, str]:
        """Retrieve the current exposure-compensation value.

        Returns:
            Union[int, str]: Current value or an error status.
        """
        return self.__get_cmd(
            "exposurecompensation"
        )

    def list_exposure_comp(self) -> list:
        """List all supported exposure-compensation values.

        Returns:
            list: Available exposure-compensation values.
        """
        return self.__list_cmd(
            "exposurecompensation"
        )

    # %% Compression
    def set_compression(
        self,
        comp: str = "RAW"
    ) -> int:
        """Set the camera image-compression format.

        Args:
            comp: Compression setting, such as ``RAW`` or ``JPEG (BASIC)``.

        Returns:
            int: Command status code.
        """
        return self.__set_cmd(
            "compressionsetting",
            comp
        )

    def get_compression(
        self
    ) -> Union[int, str]:
        """Retrieve the current compression setting.

        Returns:
            Union[int, str]: Current value or an error status.
        """
        return self.__get_cmd(
            "compressionsetting"
        )

    def list_compression(self) -> list:
        """List all image-compression settings supported by the camera.

        Returns:
            list: Available compression settings.
        """
        return self.__list_cmd(
            "compressionsetting"
        )

    # %% White balance
    def set_whitebalance(
        self,
        wb: str
    ) -> int:
        """Set the camera white-balance mode.

        Args:
            wb: White-balance setting, such as ``Auto``, ``Daylight`` or
                ``Cloudy``.

        Returns:
            int: Command status code.
        """
        return self.__set_cmd(
            "whitebalance",
            wb
        )

    def get_whitebalance(
        self
    ) -> Union[int, str]:
        """Retrieve the current white-balance setting.

        Returns:
            Union[int, str]: Current value or an error status.
        """
        return self.__get_cmd(
            "whitebalance"
        )

    def list_whitebalance(self) -> list:
        """List all white-balance modes supported by the camera.

        Returns:
            list: Available white-balance modes.
        """
        return self.__list_cmd(
            "whitebalance"
        )

    # %% Video
    def start_video(self) -> int:
        """Start video recording.

        Returns:
            int: Command status code.
        """
        self.show_live_view()  # Live view may be required.
        return self.run_cmd(
            "do StartRecord"
        )

    def stop_video(self) -> int:
        """Stop video recording.

        Returns:
            int: Command status code.
        """
        return self.run_cmd(
            "do StopRecord"
        )

    # %% Generic commands
    def run_cmd(self, cmd: str) -> int:
        """Execute a generic digiCamControl command.

        Args:
            cmd: Command passed to CameraControlRemoteCmd.exe.

        Returns:
            int: 0 when successful and -1 otherwise.
        """
        executable = os.path.join(
            self.exe_dir,
            "CameraControlRemoteCmd.exe"
        )

        if not os.path.exists(executable):
            print(
                f"Error: Executable not found at {executable}"
            )
            return -1

        try:
            r = subprocess.check_output(
                f'"{executable}" /c {cmd}',
                shell=True
            ).decode()

            if 'null' in r or r'""' in r:  # Successful response.
                return 0

            print(f"Error: {r}")

        except subprocess.CalledProcessError as e:
            print(
                f"Command failed with error: {e}"
            )

        except FileNotFoundError:
            print(
                f"Error: Executable not found at {executable}"
            )

        return -1

    def __set_cmd(
        self,
        cmd: str,
        value: str
    ) -> int:
        """Execute a digiCamControl ``set`` command.

        Args:
            cmd: Setting to modify.
            value: Value assigned to the setting.

        Returns:
            int: 0 when successful and -1 otherwise.
        """
        # Construct the complete executable path.
        executable = os.path.join(
            self.exe_dir,
            "CameraControlRemoteCmd.exe"
        )

        # Verify that the executable exists before running the command.
        if not os.path.exists(executable):
            print(
                f"Error: Executable not found at {executable}"
            )
            return -1

        try:
            # Execute the configuration command and decode its response.
            full_command = (
                f'"{executable}" /c set {cmd} {value}'
            )

            result = subprocess.check_output(
                full_command,
                shell=True
            ).decode()

            # A null response indicates successful execution.
            if 'null' in result:
                print(
                    f"Set the {cmd} to {value}."
                )
                return 0

            # Extract the digiCamControl error message when available.
            return_value = (
                result[109:]
                if len(result) > 109
                else result
            )

            print(
                f"Error: {return_value}"
            )
            return -1

        except subprocess.CalledProcessError as e:
            print(
                "Command failed with error code: "
                f"{e.returncode} "
                f"{e.output.decode() if e.output else 'No output'}"
            )
            return -1

        except Exception as e:
            print(
                f"Unexpected error: {e}"
            )
            return -1

    def __get_cmd(
        self,
        cmd: str
    ) -> Union[int, str]:
        """Execute a digiCamControl ``get`` command.

        Args:
            cmd: Camera parameter to retrieve.

        Returns:
            Union[int, str]: Retrieved value or -1 if the command fails.
        """
        r = subprocess.check_output(
            (
                f"cd {self.exe_dir} && "
                f"CameraControlRemoteCmd.exe /c get {cmd}"
            ),
            shell=True
        ).decode()

        if 'Unknown parameter get' in r:  # Error response.
            return_value = r[109:]
            print(
                f"Error: {return_value}"
            )
            return -1

        return_value = r[96:-6]

        print(
            f"Current {cmd}: {return_value}"
        )

        return return_value

    def __list_cmd(
        self,
        cmd: str
    ) -> Union[int, List[str]]:
        """Execute a digiCamControl ``list`` command.

        Args:
            cmd: Camera parameter whose supported values are requested.

        Returns:
            Union[int, List[str]]: List of available values, or -1 if the
                command fails.
        """
        r = subprocess.check_output(
            (
                f"cd {self.exe_dir} && "
                f"CameraControlRemoteCmd.exe /c list {cmd}"
            ),
            shell=True
        ).decode()

        if 'Unknown parameter list' in r:  # Error response.
            return_value = r[109:]
            print(
                f"Error: {return_value}"
            )
            return -1

        # Convert the digiCamControl response into a Python list.
        return_list = r[96:-6].split(",")

        # Remove quotation marks surrounding individual response values.
        return_list = [
            e[1:-1]
            for e in return_list
        ]

        print(
            f"List of all possible {cmd}s: {return_list}"
        )

        return return_list


# %% Unit tests
if __name__ == '__main__':
    # TODO: Extend test coverage to the complete module.

    print("Beginning unit tests:")

    camera = Camera()
    assert isinstance(camera, Camera)

    assert isinstance(
        camera.list_shutterspeed(),
        list
    )
    temp = camera.list_shutterspeed()[0]
    assert camera.set_shutterspeed(temp) == 0
    assert camera.get_shutterspeed() == temp

    assert isinstance(
        camera.list_iso(),
        list
    )
    temp = camera.list_iso()[0]
    assert camera.set_iso(temp) == 0
    assert camera.get_iso() == temp

    assert isinstance(
        camera.list_aperture(),
        list
    )
    temp = camera.list_aperture()[0]
    assert camera.set_aperture(temp) == 0
    assert camera.get_aperture() == temp

    assert isinstance(
        camera.list_exposure_comp(),
        list
    )
    temp = camera.list_exposure_comp()[0]
    assert camera.set_exposure_comp(temp) == 0
    assert camera.get_exposure_comp() == temp

    assert isinstance(
        camera.list_compression(),
        list
    )
    temp = camera.list_compression()[0]
    assert camera.set_compression(temp) == 0
    assert camera.get_compression() == temp

    assert isinstance(
        camera.list_whitebalance(),
        list
    )
    temp = camera.list_whitebalance()[0]
    assert camera.set_whitebalance(temp) == 0
    assert camera.get_whitebalance() == temp

    print("End unit tests.")