#!/usr/bin/env python3
"""
Script to create SQS queues with Dead Letter Queue configuration
"""

import boto3
import json
import sys
from botocore.exceptions import ClientError

# Constants
REGION = 'ap-southeast-2'
STUDENT_NUMBER = 'n11544309'
DLQ_NAME = f'{STUDENT_NUMBER}-imagelab-jobs-dlq'
MAIN_QUEUE_NAME = f'{STUDENT_NUMBER}-imagelab-jobs'
PARAMETER_STORE_PATH = f'/{STUDENT_NUMBER}/imagelab/sqs-queue-url'

# Queue configuration
VISIBILITY_TIMEOUT = 300  # 5 minutes in seconds
MESSAGE_RETENTION = 345600  # 4 days in seconds
MAX_RECEIVE_COUNT = 3  # Number of receives before sending to DLQ


def create_dlq(sqs_client):
    """Create Dead Letter Queue"""
    print(f"\nCreating Dead Letter Queue: {DLQ_NAME}")

    try:
        response = sqs_client.create_queue(
            QueueName=DLQ_NAME,
            Attributes={
                'MessageRetentionPeriod': str(MESSAGE_RETENTION),
            },
            tags={
                'qut-username': 'n11544309@qut.edu.au'
            }
        )

        dlq_url = response['QueueUrl']
        print(f"✓ DLQ created successfully: {dlq_url}")

        # Get DLQ ARN
        dlq_attributes = sqs_client.get_queue_attributes(
            QueueUrl=dlq_url,
            AttributeNames=['QueueArn']
        )
        dlq_arn = dlq_attributes['Attributes']['QueueArn']
        print(f"✓ DLQ ARN: {dlq_arn}")
        print(f"✓ Tagged with qut-username: n11544309@qut.edu.au")

        return dlq_url, dlq_arn

    except ClientError as e:
        if e.response['Error']['Code'] == 'QueueAlreadyExists':
            print(f"⚠ DLQ already exists, retrieving URL...")
            dlq_url = sqs_client.get_queue_url(QueueName=DLQ_NAME)['QueueUrl']
            dlq_attributes = sqs_client.get_queue_attributes(
                QueueUrl=dlq_url,
                AttributeNames=['QueueArn']
            )
            dlq_arn = dlq_attributes['Attributes']['QueueArn']
            print(f"✓ DLQ URL: {dlq_url}")
            print(f"✓ DLQ ARN: {dlq_arn}")

            # Add tags to existing queue
            try:
                sqs_client.tag_queue(
                    QueueUrl=dlq_url,
                    Tags={'qut-username': 'n11544309@qut.edu.au'}
                )
                print(f"✓ Tagged with qut-username: n11544309@qut.edu.au")
            except Exception as tag_error:
                print(f"⚠ Warning: Could not add tags: {tag_error}")

            return dlq_url, dlq_arn
        else:
            print(f"✗ Error creating DLQ: {e}")
            raise


def create_main_queue(sqs_client, dlq_arn):
    """Create main queue with DLQ configuration"""
    print(f"\nCreating main queue: {MAIN_QUEUE_NAME}")

    # Configure redrive policy
    redrive_policy = {
        'deadLetterTargetArn': dlq_arn,
        'maxReceiveCount': str(MAX_RECEIVE_COUNT)
    }

    try:
        response = sqs_client.create_queue(
            QueueName=MAIN_QUEUE_NAME,
            Attributes={
                'VisibilityTimeout': str(VISIBILITY_TIMEOUT),
                'MessageRetentionPeriod': str(MESSAGE_RETENTION),
                'RedrivePolicy': json.dumps(redrive_policy)
            },
            tags={
                'qut-username': 'n11544309@qut.edu.au'
            }
        )

        queue_url = response['QueueUrl']
        print(f"✓ Main queue created successfully: {queue_url}")
        print(f"✓ Visibility timeout: {VISIBILITY_TIMEOUT} seconds (5 minutes)")
        print(f"✓ Message retention: {MESSAGE_RETENTION} seconds (4 days)")
        print(f"✓ Max receive count: {MAX_RECEIVE_COUNT}")
        print(f"✓ Tagged with qut-username: n11544309@qut.edu.au")

        return queue_url

    except ClientError as e:
        if e.response['Error']['Code'] == 'QueueAlreadyExists':
            print(f"⚠ Main queue already exists, retrieving URL...")
            queue_url = sqs_client.get_queue_url(QueueName=MAIN_QUEUE_NAME)['QueueUrl']
            print(f"✓ Main queue URL: {queue_url}")

            # Update queue attributes to ensure configuration is correct
            print("✓ Updating queue attributes...")
            sqs_client.set_queue_attributes(
                QueueUrl=queue_url,
                Attributes={
                    'VisibilityTimeout': str(VISIBILITY_TIMEOUT),
                    'MessageRetentionPeriod': str(MESSAGE_RETENTION),
                    'RedrivePolicy': json.dumps(redrive_policy)
                }
            )
            print("✓ Queue attributes updated")

            # Add tags to existing queue
            try:
                sqs_client.tag_queue(
                    QueueUrl=queue_url,
                    Tags={'qut-username': 'n11544309@qut.edu.au'}
                )
                print(f"✓ Tagged with qut-username: n11544309@qut.edu.au")
            except Exception as tag_error:
                print(f"⚠ Warning: Could not add tags: {tag_error}")

            return queue_url
        else:
            print(f"✗ Error creating main queue: {e}")
            raise


def store_in_parameter_store(ssm_client, queue_url):
    """Store queue URL in AWS Systems Manager Parameter Store"""
    print(f"\nStoring queue URL in Parameter Store: {PARAMETER_STORE_PATH}")

    try:
        ssm_client.put_parameter(
            Name=PARAMETER_STORE_PATH,
            Description=f'SQS Queue URL for ImageLab job processing',
            Value=queue_url,
            Type='String',
            Overwrite=True
        )
        print(f"✓ Queue URL stored in Parameter Store")

    except ClientError as e:
        print(f"✗ Error storing in Parameter Store: {e}")
        raise


def main():
    """Main function to create SQS queues"""
    print("=" * 80)
    print("SQS Queue Setup Script")
    print("=" * 80)

    try:
        # Initialize boto3 clients
        sqs_client = boto3.client('sqs', region_name=REGION)
        ssm_client = boto3.client('ssm', region_name=REGION)

        # Create DLQ
        dlq_url, dlq_arn = create_dlq(sqs_client)

        # Create main queue
        queue_url = create_main_queue(sqs_client, dlq_arn)

        # Store queue URL in Parameter Store
        store_in_parameter_store(ssm_client, queue_url)

        # Print summary
        print("\n" + "=" * 80)
        print("Setup Complete!")
        print("=" * 80)
        print(f"\nDead Letter Queue URL:")
        print(f"  {dlq_url}")
        print(f"\nMain Queue URL:")
        print(f"  {queue_url}")
        print(f"\nParameter Store Path:")
        print(f"  {PARAMETER_STORE_PATH}")
        print("\n" + "=" * 80)

        return 0

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
