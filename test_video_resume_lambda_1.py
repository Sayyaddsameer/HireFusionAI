import json
import pytest
from unittest.mock import patch
import video_resume_lambda_1_website_integrated as lambda1


@pytest.fixture
def s3_event():
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "interview.mp4"}
                }
            }
        ]
    }


@patch("video_resume_lambda_1_website_integrated.rekognition")
@patch("video_resume_lambda_1_website_integrated.transcribe")
def test_lambda1_handler_success(mock_transcribe, mock_rekog, s3_event):
    # Mock Rekognition
    mock_rekog.start_face_detection.return_value = {"JobId": "rekog-job-1"}

    # Mock Transcribe
    mock_transcribe.start_transcription_job.return_value = {"TranscriptionJob": {"TranscriptionJobName": "job-1"}}

    response = lambda1.lambda_handler(s3_event, None)
    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert "analysisId" in body
    assert body["file"] == "interview.mp4"
    assert body["bucket"] == "test-bucket"
