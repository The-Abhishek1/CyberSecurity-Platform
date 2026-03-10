from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError


class AWSIntegration:
    """
    AWS Cloud Integration
    
    Features:
    - EC2 instance scanning
    - S3 bucket auditing
    - IAM policy analysis
    - Security group review
    - CloudTrail integration
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.session = None
        self._init_session()
    
    def _init_session(self):
        """Initialize AWS session"""
        self.session = boto3.Session(
            aws_access_key_id=self.config["access_key_id"],
            aws_secret_access_key=self.config["secret_access_key"],
            region_name=self.config.get("region", "us-east-1")
        )
    
    async def list_ec2_instances(self) -> List[Dict]:
        """List all EC2 instances"""
        
        ec2 = self.session.client('ec2')
        instances = []
        
        try:
            response = ec2.describe_instances()
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        "instance_id": instance['InstanceId'],
                        "instance_type": instance['InstanceType'],
                        "state": instance['State']['Name'],
                        "launch_time": instance['LaunchTime'].isoformat(),
                        "public_ip": instance.get('PublicIpAddress'),
                        "private_ip": instance.get('PrivateIpAddress'),
                        "tags": {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                    })
            
            return instances
            
        except ClientError as e:
            logger.error(f"AWS EC2 list failed: {e}")
            return []
    
    async def list_s3_buckets(self) -> List[Dict]:
        """List all S3 buckets with security info"""
        
        s3 = self.session.client('s3')
        s3_resource = self.session.resource('s3')
        buckets = []
        
        try:
            response = s3.list_buckets()
            
            for bucket in response['Buckets']:
                bucket_name = bucket['Name']
                bucket_info = {
                    "name": bucket_name,
                    "creation_date": bucket['CreationDate'].isoformat(),
                    "public_access": False,
                    "encryption_enabled": False,
                    "versioning_enabled": False,
                    "logging_enabled": False
                }
                
                # Check public access
                try:
                    acl = s3.get_bucket_acl(Bucket=bucket_name)
                    for grant in acl['Grants']:
                        if 'URI' in grant['Grantee'] and 'AllUsers' in grant['Grantee']['URI']:
                            bucket_info['public_access'] = True
                except:
                    pass
                
                # Check encryption
                try:
                    encryption = s3.get_bucket_encryption(Bucket=bucket_name)
                    bucket_info['encryption_enabled'] = True
                except:
                    pass
                
                # Check versioning
                try:
                    versioning = s3.get_bucket_versioning(Bucket=bucket_name)
                    bucket_info['versioning_enabled'] = versioning.get('Status') == 'Enabled'
                except:
                    pass
                
                # Check logging
                try:
                    logging = s3.get_bucket_logging(Bucket=bucket_name)
                    bucket_info['logging_enabled'] = 'LoggingEnabled' in logging
                except:
                    pass
                
                buckets.append(bucket_info)
            
            return buckets
            
        except ClientError as e:
            logger.error(f"AWS S3 list failed: {e}")
            return []
    
    async def analyze_iam_policies(self) -> List[Dict]:
        """Analyze IAM policies for security issues"""
        
        iam = self.session.client('iam')
        issues = []
        
        try:
            # Check for root account usage
            account_summary = iam.get_account_summary()
            if account_summary['SummaryMap']['AccountAccessKeysPresent'] > 0:
                issues.append({
                    "type": "root_access_keys",
                    "severity": "critical",
                    "description": "Root account has access keys"
                })
            
            # Check for unused IAM users
            users = iam.list_users()['Users']
            for user in users:
                # Check password last used
                if 'PasswordLastUsed' not in user:
                    issues.append({
                        "type": "unused_user",
                        "severity": "medium",
                        "user": user['UserName'],
                        "description": f"User {user['UserName']} never used password"
                    })
                
                # Check access keys
                keys = iam.list_access_keys(UserName=user['UserName'])['AccessKeyMetadata']
                for key in keys:
                    if key['Status'] == 'Active':
                        last_used = iam.get_access_key_last_used(AccessKeyId=key['AccessKeyId'])
                        if 'LastUsedDate' not in last_used['AccessKeyLastUsed']:
                            issues.append({
                                "type": "unused_access_key",
                                "severity": "medium",
                                "user": user['UserName'],
                                "description": f"User {user['UserName']} has unused access key"
                            })
            
            return issues
            
        except ClientError as e:
            logger.error(f"AWS IAM analysis failed: {e}")
            return []