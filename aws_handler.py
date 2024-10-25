import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from boto3.dynamodb.conditions import Attr
import os

class AWSHandler:
    def __init__(self, session_name):
        self.session_name = session_name
        self.s3_client, self.s3_resource = self._create_bot3_session()

        # XRLAB AWS DB Info
        if self.session_name == 'session_a':
            ########### ACCESS KEYS HERE | DO NOT MODIFY #############
            self.db_access_key = ""
            self.db_secret_key = ""
            self.dynamodb = boto3.resource('dynamodb')
            self.available_id_table = 'available_ids'
            self.user_data_table = 'user_data'
            ##########################################################

        # Empatica AWS Bucket Info
        # if self.session_name == 'session_b':
        #     ########### ACCESS KEYS HERE | DO NOT MODIFY #############
        #     self.BUCKET_NAME = ""
        #     self.PREFIX = ""
        #     self.TEMP_DIR = "/tmp"
        #     self.emp_access_key = ''
        #     self.emp_secret_key = ''
        #     ##########################################################

    def _create_bot3_session(self):
        if self.session_name == 'session_a':
            # TODO: Change the access key and secret key to the correct ones
            # XRLAB AWS
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID_A')
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            region = 'us-west-1'

        elif self.session_name == 'session_b':
            # Empatica AWS
            aws_access_key_id = os.getenv(self.emp_access_key)
            aws_secret_access_key = os.getenv(self.emp_secret_key)
            region = 'us-east-1'

        else:
            raise ValueError('Unknown session name {self.session_name}')
        
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name='us-east-1'
        )

        return session.client('s3'), session.resource('s3')

    def _ensure_session_a(self):
        if self.session_name != 'session_a':
            raise PermissionError("This method is only accessible when uploading user test data to XRLAB's AWS")
            
    def _ensure_session_b(self):
        if self.session_name != 'session_b':
            raise PermissionError("This method is only accessible when retrieving data from Empatica's AWS")
            
    # def get_empatica_csv(self):
    #     self._ensure_session_b()

    #     response = self.s3_client.list_objects_v2(self.BUCKET_NAME, self.PREFIX)

    #     if 'Contents' not in response:
    #         print('No files found in the bucket')
    #         return None
        
    #     csv_files = [obj for obj in response['Contents'] if obj['Key'].endswith('.csv')]
    #     if not csv_files:
    #         print('No CSV files found in the bucket')
    #         return None
        
    #     # TODO: Replace this line with code retrieving data by user session number
    #     most_recent_file = max(csv_files, key=lambda x: x['LastModified'])

    #     return most_recent_file['Key']

    def download_and_save(self, file_key):
        self._ensure_session_b()

        temp_file_path = os.path.join(self.TEMP_DIR, 'temp.csv')
        os.makedirs(self.TEMP_DIR, exist_ok=True)

        with open(temp_file_path, 'wb') as f:
            self.s3_client.download_fileobj(self.BUCKET_NAME, file_key, f)   
        
        return temp_file_path
    
    def upload_user_data(self, user_data):
        self._ensure_session_a()

        try:
            table = self.dynamodb.Table(self.user_data_table)
            response = table.put_item(Item=user_data)
            return response
        
        except (NoCredentialsError, PartialCredentialsError) as e:
            print(f"Error uploading user data to DynamoDB: {str(e)}")
            return None
        
    # This function will query a list of available ids stored on the xrlab server
def assign_available_id(self):
    self._ensure_session_a()
    table = self.dynamodb.Table(self.available_id_table)

    try:
        response = table.scan(
            FilterExpression=Attr('availability_status').eq('available')
        )

        if not response['Items']:
            raise Exception('No available IDs found.')
        
        available_id = response['Items'][0]['user_id']

        table.update_item(
            Key={'user_id': available_id},
            UpdateExpression='SET availability_status = :unavailable',
            ExpressionAttributeValues={':unavailable': 'unavailable'}
        )

        return available_id
    
    except ClientError as e:
        print(f"Client error: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"Error assigning available ID: {str(e)}")
        return None