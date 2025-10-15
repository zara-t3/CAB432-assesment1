Assignment 2 - Cloud Services Exercises - Response to Criteria
================================================

Instructions
------------------------------------------------
- Keep this file named A2_response_to_criteria.md, do not change the name
- Upload this file along with your code in the root directory of your project
- Upload this file in the current Markdown format (.md extension)
- Do not delete or rearrange sections.  If you did not attempt a criterion, leave it blank
- Text inside [ ] like [eg. S3 ] are examples and should be removed


Overview
------------------------------------------------

- **Name:** Zara Tyerman
- **Student number:** n11544309
- **Partner name (if applicable):** 
- **Application name:** ImageLab
- **Two line description:** Image processing application that allows users to upload images and apply face blur processing.
- **EC2 instance name or ID:** ID: i-08447d3f73d5ca8eb

------------------------------------------------

### Core - First data persistence service

- **AWS service name:** S3
- **What data is being stored?:** Image files (original uploads, processed images with face blur, thumbnails)
- **Why is this service suited to this data?:** S3 is designed for large binary files like images, provides high durability, and supports direct client uploads via pre-signed URLs
- **Why is are the other services used not suitable for this data?:** DynamoDB has item size limits which makes it unsuitable for large binary files, RDS is not optimised for blob storage, EBS/EFS would require server side processing for all uploads
- **Bucket/instance/table name:** n11544309-imagelab-bucket
- **Video timestamp:** 0:10
- **Relevant files:**
    - app/services/s3_service.py
    - app/routers/images.py

### Core - Second data persistence service

- **AWS service name:** DynamoDB
- **What data is being stored?:** Image metadata (name, owner, upload timestamps, S3 keys) and job processing records (job status, processing parameters, completion times)
- **Why is this service suited to this data?:** DynamoDB excels at fast key-value lookups for metadata, scales automatically, and handles the structured data with predictable access patterns
- **Why is are the other services used not suitable for this data?:** S3 is not queryable for metadata searches, RDS would be overkill for simple key value operations, EBS/EFS require application level data management
- **Bucket/instance/table name:** n11544309-imagelab-images, n11544309-imagelab-jobs
- **Video timestamp:** 1:10
- **Relevant files:**
    - app/services/dynamodb_service.py
    - app/routers/images.py
    - app/routers/jobs.py

### Third data service
- Not attempted

### S3 Pre-signed URLs

- **S3 Bucket names:** n11544309-imagelab-bucket
- **Video timestamp:** 1:50
- **Relevant files:**
    - app/services/s3_service.py 
    - app/routers/images.py 
    - app/templates/presigned_upload.html

### In-memory cache
- Not attempted

### Core - Statelessness

- **What data is stored within your application that is not stored in cloud data services?:** No persistent data is stored within the application. Temporary files are created during image processing but are immediately uploaded to S3 and then deleted.
- **Why is this data not considered persistent state?:** Temporary processing files are temporary and can be recreated from the original S3 images if needed. All persistent state like metadata and processed images are stored in cloud services.
- **How does your application ensure data consistency if the app suddenly stops?:** All database operations are atomic, S3 uploads are completed before DynamoDB records are created, and temporary files are cleaned up automatically by the OS if the application stops unexpectedly
- **Relevant files:**
    - app/services/s3_service.py
    - app/services/dynamodb_service.py
    - app/routers/jobs.py

### Graceful handling of persistent connections
- Not attempted

### Core - Authentication with Cognito

- **User pool name:** n11544309-a2-pool
- **How are authentication tokens handled by the client?:** JWT access tokens are stored in browser localStorage and sent as Bearer tokens in authorization headers for API requests
- **Video timestamp:** 2:30
- **Relevant files:**
    - app/auth.py
    - app/services/cognito_service.py
    - app/static/js/common.js
    - app/templates/login.html

### Cognito multi-factor authentication

- **What factors are used for authentication:** Password and email based one time code
- **Video timestamp:** 3:15
- **Relevant files:**
    - app/auth.py 
    - app/services/cognito_service.py 
    - app/templates/login.html

### Cognito federated identities

- **Identity providers used:** Google OAuth
- **Video timestamp:** 3:40
- **Relevant files:**
    - app/auth.py 
    - app/services/cognito_service.py 
    - app/templates/login.html 

### Cognito groups

- **How are groups used to set permissions?:** Users are assigned to 'user' or 'admin' groups. Admin users can view all images and jobs from all users, while regular users can only access their own content. 
- **Video timestamp:** 4:00
- **Relevant files:**
    - app/auth.py
    - app/services/cognito_service.py
    - app/routers/images.py
    - app/routers/jobs.py 

### Core - DNS with Route53

- **Subdomain:** n11544309.cab432.com
- **Video timestamp:** 4:50

### Parameter store

- **Parameter names:** /n11544309/imagelab/app-url, /n11544309/imagelab/s3-bucket-name, /n11544309/imagelab/dynamodb-images-table, /n11544309/imagelab/dynamodb-jobs-table, /n11544309/imagelab/cognito-client-id, /n11544309/imagelab/cognito-user-pool-id, /n11544309/imagelab/cognito-domain
- **Video timestamp:** 5:10
- **Relevant files:**
    - app/services/parameter_store_service.py
    - app/main.py
    - app/services/cognito_service.py
    - app/auth.py 

### Secrets manager

- **Secrets names:** n11544309-imagelab-secrets (contains: cognito_client_secret, jwt_secret)
- **Video timestamp:** 6:55
- **Relevant files:**
    - app/services/secrets_manager_service.py
    - app/services/cognito_service.py
    - app/main.py
    - app/auth.py

### Infrastructure as code
- Not attempted

### Other (with prior approval only)
- Not attempted

### Other (with prior permission only)
- Not attempted