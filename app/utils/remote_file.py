import io
import logging
from functools import cached_property

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_s3 import S3Client

from app.utils.base_ import AppUtilBase

logger = logging.getLogger(__name__)

PROFILE_IMAGE_BUCKET = "mugip-profile-image"
AWS_S3_BASE_URL = f"{PROFILE_IMAGE_BUCKET}.s3.ap-notheast-2.amazonaws.com/"


class RemoteFileAppUtil(AppUtilBase):
    @cached_property
    def s3_client(self) -> S3Client:
        return boto3.client(
            service_name="s3",
            region_name="ap-northeast-2",
            aws_access_key_id=self.app_settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.app_settings.AWS_SECRET_ACCESS_KEY,
        )

    def upload_profile_image(
        self,
        file_name: str,
        file_obj: io.BytesIO,
    ) -> str:
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                PROFILE_IMAGE_BUCKET,
                file_name,
                ExtraArgs={
                    "ContentType": "image/jpeg",
                    "ACL": "public-read",
                },
            )
        except ClientError as err:
            raise RuntimeError("AWS s3 does not response", err)

        return AWS_S3_BASE_URL + file_name
