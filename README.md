# HireFusion AI - Detailed Project Documentation

## Overview

**HireFusion AI** is a cutting-edge AI-powered platform designed to automate the recruitment process by providing **Resume Analysis** and **Interview Grading** services. It utilizes various **AWS services** to process resumes and evaluate interview videos in an efficient, scalable, and accurate manner.

The platform enables recruiters to streamline their hiring process by:
1. Automatically analyzing resumes and extracting relevant skills.
2. Grading interview videos based on facial expressions, gestures, and sentiment analysis.

This document provides an overview of the project, setup instructions, and details about the technologies used.

---

## Key Features

### 1. **Resume Analyzer**
- **Functionality:**
  - Upload resumes in formats like **PDF**, **DOCX**, or **TXT**.
  - Extract text content using **Amazon Textract**.
  - Detect key skills from the resume using **Amazon Comprehend**.
  - Score the resume based on the detected skills.
  - Store results in **Amazon DynamoDB**.

### 2. **Interview Grader**
- **Functionality:**
  - Upload interview videos in formats like **MP4**, **MOV**, and **AVI**.
  - Analyze the video for **facial expressions** and **hand gestures** using **Amazon Rekognition**.
  - Transcribe speech in the video to text using **Amazon Transcribe**.
  - Perform **sentiment analysis** on the transcribed text using **Amazon Comprehend**.
  - Grade the interview based on facial analysis and sentiment analysis.
  - Store results in **Amazon DynamoDB**.

---

## AWS Architecture and Services Used

### 1. **AWS Lambda**
- **Purpose:** AWS Lambda functions are used to handle the backend logic for processing resume files and interview videos. Lambda functions are event-driven and get triggered by file uploads to **Amazon S3**.
  
- **Roles & Permissions:**
  - Lambda functions are assigned appropriate **IAM roles** to access resources like S3, Textract, Rekognition, Transcribe, Comprehend, and DynamoDB.
  - **Event Notification** in **S3** triggers the Lambda function when a new file is uploaded.

### 2. **Amazon S3**
- **Purpose:** S3 is used as the storage service for uploading resumes and interview videos. Once a file is uploaded, an event notification triggers the corresponding Lambda function to process the file.

### 3. **Amazon Textract**
- **Purpose:** Textract is used to extract text from **PDF**, **DOCX**, and **TXT** files (resumes). The extracted text is then processed by **Amazon Comprehend** to identify skills.

### 4. **Amazon Comprehend**
- **Purpose:** Comprehend is used for **Natural Language Processing (NLP)**. It analyzes the text extracted from resumes to identify entities, particularly **skills**. For interview videos, Comprehend analyzes the transcribed text to identify **sentiments**.

### 5. **Amazon Rekognition**
- **Purpose:** Rekognition is used to analyze **facial expressions** and **hand gestures** in interview videos. It provides data on the dominant emotion detected in the faces from the video frames.

### 6. **Amazon Transcribe**
- **Purpose:** Transcribe is used to convert **speech to text** for interview videos, allowing for sentiment analysis on the transcribed content.

### 7. **Amazon DynamoDB**
- **Purpose:** DynamoDB is a NoSQL database used to store the results of both **Resume Analysis** and **Interview Grading** processes. It stores the resume file name, score, skills, facial expressions, and sentiment analysis.

### 8. **API Gateway**
- **Purpose:** API Gateway is used to expose HTTP endpoints for the frontend to interact with the backend Lambda functions, allowing users to upload files, view scores, and more.

### 9. **AWS CloudWatch**
- **Purpose:** CloudWatch monitors the performance and health of Lambda functions, logging events, errors, and function executions for debugging and optimization.

---

## Services Used

- **AWS Lambda:** Compute service that runs backend code based on events (file uploads).
- **Amazon S3:** Object storage service for storing resumes and interview videos.
- **Amazon Textract:** Extracts text from resumes for analysis.
- **Amazon Comprehend:** Identifies key skills and analyzes sentiment from resume and interview texts.
- **Amazon Rekognition:** Detects facial expressions and gestures in interview videos.
- **Amazon Transcribe:** Converts audio in interview videos to text.
- **Amazon DynamoDB:** Stores analysis results (skills, scores, and sentiment).
- **API Gateway:** Exposes HTTP endpoints for user interactions.
- **AWS CloudWatch:** Monitors function performance and logs errors.

---

## Project Workflow

### 1. **Resume Analysis Workflow**
1. **File Upload:** The user uploads a resume (PDF, DOCX, or TXT) to the **Amazon S3** bucket.
2. **Trigger Lambda:** An S3 **event notification** triggers the **Resume Analysis Lambda** function.
3. **Text Extraction:** The Lambda function uses **Amazon Textract** to extract text from the resume.
4. **Skill Extraction:** **Amazon Comprehend** analyzes the text to extract relevant skills.
5. **Score Generation:** A score is generated based on the number of detected skills.
6. **Store Results:** The results, including the resume file name, score, and skills, are stored in **Amazon DynamoDB**.
7. **Return Results:** A response with the extracted skills and score is returned to the frontend for display.

### 2. **Interview Grading Workflow**
1. **File Upload:** The user uploads an interview video (MP4, MOV, AVI) to the **Amazon S3** bucket.
2. **Trigger Lambda:** An S3 **event notification** triggers the **Interview Grading Lambda** function.
3. **Facial Expression Analysis:** The Lambda function uses **Amazon Rekognition** to detect facial expressions and gestures from the video.
4. **Speech-to-Text:** **Amazon Transcribe** converts the speech in the video to text.
5. **Sentiment Analysis:** **Amazon Comprehend** analyzes the transcribed text for sentiment.
6. **Generate Score:** A score is generated based on facial analysis, gestures, and sentiment.
7. **Store Results:** The results, including the video file name, score, facial analysis, and sentiment, are stored in **Amazon DynamoDB**.
8. **Return Results:** A response with the analyzed results is returned to the frontend for display.

---

