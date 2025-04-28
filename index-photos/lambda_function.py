import json
import boto3
import os
import uuid
import requests  # Now from PyPI 'requests', not botocore.vendored.requests
from datetime import datetime
from requests.auth import HTTPBasicAuth

# Your OpenSearch endpoint (no trailing slash)
ES_HOST = 'https://search-photos-yzbexdxz2zkp3n7zlwamb3v4tq.us-east-1.es.amazonaws.com'
ES_INDEX = 'photos'
REGION = 'us-east-1'

# Fine-grained authentication user
ES_USER = 'deansmile'
ES_PASS = 'Yy201023!'

def get_es_url(index):
    return f"{ES_HOST}/{index}/_doc"

def lambda_handler(event, context):
    print("EVENT --- {}".format(json.dumps(event)))
    
    s3 = boto3.client('s3')
    rekognition = boto3.client('rekognition')

    headers = {"Content-Type": "application/json"}
    auth = HTTPBasicAuth(ES_USER, ES_PASS)

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        print(f"Processing s3://{bucket}/{key}")

        # Rekognition - Detect labels
        rekog_response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=10
        )

        detected_labels = [label['Name'] for label in rekog_response['Labels']]
        print("Detected labels:", detected_labels)

        # S3 - Retrieve custom labels from metadata
        try:
            head_object = s3.head_object(Bucket=bucket, Key=key)
            metadata = head_object.get('Metadata', {})
            custom_labels_str = metadata.get('customlabels', '')  # Note: S3 converts all metadata keys to lowercase
            if custom_labels_str:
                custom_labels = [label.strip() for label in custom_labels_str.split(',')]
                print("Custom labels from metadata:", custom_labels)
            else:
                custom_labels = []
        except Exception as e:
            print(f"Failed to retrieve custom labels: {e}")
            custom_labels = []

        # Combine Rekognition labels + Custom labels
        all_labels = list(set(detected_labels + custom_labels))  # Remove duplicates

        # Prepare JSON object
        photo_doc = {
            'objectKey': key,
            'bucket': bucket,
            'createdTimestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'labels': all_labels
        }

        print("Document to index:", photo_doc)

        # Send to OpenSearch
        url = get_es_url(ES_INDEX)
        response = requests.post(url, auth=auth, headers=headers, json=photo_doc)

        print("Elasticsearch response:", response.status_code, response.text)

    return {
        'statusCode': 200,
        'body': json.dumps('Image indexed successfully!')
    }