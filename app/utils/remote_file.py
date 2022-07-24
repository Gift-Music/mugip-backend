import asyncio
import io
import logging
from concurrent.futures import ThreadPoolExecutor

from botocore.exceptions import ClientError

from app.ctx import AppCtx

logger = logging.getLogger(__name__)

PROFILE_IMAGE_BUCKET = "mugip-profile-image"
AWS_S3_BASE_URL = f"{PROFILE_IMAGE_BUCKET}.s3.ap-notheast-2.amazonaws.com/"

_executor = ThreadPoolExecutor(10)


async def upload_profile_image(
    file_name: str,
    file_obj: io.BytesIO,
) -> str:
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            _executor,
            AppCtx.current.s3.upload_fileobj,
            file_obj,
            PROFILE_IMAGE_BUCKET,
            file_name,
            {
                "ContentType": "image/jpeg",
                "ACL": "public-read",
            },
        )
    except ClientError as err:
        raise RuntimeError("AWS s3 does not response", err)

    return AWS_S3_BASE_URL + file_name
