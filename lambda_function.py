import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import json
from urllib.parse import unquote
import inflection

def singularize_and_lowercase_labels(label_list):
    # Singularize and lowercase each label using inflection
    singularized_lowercased_labels = [inflection.singularize(label).lower() for label in label_list]

    return singularized_lowercased_labels

REGION = 'us-east-1'
HOST = 'search-photos-oimkc7iqvpnts6h36bvzeigpni.us-east-1.es.amazonaws.com'
INDEX = 'photos'

# Define the client to interact with Lex
client = boto3.client('lexv2-runtime')

def lambda_handler(event, context):
    print(event)
    print(context)
    msg_from_user = event['pathParameters']["prompt"]
    msg_from_user = unquote(msg_from_user)


    first = None
    second = None

    # change this to the message that user submits on 
    # your website using the 'event' variable

    print(f"Message from frontend: {msg_from_user}")

    # Initiate conversation with Lex
    response = client.recognize_text(
            botId='XWLCEMAUOE', # MODIFY HERE
            botAliasId='3ZVV1BNA0R', # MODIFY HERE
            localeId='en_US',
            sessionId='testuser',
            text=msg_from_user)
            
    print(f"{response['sessionState']['intent']['slots']['second'] =}")

    if response['sessionState']['intent']['slots']['second'] != None:
        second = response['sessionState']['intent']['slots']['second']['value']['resolvedValues'][0]
    if response['sessionState']['intent']['slots']['first'] != None:
        first = response['sessionState']['intent']['slots']['first']['value']['resolvedValues'][0]
    print(f"{response =}")

    print(f"{first =}")
    print(f"{second =}")
    
    label = []
    if first:
        label.append(first)
    if second:
        label.append(second)
        
    label = singularize_and_lowercase_labels(label)
    print(f"{label =}")
    
    
    opensearch_client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
                        http_auth=get_awsauth(REGION, 'es'),
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection)
    

    q = {
        'size': 5,
        'query': {
            'terms': {
                'labels': label  # Replace 'label_field_name' with the actual field name in your index
            }
        }
    }
    res = opensearch_client.search(index=INDEX, body=q)
    print(f"{res =}")

    hits = res['hits']['hits']
    results = []
    for i,hit in enumerate(hits):
        results.append(hit['_id'])

    print(f"{results =}")
    
    s3 = boto3.client("s3")
    bucket_name = "b2-store-photos"
    response = []
    for r in results:
        
        response.append(s3.generate_presigned_url('get_object',
                                                        Params={'Bucket': bucket_name,
                                                                'Key': r},
                                                        ExpiresIn=600))
                                                        
    print(f"{response =}")

    return {
        'statusCode': 200,
        'body': json.dumps({"url":response})
    }


def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)
    