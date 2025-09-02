import boto3
import json
import os
import urllib.request
import time
from datetime import datetime
from decimal import Decimal
import re

rekognition = boto3.client('rekognition')
transcribe = boto3.client('transcribe')
dynamodb = boto3.resource('dynamodb')
comprehend = boto3.client('comprehend')

TABLE_NAME = os.environ['DDB_TABLE']
table = dynamodb.Table(TABLE_NAME)

# Convert float/nested values into Decimal
def to_decimal(val):
    if isinstance(val, float):
        return Decimal(str(val))
    elif isinstance(val, dict):
        return {k: to_decimal(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [to_decimal(v) for v in val]
    elif isinstance(val, str):
        return val.strip() if val else None
    return val

def lambda_handler(event, context):
    print("[DEBUG] Incoming Event:", json.dumps(event))

    try:
        # Parse SNS message
        message = json.loads(event['Records'][0]['Sns']['Message'])
        print("[DEBUG] Parsed SNS Message:", json.dumps(message))

        # Use resume_id (JobTag) instead of random UUID
        resume_id = message['JobTag']    
        bucket = message['Video']['S3Bucket']
        key = message['Video']['S3ObjectName']

        # ---- 1. Rekognition Results ----
        print(f"[DEBUG] Getting Rekognition results for JobId={message['JobId']}")
        rekog_results = rekognition.get_face_detection(JobId=message['JobId'])
        face_detections = rekog_results.get('Faces', [])
        print(f"[DEBUG] Total Faces Detected: {len(face_detections)}")

        # Facial expression score (based on "HAPPY" emotion)
        happy_confidences = [
            e['Confidence'] for face_item in face_detections 
            for e in face_item['Face'].get('Emotions', []) if e['Type'] == 'HAPPY'
        ]
        facial_score = round(sum(happy_confidences) / len(happy_confidences), 2) if happy_confidences else 50.0

        # Gesture score (based on Smile)
        gesture_confidences = [
            face_item['Face']['Smile']['Confidence'] 
            for face_item in face_detections 
            if 'Smile' in face_item['Face'] and face_item['Face']['Smile'].get('Value', False)
        ]
        gesture_score = round(sum(gesture_confidences) / len(gesture_confidences), 2) if gesture_confidences else 50.0

        print(f"[DEBUG] Facial Score={facial_score}, Gesture Score={gesture_score}")

        # ---- 2. Wait for Transcribe ----
        print(f"[DEBUG] Waiting for Transcribe Job={resume_id}")
        status = None
        for _ in range(60):   # 60 attempts × 5s = 300s = 5 min
            transcribe_result = transcribe.get_transcription_job(TranscriptionJobName=resume_id)
            status = transcribe_result['TranscriptionJob']['TranscriptionJobStatus']
            print(f"[DEBUG] Transcribe Status={status}")
            if status == 'COMPLETED':
                break
            elif status == 'FAILED':
                raise Exception("Transcribe job failed")
            time.sleep(5)

        if status != 'COMPLETED':
            raise Exception("Transcribe job timed out")

        transcript_uri = transcribe_result['TranscriptionJob']['Transcript']['TranscriptFileUri']
        print(f"[DEBUG] Transcript URI={transcript_uri}")

        # ---- 3. Transcript Analysis ----
        with urllib.request.urlopen(transcript_uri) as response:
            transcript_data = json.loads(response.read().decode('utf-8'))

        transcript_text = transcript_data['results']['transcripts'][0]['transcript'] if transcript_data['results']['transcripts'] else ""
        print(f"[DEBUG] Transcript Extracted: {transcript_text[:100]}...")

        # Sentiment analysis
        sentiment = comprehend.detect_sentiment(Text=transcript_text or "neutral", LanguageCode='en')
        print(f"[DEBUG] Sentiment={sentiment['Sentiment']}")

        # Communication score
        communication_score = 90 if sentiment['Sentiment'] == "POSITIVE" else (75 if sentiment['Sentiment'] == "NEUTRAL" else 60)

        # Grammar score based on transcript length
        word_count = len(transcript_text.split())
        grammar_score = 50 if word_count < 30 else (70 if word_count < 100 else 90)

        # Content score based on richness (keywords + word count)
        keywords = ["experience", "project", "internship", "developed", "built", "designed", "certification"]
        keyword_hits = sum(transcript_text.lower().count(word) for word in keywords)
        content_score = min(100, (word_count / 2) + (keyword_hits * 5))

        # Dynamic projects, internship, certifications from transcript
        project_score = min(20, transcript_text.lower().count("project") * 5)
        internship_score = min(20, transcript_text.lower().count("internship") * 5)
        certifications_count = len(re.findall(r"certification|certificate", transcript_text.lower()))
        certification_score = min(20, certifications_count * 5)

        # Total Score
        total_score = round(
            (facial_score + gesture_score + grammar_score + content_score +
             communication_score + project_score + internship_score + certification_score) / 8, 2
        )

        final_score = {
            "facial_expressions": facial_score,
            "hand_gestures": gesture_score,
            "confidence_level": round((facial_score + gesture_score) / 2, 2),
            "communication_skills": communication_score,
            "grammar": grammar_score,
            "content": content_score,
            "projects": project_score,
            "internship": internship_score,
            "certifications": certification_score,
            "total_score": total_score
        }

        print("[DEBUG] Final Score Object:", final_score)

        # ---- 4. Save to DynamoDB ----
        item = {
            "ResumeID": resume_id,  #  Same as website metadata
            "Video": f"s3://{bucket}/{key}",
            "Timestamp": datetime.utcnow().isoformat(),
            "Scores": to_decimal(final_score),
            "Transcript": transcript_text,
            "Status": "COMPLETED",
            "TotalScore": Decimal(str(total_score))
        }

        print(f"[DEBUG] Item to be saved to DynamoDB: {json.dumps(item, default=str)}")
        table.put_item(Item=item)

        print(f"[SUCCESS] Analysis saved for {resume_id}")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Analysis saved', 'resume_id': resume_id})
        }

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
