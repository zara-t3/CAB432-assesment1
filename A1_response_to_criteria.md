Assignment 1 - REST API Project - Response to Criteria
================================================

Overview
------------------------------------------------

- **Name:** Zara Tyerman
- **Student number:** n115443098
- **Application name:** ImageLab
- **Two line description:** This app applies face detection and blurring to uploaded images using MTCNN neural networks. Users can upload images, trigger face blurring jobs, and download processed results through a web interface.

Core criteria
------------------------------------------------

### Containerise the app

- **ECR Repository name:** n11544309-a1-repo
- **Video timestamp:** 0:20
- **Relevant files:**
    - Dockerfile
    - requirements.txt
    - docker-compose.yml

### Deploy the container

- **EC2 instance ID:** ec2-n11544309-a1
- **Video timestamp:** 0:45

### User login

- **One line description:** Hard-coded admin/student users with JWT token authentication and role-based access control
- **Video timestamp:** 1:00
- **Relevant files:**
    - app/auth.py
    - app/templates/login.html

### REST API

- **One line description:** RESTful API with proper HTTP methods, JSON responses, and endpoints for authentication, images, and jobs
- **Video timestamp:** 2:30
- **Relevant files:**
    - app/main.py
    - app/routers/images.py
    - app/routers/jobs.py
    - app/auth.py

### Data types

- **One line description:** Application stores both unstructured image files and structured metadata/job records
- **Video timestamp:** 3:00
- **Relevant files:**
    - app/models/store.py
    - app/routers/images.py
    - app/services/processing.py

#### First kind

- **One line description:** Image files stored as binary data in filesystem (original, thumbnails, processed versions)
- **Type:** Unstructured
- **Rationale:** Binary image data too large and inappropriate for database storage. Application treats as opaque files.
- **Video timestamp:** 3:00
- **Relevant files:**
    - app/routers/images.py
    - app/services/processing.py
    - data/ directory structure

#### Second kind

- **One line description:** Image metadata, job records, and user ownership stored in Python dictionaries
- **Type:** Structured
- **Rationale:** Need to query for user images, job status, and processing parameters. Simple in-memory storage sufficient for demo.
- **Video timestamp:** 3:40
- **Relevant files:**
    - app/models/store.py
    - app/routers/images.py
    - app/routers/jobs.py

### CPU intensive task

- **One line description:** MTCNN face detection with multi-pass Gaussian blur and image format conversion
- **Video timestamp:** 2:00
- **Relevant files:**
    - app/services/processing.py

### CPU load testing

- **One line description:** Python script generating concurrent HTTP requests to trigger face processing jobs
- **Video timestamp:** 4:00
- **Relevant files:**
    - tools/load_test.py

Additional criteria
------------------------------------------------

### Extensive REST API features

- **One line description:** Pagination with limit/offset, multiple file versions (original/processed/thumb)
- **Video timestamp:** 1:50
- **Relevant files:**
    - app/routers/images.py
    - app/routers/jobs.py

### External API(s)

- **One line description:** Not attempted
- **Video timestamp:**
- **Relevant files:**
    - 

### Additional types of data

- **One line description:** JSON metadata files storing processing parameters and results alongside binary image data
- **Video timestamp:** 3:20
- **Relevant files:**
    - app/services/processing.py
    - app/routers/images.py

### Custom processing

- **One line description:** Custom face detection pipeline combining MTCNN with configurable multi-pass Gaussian blur and format optimization
- **Video timestamp:** 1:50
- **Relevant files:**
    - app/services/processing.py

### Infrastructure as code

- **One line description:** Not attempted
- **Video timestamp:**
- **Relevant files:**
    - 

### Web client

- **One line description:** Complete browser interface with image upload, job management, and file download capabilities
- **Video timestamp:** 1:00
- **Relevant files:**
    - app/templates/upload.html
    - app/templates/images.html
    - app/templates/jobs.html
    - app/static/css/mystyle.css
    - app/static/js/common.js

### Upon request

- **One line description:** Not attempted
- **Video timestamp:**
- **Relevant files:**
    -