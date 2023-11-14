import boto3
import os
from datetime import datetime, time, timezone
import sys
import time

#### PURPOSE ####
# We want to move objects to cheaper storage class, if they aren't frequently used. 

#### REQUIREMENTS ####
# - Object that wasn't modified in the last [X] days
# - Object that wasn't accesed in the last [Y] days

#### FLOW ####
## 1 ##
# In the first step we want to detect which objects weren't modified for the last [X] days and add them 
# to the list, that contains items which should be moved to another storage class.
## 2 ##
# Here we use the athena query in order to retrieve all the objects, that were accesed in period of
# [Y] last days. This is the last requirement, that should be supplied. If the object was accesed, then we
# remove object from the list or skip this step, if object wasn't added. If the object didn't appear in
# in our query, we maintain our decision about moving.

output_queries = os.environ.get('OUTPUT_QUERIES')
log_bucket_name = os.environ.get('LOG_BUCKET_NAME')
key = os.environ.get('KEY')
value = os.environ.get('VALUE')
athena = boto3.client('athena')
s3 = boto3.client('s3')


def lambda_handler(event, context):
    
    ######## PART FOR MODIFIED TIME ########

    paginator = s3.get_paginator('list_objects_v2')

    not_modified = []

    # for page in paginator.paginate(Bucket=os.environ.get('BUCKET_NAME')):
    #     for obj in page.get('Contents', []):
    #         current_time_seconds = datetime.now().timestamp()
    #         last_modified_time = obj['LastModified'].timestamp()
    #         time_difference = (current_time_seconds - last_modified_time) / 86400

    #         if time_difference >= float(os.environ.get('MODIFY_DAYS')):
    #             not_modified.append(obj['Key'])
    current_time_seconds = datetime.now().timestamp()
    filtered_iterator = paginator.paginate(Bucket=os.environ.get('BUCKET_NAME'), MaxKeys=10).search("Contents[?StorageClass != 'STANDARD_IA'][]") #filter the storage class from the start.
    for obj in filtered_iterator:
        # tagging = s3.get_object_tagging(Bucket=os.environ.get('BUCKET_NAME'), Key=obj['Key'])
        # tags = {tag['Key']: tag['Value'] for tag in tagging.get('TagSet', [])}
        # # Check if object is tagged with demo=demo
        # if tags.get('demo') == 'demo':
        #     continue  # Skip this file as it's already tagged with demo=demo
        print(f"Processing object: {obj['Key']} with StorageClass: {obj.get('StorageClass', 'N/A')}")
        last_modified_time = obj['LastModified'].timestamp()
        time_difference = (current_time_seconds - last_modified_time) / 86400

        if time_difference >= float(os.environ.get('MODIFY_DAYS')):
            not_modified.append(obj['Key'])
    #########################################


    ######## PART FOR ACCESSED TIME ########
    
    #Computing and converting time in order to incorporate it to our query !!!!NOTE --> CHANGE ACCESS TIME TO ENV!!!!!
    current_datetime = datetime.fromtimestamp(current_time_seconds).strftime("%Y-%m-%d %H:%M:%S").replace(" ", ":")
    last_possible_datetime = datetime.fromtimestamp(current_time_seconds - float(os.environ.get('ACCESS_DAYS')) * 86400).strftime("%Y-%m-%d %H:%M:%S").replace(" ", ":")
    database = os.environ.get('DATABASE_NAME')
    table = os.environ.get('TABLE_NAME')
    query = f'''SELECT DISTINCT(key)
FROM "{table}"
WHERE parse_datetime(RequestDateTime,'dd/MMM/yyyy:HH:mm:ss Z')
BETWEEN parse_datetime('{last_possible_datetime}','yyyy-MM-dd:HH:mm:ss')
AND
parse_datetime('{current_datetime}','yyyy-MM-dd:HH:mm:ss')'''
    print(f'{query=}')
                                                                                                                                                                      
    output   = f's3://{log_bucket_name}'
    path     = output_queries

    execute_query = athena.start_query_execution(
         QueryString = query,
         QueryExecutionContext = {
             'Database': database
         },
         ResultConfiguration = {
             'OutputLocation': "{}/{}".format(output, path),
         }
     )
    
    #Check the status of our query
    def check_status(get_data):                                                                                                                                                                                                                                                                             
        status = get_data['QueryExecution']['Status']['State']                                                                                                                                                                                                                                             
        return status
    # Here's resiliency mechanism (Exponential Backoff).
    executed = False
    retry = 0
    waiting_time = 1
    while not executed:
        metadata = athena.get_query_execution(QueryExecutionId=execute_query['QueryExecutionId'])
        status = check_status(metadata)
        if status == 'SUCCEEDED':
            executed = True
        elif retry == 5:
            sys.exit("Retrieving data didn't succeed")
        else:
            retry += 1
            time.sleep(waiting_time)
            waiting_time *= 2

    # Get the results from database
    results = athena.get_query_results(QueryExecutionId=execute_query['QueryExecutionId'])
    #Extract names of the objects, that were accessed and remove them from the list if they're present
    for dict in results['ResultSet']['Rows'][1:]:
        key_name = dict['Data'][0]['VarCharValue']
        try:
            not_modified.remove(key_name)
        except ValueError:
            continue

    #sys.exit(print(not_modified))
    # for name in not_modified:
    #     s3.put_object_tagging(
    #                     Bucket=os.environ.get('BUCKET_NAME'),
    #                     Key=name,
    #                     Tagging={
    #                         'TagSet': [
    #                             {
    #                                 'Key': key,
    #                                 'Value': value
    #                             },
    #                         ]
    #                     }
    #                 )  
    for name in not_modified:
        try:
            # Attempt to tag the object
            response = s3.put_object_tagging(
                Bucket=os.environ.get('BUCKET_NAME'),
                Key=name,
                Tagging={
                    'TagSet': [
                        {
                            'Key': key,
                            'Value': value
                        },
                    ]
                }
            )
            print(f"Tagging successful for {name}: {response}")
        except Exception as e:
            # If there's an error, print it out.
            print(f"Error tagging {name}: {e}")
        