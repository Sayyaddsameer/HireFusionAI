import json
import pytest
from unittest.mock import patch, MagicMock
import video_resume_lambda_2_website_integrated as lambda2


@pytest.fixture
def sns_event():
    return {
        "Records": [
            {
                "Sns": {
                    "Message": json.dumps({
                        "JobId": "rekog-job-1",
                        "JobTag": "resume-123",
                        "Video": {"S3Bucket": "test-bucket", "S3ObjectName": "interview.mp4"}
                    })
                }
            }
        ]
    }


@patch("video_resume_lambda_2_website_integrated.comprehend")
@patch("video_resume_lambda_2_website_integrated.transcribe")
@patch("video_resume_lambda_2_website_integrated.rekognition")
@patch("video_resume_lambda_2_website_integrated.table")
def test_lambda2_handler_success(mock_table, mock_rekog, mock_transcribe, mock_comprehend, sns_event):
    # Mock Rekognition
    mock_rekog.get_face_detection.return_value = {
        "Faces": [
            {"Face": {"Emotions": [{"Type": "HAPPY", "Confidence": 90.0}], "Smile": {"Confidence": 85.0, "Value": True}}}
        ]
    }

    # Mock Transcribe job polling
    mock_transcribe.get_transcription_job.return_value = {
        "TranscriptionJob": {
            "TranscriptionJobStatus": "COMPLETED",
            "Transcript": {"TranscriptFileUri": "http://fake-transcript.com"}
        }
    }

    # Mock transcript download
    transcript_data = {
        "results": {"transcripts": [{"transcript": "I worked on a project internship certification"}]}
    }
    with patch("urllib.request.urlopen", MagicMock()) as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(transcript_data).encode()

        # Mock Comprehend
        mock_comprehend.detect_sentiment.return_value = {"Sentiment": "POSITIVE"}

        # Mock DynamoDB
        mock_table.put_item.return_value = {}

        response = lambda2.lambda_handler(sns_event, None)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["message"] == "Analysis saved"
        assert body["resume_id"] == "resume-123"
