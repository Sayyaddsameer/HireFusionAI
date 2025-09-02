from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import boto3
from datetime import datetime
import os
import uuid
from boto3.dynamodb.conditions import Key
import json

app = Flask(__name__, template_folder='templates')
CORS(app)

# Replace with your region and table name
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('HireFusionTable')
table_name ='ResumeAnalysisResults'  # Your second table


# S3 Configuration (Using IAM Role)
S3 = boto3.client("s3", region_name="us-east-1")
BUCKET = "hirefusionai-resumes"  # Replace with your actual bucket name

s3 = boto3.client('s3', region_name='us-east-1')
VIDEO_BUCKET = 'hirefusion-interview-videos'

def allowed_file(filename):
    ext = filename.rsplit(".", 1)[1].lower()
    return "." in filename and ext in {"pdf", "doc", "docx"}

def upload_to_s3(fileobj, filename, acl="public-read"):
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    S3.upload_fileobj(fileobj, BUCKET, unique_name,
                      ExtraArgs={"ACL": acl, "ContentType": fileobj.content_type})
    url = f"https://{BUCKET}.s3.amazonaws.com/{unique_name}"
    return url

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/ind")
def ind():
    auth_type = request.args.get("auth", "")
    return render_template("ind.html", auth=auth_type)

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    full_name = data.get("full_name")
    username = data.get("username")
    date_of_birth = data.get("date_of_birth")
    phone = data.get("phone")
    gender = data.get("gender")
    email = data.get("email")
    password = data.get("password")

    # Store all fields in DynamoDB
    table.put_item(Item={
        'email': email,  # primary key
        'full_name': full_name,
        'username': username,
        'date_of_birth': date_of_birth,
        'phone': phone,
        'gender': gender,
        'password': password,
        'created_at': datetime.utcnow().isoformat()
    })

    return jsonify({"message": "User registered successfully"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    response = table.get_item(Key={'email': email})
    user = response.get("Item")

    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.get("password") != password:
        return jsonify({"error": "Incorrect password"}), 401

    return jsonify({"message": "Login successful", "user": user})

@app.route("/dashboard.html")
def dashboard():
    return render_template("dashboard.html")

@app.route("/resume-analyzer.html")
def resume_analyzer():
    return render_template("resume-analyzer.html")

@app.route("/interview-grader.html")
def interview_grader():
    return render_template("interview-grader.html")

def allowed_file(filename):
    ext = filename.rsplit(".", 1)[1].lower()
    return "." in filename and ext in {"pdf", "doc", "docx"}

def upload_to_s3(fileobj, filename):
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    S3.upload_fileobj(fileobj, BUCKET, unique_name,
                      ExtraArgs={"ContentType": fileobj.content_type})
    url = f"https://{BUCKET}.s3.amazonaws.com/{unique_name}"
    return url
@app.route('/generate_presigned_url', methods=['POST'])
def generate_presigned_url():
    try:
        data = request.get_json()
        file_name = data.get('filename')
        file_type = data.get('filetype')

        if not file_name or not file_type:
            return jsonify({'error': 'Missing filename or filetype'}), 400

        resume_id = str(uuid.uuid4())  # ✅ generate only once
        unique_filename = f"{resume_id}_{file_name}"  # ✅ use resume_id in S3 filename
        presigned_url = s3.generate_presigned_url(
        ClientMethod='put_object',
         Params={
              'Bucket': BUCKET,
              'Key': unique_filename,
              'ContentType': file_type,
              'Metadata': {
              'resumeid': resume_id  # <-- this will be attached to the S3 object
              }
            },
           ExpiresIn=3600
        )
        return jsonify({
            'url': presigned_url,
            'key': unique_filename,
            'resume_id': resume_id  # ✅ send back to frontend
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/resume_data', methods=['GET'])
def get_resume_data():
    resume_id = request.args.get('resume_id')
    if not resume_id:
        return jsonify({'error': 'Missing resume_id'}), 400

    try:
        # Use the high-level resource interface for consistency
        analysis_table = dynamodb.Table(table_name)

        response = analysis_table.get_item(Key={'ResumeID': resume_id})
        item = response.get('Item')

        if not item:
            return jsonify({"error": "Resume not found"}), 404

        return jsonify({
            'ResumeID': item.get('ResumeID'),
            'CertificationsCount': int(item.get('CertificationsCount', 0)),
            'InternshipDetected': item.get('InternshipDetected', False),
            'InternshipType': item.get('InternshipType', 'Unknown'),
            'ProjectDetected': item.get('ProjectDetected', False),
            'ResumeFile': item.get('ResumeFile', ''),
            'Score': int(item.get('Score', 0)),
            'Skills': json.loads(item.get('Skills', '[]')) if 'Skills' in item else []
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
def upload_video_to_s3(file_obj, filename):
    s3.upload_fileobj(
        file_obj,
        VIDEO_BUCKET,
        f"videos/{filename}",
        ExtraArgs={
            "ContentType": file_obj.content_type
        }
    )
    return f"https://{VIDEO_BUCKET}.s3.amazonaws.com/videos/{filename}"


# ✅ Video Upload Endpoint
@app.route("/api/upload_video", methods=["POST"])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"error": "No video file uploaded"}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # Upload to S3
        unique_name = f"{uuid.uuid4().hex}_{file.filename}"
        s3.upload_fileobj(
            file,
            VIDEO_BUCKET,
            f"videos/{unique_name}",
            ExtraArgs={
                "ACL": "public-read",  # optional
                "ContentType": file.content_type
            }
        )
        video_url = f"https://{VIDEO_BUCKET}.s3.amazonaws.com/videos/{unique_name}"

        # ✅ Add structured response for Interview Grader frontend
        response_data = {
            "message": "Upload successful",
            "url": video_url,
            "resume_score": 43.69,  # mock data for now
            "skills": ["Git", "C++", "Java", "Go", "Linux", "Cloud Computing", "GitHub", "Python", "AWS", "SQL"],
            "transcript": "Hi, I'm Mukesh. I'm self-motivated engineering expert...",
            "scores": {
                "Certifications": 5,
                "Communication Skills": "75%",
                "Confidence Level": "50%",
                "Content": "74.5%",
                "Facial Expressions": "50%",
                "Grammar": "90%",
                "Hand Gestures": "50%",
                "Internship": "0%",
                "Projects": 5
            },
            "total_score": 43.69,
            "status": "COMPLETED",
            "timestamp": datetime.utcnow().isoformat()
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------
# Dashboard API Endpoints
# -------------------------

@app.route("/api/dashboard_stats", methods=["GET"])
def dashboard_stats():
    """
    Returns actual dashboard stats from DynamoDB.
    Assumes 'HireFusionTable' has resume and video records.
    """
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Missing email"}), 400

    try:
        # Query all items for this user
        response = table.query(
            KeyConditionExpression=Key('email').eq(email)
        )
        items = response.get("Items", [])

        # Separate resume and video records
        resume_items = [i for i in items if i.get("type") == "resume"]
        video_items = [i for i in items if i.get("type") == "video"]

        stats = {
            "resumeCount": len(resume_items),
            "resumeAvgScore": (
                sum(int(i.get("score", 0)) for i in resume_items) / len(resume_items)
                if resume_items else 0
            ),
            "videoCount": len(video_items),
            "videoAvgScore": (
                sum(int(i.get("score", 0)) for i in video_items) / len(video_items)
                if video_items else 0
            )
        }

        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/user_details", methods=["GET"])
def user_details():
    """
    Returns logged-in user details from DynamoDB.
    """
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Missing email"}), 400

    try:
        response = table.get_item(Key={'email': email})
        user = response.get("Item")
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "full_name": user.get("full_name"),
            "email": user.get("email"),
            "phone": user.get("phone"),
            "username": user.get("username"),
            "date_of_birth": user.get("date_of_birth"),
            "gender": user.get("gender")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
