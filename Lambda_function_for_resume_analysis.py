import json
import boto3
import uuid
import time

# AWS Clients
s3 = boto3.client('s3')
textract = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ResumeAnalysisResults')

# Skills list
SKILL_KEYWORDS = [
    "AWS","Azure","GCP","Google Cloud","Cloud Computing","Docker","Kubernetes","Terraform",
    "Ansible","CI/CD","Jenkins","GitHub Actions","CloudFormation","Python","Java","JavaScript",
    "TypeScript","C++","C#","Go","Ruby","PHP","Swift","React","Angular","Vue","Next.js","Nuxt.js",
    "Spring Boot","Django","Flask","Express","SQL","MySQL","PostgreSQL","NoSQL","MongoDB","DynamoDB",
    "Redis","Elasticsearch","Machine Learning","Deep Learning","TensorFlow","Keras","PyTorch",
    "Scikit-learn","Pandas","NumPy","Data Science","NLP","Computer Vision","Git","GitHub","Bitbucket",
    "Linux","Networking","REST API","GraphQL","Microservices","Agile","Scrum"
]

def lambda_handler(event, context):
    try:
        # Get S3 bucket and file details
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        resume_file = event['Records'][0]['s3']['object']['key']
        print(f"Processing file: {resume_file} from bucket: {bucket_name}")

        # Extract text using Textract
        extracted_text = extract_text_from_pdf_s3(bucket_name, resume_file)

        if not extracted_text or len(extracted_text) < 200:
            print("Warning: Extracted text is too small. Resume may be image-based or poorly scanned.")

        # Analyze skills and score
        skills = analyze_resume_text(extracted_text)
        score, project_flag, internship_flag, internship_type, cert_count = generate_score(skills, extracted_text)

        # Store in DynamoDB
        store_in_dynamodb(resume_file, score, skills, project_flag, internship_flag, internship_type, cert_count)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'resume_file': resume_file,
                'score': score,
                'skills': skills,
                'project_detected': project_flag,
                'internship_detected': internship_flag,
                'internship_type': internship_type,
                'certifications_count': cert_count
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}


def extract_text_from_pdf_s3(bucket_name, resume_file):
    """Extract text from PDF in S3 using Textract"""
    try:
        response = textract.start_document_text_detection(
            DocumentLocation={'S3Object': {'Bucket': bucket_name, 'Name': resume_file}}
        )
        job_id = response['JobId']

        # Wait for completion
        while True:
            status = textract.get_document_text_detection(JobId=job_id)
            if status['JobStatus'] in ['SUCCEEDED', 'FAILED']:
                break
            time.sleep(2)

        if status['JobStatus'] == 'FAILED':
            return ""

        text = ""
        while True:
            for item in status['Blocks']:
                if item['BlockType'] == 'LINE':
                    text += item['Text'] + "\n"

            if 'NextToken' in status:
                status = textract.get_document_text_detection(JobId=job_id, NextToken=status['NextToken'])
            else:
                break

        return text

    except Exception as e:
        print(f"Textract Error: {str(e)}")
        return ""


def analyze_resume_text(text):
    """Extract skills from text"""
    return list(set(skill for skill in SKILL_KEYWORDS if skill.lower() in text.lower()))


def generate_score(skills, text):
    """Generate score based on skills, projects, internships, and certifications"""
    text_lower = text.lower()

    # Flags
    project_flag = "project" in text_lower
    internship_flag = False
    internship_type = None

    # Check for internship or industry experience
    if "internship" in text_lower:
        internship_flag = True
        internship_type = "internship"
    elif "industry experience" in text_lower:
        internship_flag = True
        internship_type = "industry experience"

    # Count certifications (each = 5 points)
    cert_count = text_lower.count("certificate") + text_lower.count("certification")

    # Base + skills
    score = 10 + (len(skills) * 3)

    # Add project & internship scores
    if project_flag:
        score += 10
    if internship_flag:
        score += 10

    # Add certifications scores (5 points per certification mention)
    score += (cert_count * 5)

    return min(score, 100), project_flag, internship_flag, internship_type, cert_count


def store_in_dynamodb(resume_file, score, skills, project_flag, internship_flag, internship_type, cert_count):
    """Store result in DynamoDB"""
    resume_id = str(uuid.uuid4())
    table.put_item(
        Item={
            'ResumeID': resume_id,
            'ResumeFile': resume_file,
            'Score': score,
            'Skills': json.dumps(skills),
            'ProjectDetected': project_flag,
            'InternshipDetected': internship_flag,
            'InternshipType': internship_type if internship_type else "None",
            'CertificationsCount': cert_count
        }
    )

