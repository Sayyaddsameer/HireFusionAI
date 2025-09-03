# test_resume_analyzer.py

import json
import pytest
from unittest.mock import patch

import resume_analyzer_lambda_website_integrated as analyzer


# ---- Sample Input Event ----
@pytest.fixture
def s3_event():
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "resume.pdf"}
                }
            }
        ]
    }


# ---- Test: lambda_handler end-to-end ----
@patch("resume_analyzer_lambda_website_integrated.s3")
@patch("resume_analyzer_lambda_website_integrated.textract")
@patch("resume_analyzer_lambda_website_integrated.table")
def test_lambda_handler_success(mock_table, mock_textract, mock_s3, s3_event):
    # Mock S3 metadata
    mock_s3.head_object.return_value = {"Metadata": {"resumeid": "123"}}

    # Mock Textract workflow
    mock_textract.start_document_text_detection.return_value = {"JobId": "job-1"}
    mock_textract.get_document_text_detection.side_effect = [
        {
            "JobStatus": "SUCCEEDED",
            "Blocks": [
                {"BlockType": "LINE", "Text": "AWS Project Internship Certificate"}
            ]
        }
    ]

    # Mock DynamoDB
    mock_table.put_item.return_value = {}

    response = analyzer.lambda_handler(s3_event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "Success"
    assert body["resume_id"] == "123"


# ---- Test: analyze_resume_text ----
def test_analyze_resume_text():
    text = "Experienced in AWS, Docker, and Python."
    skills = analyzer.analyze_resume_text(text)
    assert "AWS" in skills
    assert "Docker" in skills
    assert "Python" in skills


# ---- Test: generate_score ----
def test_generate_score():
    skills = ["AWS", "Python"]
    text = "This resume mentions project, internship and certification."
    score, proj, intern, intern_type, certs = analyzer.generate_score(skills, text)

    assert score <= 100
    assert proj is True
    assert intern is True
    assert certs >= 1
    assert intern_type in ("internship", "industry experience")


# ---- Test: store_in_dynamodb ----
@patch("resume_analyzer_lambda_website_integrated.table")
def test_store_in_dynamodb(mock_table):
    mock_table.put_item.return_value = {}

    analyzer.store_in_dynamodb(
        "123", "resume.pdf", 85, ["AWS", "Python"], True, True, "internship", 2
    )

    mock_table.put_item.assert_called_once()
    args, kwargs = mock_table.put_item.call_args
    assert kwargs["Item"]["ResumeID"] == "123"
    assert kwargs["Item"]["Score"] == 85
    assert json.loads(kwargs["Item"]["Skills"]) == ["AWS", "Python"]
