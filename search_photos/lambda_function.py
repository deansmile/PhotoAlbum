import json
import boto3
import os
import requests
from requests.auth import HTTPBasicAuth

# Constants
ES_HOST = 'https://search-photos-yzbexdxz2zkp3n7zlwamb3v4tq.us-east-1.es.amazonaws.com'  # no trailing slash
ES_INDEX = 'photos'
S3_BUCKET = 'cc3-photos-diwei'
REGION = 'us-east-1'

# OpenSearch login
ES_USER = 'deansmile'
ES_PASS = 'Yy201023!'

def lambda_handler(event, context):
    print("EVENT --- {}".format(json.dumps(event)))

    lex = boto3.client('lex-runtime')
    headers = {"Content-Type": "application/json"}
    auth = HTTPBasicAuth(ES_USER, ES_PASS)

    query = event.get("queryStringParameters", {}).get("q", "")
    if not query:
        return {
            'statusCode': 400,
            'headers': {"Access-Control-Allow-Origin": "*"},
            'body': json.dumps([])
        }

    # Call Lex to disambiguate
    try:
        lex_response = lex.post_text(
            botName='PhotoAlbum',
            botAlias='photoalbum',
            userId='user123',  # can be random or session-based
            inputText=query
        )
    except Exception as e:
        print("LEX ERROR ---", str(e))
        return {
            'statusCode': 200,
            'headers': {"Access-Control-Allow-Origin": "*"},
            'body': json.dumps([])
        }

    print("LEX RESPONSE ---", json.dumps(lex_response))

    slots = lex_response.get('slots', {})

    img_list = []

    for slot_name, keyword in slots.items():
        if keyword:
            # Build OpenSearch query
            search_url = f"{ES_HOST}/{ES_INDEX}/_search"
            search_query = {
                "query": {
                    "match": {
                        "labels": keyword.lower()
                    }
                }
            }
            print("OpenSearch Query ---", json.dumps(search_query))

            # Send POST request to OpenSearch
            try:
                es_response = requests.post(search_url, auth=auth, headers=headers, json=search_query)
                search_results = es_response.json()
            except Exception as e:
                print("OpenSearch ERROR ---", str(e))
                continue

            print("OpenSearch Response ---", json.dumps(search_results))

            hits = search_results.get('hits', {}).get('hits', [])

            for photo in hits:
                source = photo['_source']
                objectKey = source['objectKey']
                img_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{objectKey}"
                img_list.append(img_url)

    # Return search results
    return {
        'statusCode': 200,
        'headers': {
            "Access-Control-Allow-Origin": "*",
            'Content-Type': 'application/json'
        },
        'body': json.dumps(img_list)  # Return [] if no results
    }
