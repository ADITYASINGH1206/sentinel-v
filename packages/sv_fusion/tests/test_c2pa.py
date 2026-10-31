from unittest.mock import MagicMock, patch
from sv_fusion.c2pa import inspect_c2pa


def test_inspect_c2pa_no_manifest(tmp_path):
    dummy_file = tmp_path / "plain.mp4"
    dummy_file.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00")
    
    result = inspect_c2pa(str(dummy_file))
    assert result["present"] is False
    assert result["ai_disclosed"] is False


def test_inspect_c2pa_nonexistent():
    result = inspect_c2pa("nonexistent_video.mp4")
    assert result["present"] is False
    assert result["ai_disclosed"] is False


def test_inspect_c2pa_with_ai_disclosure():
    mock_manifest = {
        "active_manifest": {
            "title": "AI Generated Artwork",
            "format": "video/mp4",
            "assertions": [
                {
                    "label": "c2pa.actions",
                    "data": {
                        "actions": [
                            {
                                "action": "c2pa.created",
                                "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia",
                            }
                        ]
                    },
                }
            ],
        }
    }

    mock_reader = MagicMock()
    mock_reader.json.return_value = '{"active_manifest": {"title": "AI Gen", "format": "video/mp4", "digitalSourceType": "trainedAlgorithmicMedia"}}'

    with patch("c2pa.Reader", return_value=mock_reader):
        res = inspect_c2pa("mock_ai_video.mp4")
        assert res["present"] is True
        assert res["ai_disclosed"] is True
        assert res["manifest_title"] == "AI Gen"


def test_inspect_c2pa_with_authentic_c2pa():
    mock_reader = MagicMock()
    mock_reader.json.return_value = '{"active_manifest": {"title": "Canon Camera Video", "format": "video/mp4", "digitalSourceType": "originalDigitalMediaCapture"}}'

    with patch("c2pa.Reader", return_value=mock_reader):
        res = inspect_c2pa("mock_camera_video.mp4")
        assert res["present"] is True
        assert res["ai_disclosed"] is False
        assert res["manifest_title"] == "Canon Camera Video"

