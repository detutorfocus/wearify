import cloudinary
import cloudinary.uploader
from app.core.config import settings


class StorageService:
    def __init__(self):
        if settings.STORAGE_BACKEND == "cloudinary":
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True,
            )

    async def upload_image(self, content: bytes, folder: str = "general") -> str:
        if settings.STORAGE_BACKEND == "cloudinary":
            return await self._cloudinary_upload(content, folder)
        return await self._s3_upload(content, folder)

    async def _cloudinary_upload(self, content: bytes, folder: str) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: cloudinary.uploader.upload(
                content,
                folder=f"wearify/{folder}",
                transformation=[
                    {"width": 1200, "height": 1600, "crop": "limit"},
                    {"quality": "auto", "fetch_format": "auto"},
                ],
            ),
        )
        return result["secure_url"]

    async def _s3_upload(self, content: bytes, folder: str) -> str:
        import boto3
        import uuid
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        key = f"wearify/{folder}/{uuid.uuid4().hex}.jpg"
        s3.put_object(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType="image/jpeg",
            ACL="public-read",
        )
        return f"https://{settings.AWS_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    async def delete_image(self, url: str) -> None:
        if settings.STORAGE_BACKEND == "cloudinary":
            public_id = url.split("/")[-1].split(".")[0]
            cloudinary.uploader.destroy(f"wearify/{public_id}")
