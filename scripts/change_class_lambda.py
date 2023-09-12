import boto3
import os
import urllib.parse

# bucket_name = os.environ['BUCKET_NAME']
s3 = boto3.client('s3')

def object_has_tag(bucket, key, tag_key, tag_value):
    """Check if the object has the specified tag key and value."""
    response = s3.get_object_tagging(Bucket=bucket, Key=key)
    for tag in response.get('TagSet', []):
        if tag['Key'] == tag_key and tag['Value'] == tag_value:
            return True
    return False

def lambda_handler(event, context):
    # The lambda is triggerd when an object is tagged with isOld: true
    # The lambda will change the object's class to ${ChosenClass}
    # Get the bucket name and the key from the event source
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    response = s3.head_object(Bucket=bucket, Key=key)
    object_size = response['ContentLength']

    desired_tag_key = os.environ.get('KEY')
    desired_tag_value = os.environ.get('VALUE')
    # Check if the object has the desired tag
    if not object_has_tag(bucket, key, desired_tag_key, desired_tag_value):
        return {
            'statusCode': 200,
            'body': f'Object {key} in bucket {bucket} does not have the tag isold:true. No action taken.'
        }

    # Only apply the storage class change if the object is less than 128kb
    if object_size >= 128 * 1024:
        return {
            'statusCode': 200,
            'body': f'Object {key} in bucket {bucket} is greater than or equal to 128kb. No action taken.'
        }

    # The desired storage class
    storage_class = os.environ.get('TARGET_STORAGE_CLASS', 'STANDARD_IA')  # Default to STANDARD_IA if not set

    # Change the storage class of the S3 object
    s3.copy_object(Bucket=bucket, CopySource={'Bucket': bucket, 'Key': key}, Key=key, StorageClass=storage_class)

    return {
        'statusCode': 200,
        'body': f'Object {key} in bucket {bucket} changed to storage class {storage_class}'
    }
