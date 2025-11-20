# tests/test_drive_utils_service_mode.py
import os
import json
from unittest.mock import MagicMock, patch
from video_pipeline.drive_utils import upload_folder_to_drive


def make_mock_service():
    """Create a fully mocked Google Drive service client."""
    mock_service = MagicMock()
    mock_files = MagicMock()
    mock_service.files.return_value = mock_files

    mock_upload_call = MagicMock()
    mock_upload_call.execute.return_value = {
        "id": "mock-upload-id",
        "name": "uploaded-file",
        "webViewLink": "http://drive.mock/file",
    }
    mock_files.create.return_value = mock_upload_call

    return mock_service


@patch("video_pipeline.drive_utils.service_account.Credentials.from_service_account_file")
@patch("video_pipeline.drive_utils.create_subfolder_under_parent")
@patch("video_pipeline.drive_utils.build")
def test_service_mode_upload(mock_build, mock_create_subfolder, mock_from_service_file):
    """Test the Google Drive upload function in SERVICE mode using mocks."""

    # Mock Drive API service
    mock_service = make_mock_service()
    mock_build.return_value = mock_service

    # Mock credentials load
    mock_from_service_file.return_value = MagicMock()

    # Mock folder creation sequence
    mock_create_subfolder.side_effect = [
        ("parent-session-folder", "http://drive.mock/session"),
        ("subA-id", None),
        ("subB-id", None),
        ("nested-id", None),
    ]

    # ---------------------------------------------------
    # CUSTOM LOCAL FOLDER PATH (persistent)
    # ---------------------------------------------------
    temp_dir = r"C:\ArkMalay\_Framework\Test_data"
    os.makedirs(temp_dir, exist_ok=True)

    # Clean folder contents before creating test files
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for f in files:
            os.remove(os.path.join(root, f))
        for d in dirs:
            os.rmdir(os.path.join(root, d))

    # Create sample files and folders
    with open(os.path.join(temp_dir, "file1.txt"), "w") as f:
        f.write("abc")

    with open(os.path.join(temp_dir, "config.json"), "w") as f:
        json.dump({"key": "value"}, f)

    with open(os.path.join(temp_dir, "video.mp4"), "wb") as f:
        f.write(b"\x00\x01")

    os.makedirs(os.path.join(temp_dir, "subA"), exist_ok=True)
    with open(os.path.join(temp_dir, "subA", "note.txt"), "w") as f:
        f.write("sub note")

    os.makedirs(os.path.join(temp_dir, "subB", "nested"), exist_ok=True)
    with open(os.path.join(temp_dir, "subB", "nested", "x.json"), "w") as f:
        json.dump({"x": 1}, f)

    # Patch Settings for service mode
    with patch("video_pipeline.drive_utils.Settings") as MockSettings:
        MockSettings.DRIVE_AUTH_MODE = "service"
        MockSettings.DRIVE_FOLDER_ID = "ROOT-PARENT-ID"
        MockSettings.SERVICE_ACCOUNT_PATH = "fake.json"

        result = upload_folder_to_drive(temp_dir, auth_mode="service")

    # Assertions
    mock_build.assert_called_once()
    assert mock_create_subfolder.call_count == 4
    assert result["status"] == "success"
    assert result["drive_folder_id"] == "parent-session-folder"
    assert result["uploaded_folder"] == os.path.basename(temp_dir)

    # Expect 5 uploaded files
    assert mock_service.files.return_value.create.call_count == 5

    uploaded_names = [
        call.kwargs["body"]["name"]
        for call in mock_service.files.return_value.create.call_args_list
    ]

    assert set(uploaded_names) == {
        "file1.txt",
        "config.json",
        "video.mp4",
        "note.txt",
        "x.json",
    }
