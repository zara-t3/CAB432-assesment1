import boto3
import sys
from botocore.exceptions import ClientError

def create_tables():
    
    QUT_USERNAME = "n11544309@qut.edu.au"  
    STUDENT_NUMBER = "n11544309"  
    
   
    dynamodb = boto3.client('dynamodb', region_name='ap-southeast-2')
 
    images_table_name = f'{STUDENT_NUMBER}-imagelab-images'
    jobs_table_name = f'{STUDENT_NUMBER}-imagelab-jobs'
    
    print(f"Creating DynamoDB tables for {QUT_USERNAME}...")
    print(f"Tables: {images_table_name}, {jobs_table_name}")
  
    try:
        print(f"Creating {images_table_name}...")
        
        response = dynamodb.create_table(
            TableName=images_table_name,
            AttributeDefinitions=[
                {"AttributeName": "qut-username", "AttributeType": "S"},  
                {"AttributeName": "image_id", "AttributeType": "S"},      
            ],
            KeySchema=[
                {"AttributeName": "qut-username", "KeyType": "HASH"},   
                {"AttributeName": "image_id", "KeyType": "RANGE"},      
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1}  
        )
        
        print("Waiting for images table to be active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=images_table_name)
        print(f"Images table created: {images_table_name}")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"WARNING: Images table {images_table_name} already exists")
        else:
            print(f"ERROR: Error creating images table: {e}")
            return False
    
    try:
        print(f"Creating {jobs_table_name}...")
        
        response = dynamodb.create_table(
            TableName=jobs_table_name,
            AttributeDefinitions=[
                {"AttributeName": "qut-username", "AttributeType": "S"},  
                {"AttributeName": "job_id", "AttributeType": "S"},       
            ],
            KeySchema=[
                {"AttributeName": "qut-username", "KeyType": "HASH"},   
                {"AttributeName": "job_id", "KeyType": "RANGE"},        
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1}  
        )
        
        print("Waiting for jobs table to be active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=jobs_table_name)
        print(f"Jobs table created: {jobs_table_name}")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"WARNING: Jobs table {jobs_table_name} already exists")
        else:
            print(f"ERROR: Error creating jobs table: {e}")
            return False
    
 
    
    return True

if __name__ == "__main__":
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"AWS credentials found for account: {identity.get('Account')}")
    except Exception as e:
        print(f"ERROR: AWS credentials not found: {e}")
        print("Make sure you have AWS credentials configured")
        sys.exit(1)
    
    create_tables()