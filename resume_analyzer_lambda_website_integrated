import json
import boto3
import time

# AWS Clients
s3 = boto3.client('s3')
textract = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ResumeAnalysisResults')

# Skills list
SKILL_KEYWORDS = [
    "AWS", "Azure", "GCP", "Google Cloud", "Cloud Computing", "Docker", "Kubernetes", "Terraform",
    "Ansible", "CI/CD", "Jenkins", "GitHub Actions", "CloudFormation", "Python", "Java", "JavaScript",
    "TypeScript", "C++", "C#", "Go", "Ruby", "PHP", "Swift", "React", "Angular", "Vue", "Next.js", "Nuxt.js",
    "Spring Boot", "Django", "Flask", "Express", "SQL", "MySQL", "PostgreSQL", "NoSQL", "MongoDB", "DynamoDB",
    "Redis", "Elasticsearch", "Machine Learning", "Deep Learning", "TensorFlow", "Keras", "PyTorch",
    "Scikit-learn", "Pandas", "NumPy", "Data Science", "NLP", "Computer Vision", "Git", "GitHub", "Bitbucket",
    "Linux", "Networking", "REST API", "GraphQL", "Microservices", "Agile", "Scrum"
]

def lambda_handler(event, context):
    try:
        # Get S3 file details
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        resume_file = event['Records'][0]['s3']['object']['key']
        print(f"Processing: {resume_file} from {bucket_name}")

        # ⬇ Retrieve resume_id from metadata
        head = s3.head_object(Bucket=bucket_name, Key=resume_file)
        resume_id = head['Metadata'].get('resumeid')
        if not resume_id:
            raise Exception(" resumeid metadata missing from S3 object.")

        # Extract text using Textract
        text = extract_text_from_pdf_s3(bucket_name, resume_file)
        skills = analyze_resume_text(text)
        score, proj, intern, intern_type, certs = generate_score(skills, text)

        # Store result with correct resume_id
        store_in_dynamodb(
            resume_id, resume_file, score, skills, proj, intern, intern_type, certs
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success', 'resume_id': resume_id})
        }

    except Exception as e:
        print(f"Lambda Error: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def extract_text_from_pdf_s3(bucket_name, key):
    try:
        response = textract.start_document_text_detection(
            DocumentLocation={'S3Object': {'Bucket': bucket_name, 'Name': key}}
        )
        job_id = response['JobId']

        # Wait for Textract to complete
        while True:
            result = textract.get_document_text_detection(JobId=job_id)
            if result['JobStatus'] in ['SUCCEEDED', 'FAILED']:
                break
            time.sleep(2)

        if result['JobStatus'] == 'FAILED':
            return ""

        text = ""
        while True:
            for block in result['Blocks']:
                if block['BlockType'] == 'LINE':
                    text += block['Text'] + '\n'

            if 'NextToken' in result:
                result = textract.get_document_text_detection(JobId=job_id, NextToken=result['NextToken'])
            else:
                break

        return text
    except Exception as e:
        print(f"Textract Error: {str(e)}")
        return ""

def analyze_resume_text(text):
    return list(set(skill for skill in SKILL_KEYWORDS if skill.lower() in text.lower()))

def generate_score(skills, text):
    text_lower = text.lower()
    project_flag = "project" in text_lower
    internship_flag = False
    internship_type = None

    if "internship" in text_lower:
        internship_flag = True
        internship_type = "internship"
    elif "industry experience" in text_lower:
        internship_flag = True
        internship_type = "industry experience"

    cert_count = text_lower.count("certificate") + text_lower.count("certification")

    score = 10 + len(skills) * 3
    if project_flag:
        score += 10
    if internship_flag:
        score += 10
    score += cert_count * 5

    return min(score, 100), project_flag, internship_flag, internship_type, cert_count

def store_in_dynamodb(resume_id, resume_file, score, skills, project_flag, internship_flag, internship_type, cert_count):
    table.put_item(
        Item={
            'ResumeID': resume_id,
            'ResumeFile': resume_file,
            'Score': score,
            'Skills': json.dumps(skills),
            'ProjectDetected': project_flag,
            'InternshipDetected': internship_flag,
            'InternshipType': internship_type or "None",
            'CertificationsCount': cert_count
        }
    )

