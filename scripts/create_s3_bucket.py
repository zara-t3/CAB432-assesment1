import boto3
import sys
from botocore.exceptions import ClientError

def create_s3_bucket():
    
    STUDENT_NUMBER = "n11544309" 
    QUT_USERNAME = "n11544309@qut.edu.au"  
    
    bucket_name = f'{STUDENT_NUMBER}-imagelab-bucket'
    region = 'ap-southeast-2'
    
    print(f"Creating S3 bucket: {bucket_name}")
    
    s3_client = boto3.client('s3', region_name=region)
    
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} already exists")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            
            try:
                response = s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
                print(f"Created bucket: {bucket_name}")
                print(f"Location: {response.get('Location')}")
                
            except ClientError as create_error:
                print(f"Failed to create bucket: {create_error}")
                return False
        else:
            print(f"Error checking bucket: {e}")
            return False
 
    try:
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={
                'TagSet': [
                    {'Key': 'qut-username', 'Value': QUT_USERNAME},
                    {'Key': 'purpose', 'Value': 'assessment-2'}
                ]
            }
        )
        print("Added QUT tags to bucket")
        
    except ClientError as e:
        print(f"Failed to add tags: {e}")
        return False
    
    
    try:
      
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        print("Bucket access test: SUCCESS")
        
    except ClientError as e:
        print(f"Bucket access test failed: {e}")
        return False
    
    print(f"\nS3 bucket setup complete!")
    print(f"Bucket name: {bucket_name}")
    print(f"Region: {region}")
    print(f"QUT Username: {QUT_USERNAME}")
    
    return True

if __name__ == "__main__":
  
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"AWS account: {identity.get('Account')}")
    except Exception as e:
        print(f"AWS credentials error: {e}")
        sys.exit(1)
    
    create_s3_bucket()