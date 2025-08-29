import boto3
import os
import uuid
import urllib.parse
import json

rekognition = boto3.client('rekognition')
transcribe = boto3.client('transcribe')

SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']

def lambda_handler(event, context):
    try:
        # Get S3 object details from event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']  # e.g. hirefusion-interview-resumes
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])

        # Generate unique analysis_id (for website + DB mapping)
        analysis_id = str(uuid.uuid4())
        s3_uri = f"s3://{bucket}/{key}"

        # Start Face Detection (video analysis) → async
        rekognition.start_face_detection(
            Video={'S3Object': {'Bucket': bucket, 'Name': key}},
            NotificationChannel={
                'SNSTopicArn': SNS_TOPIC_ARN,
                'RoleArn': os.environ['REKOG_ROLE_ARN']
            },
            JobTag=analysis_id  # links Rekognition result back
        )

        # Extract file extension dynamically (mp4, mov, etc.)
        file_ext = key.split('.')[-1]

        # Start Transcribe Job (audio analysis) → async
        transcribe.start_transcription_job(
            TranscriptionJobName=analysis_id,  # links Transcribe result back
            Media={'MediaFileUri': s3_uri},
            MediaFormat=file_ext,
            LanguageCode='en-US'
        )

        # Website receives this response immediately
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Jobs started successfully',
                'analysisId': analysis_id,
                'file': key,
                'bucket': bucket
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
