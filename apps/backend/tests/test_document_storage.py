from types import SimpleNamespace

from app.services.document_storage import (
    S3DocumentStorage,
    SupabaseDocumentStorage,
)


class FakeSupabaseBucket:
    def __init__(self):
        self.uploads = []
        self.downloads = {}

    def upload(self, key, contents, options):
        self.uploads.append((key, contents, options))

    def download(self, key):
        return self.downloads[key]

    def create_signed_url(self, key, expires_in):
        return {"signedURL": f"https://storage.test/{key}?expires={expires_in}"}


class FakeSupabaseStorage:
    def __init__(self):
        self.bucket = FakeSupabaseBucket()
        self.created_buckets = []

    def from_(self, bucket):
        assert bucket == "documents"
        return self.bucket

    def get_bucket(self, bucket):
        assert bucket == "documents"

    def create_bucket(self, bucket):
        self.created_buckets.append(bucket)


def test_supabase_storage_exposes_provider_neutral_operations():
    storage_api = FakeSupabaseStorage()
    storage = SupabaseDocumentStorage(
        SimpleNamespace(storage=storage_api),
        bucket="documents",
    )
    storage_api.bucket.downloads["digemid/example.pdf"] = b"pdf"

    storage.ensure_bucket()
    storage.upload("digemid/example.pdf", b"pdf", content_type="application/pdf")

    assert storage.download("digemid/example.pdf") == b"pdf"
    assert storage.create_download_url("digemid/example.pdf", 300) == (
        "https://storage.test/digemid/example.pdf?expires=300"
    )
    assert storage_api.bucket.uploads == [
        (
            "digemid/example.pdf",
            b"pdf",
            {"content-type": "application/pdf", "upsert": "true"},
        )
    ]


class FakeS3Client:
    class exceptions:
        class ClientError(Exception):
            pass

    def __init__(self):
        self.objects = {}
        self.created_buckets = []

    def head_bucket(self, *, Bucket):
        if Bucket not in self.created_buckets:
            raise self.exceptions.ClientError()

    def create_bucket(self, *, Bucket):
        self.created_buckets.append(Bucket)

    def put_object(self, *, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = (Body, ContentType)

    def get_object(self, *, Bucket, Key):
        return {"Body": SimpleNamespace(read=lambda: self.objects[(Bucket, Key)][0])}

    def generate_presigned_url(self, operation, *, Params, ExpiresIn):
        assert operation == "get_object"
        return (
            f"https://s3.test/{Params['Bucket']}/{Params['Key']}"
            f"?expires={ExpiresIn}"
        )


def test_s3_storage_uses_the_same_contract():
    client = FakeS3Client()
    storage = S3DocumentStorage(client=client, bucket="documents")

    storage.ensure_bucket()
    storage.upload("digemid/example.pdf", b"pdf", content_type="application/pdf")

    assert storage.download("digemid/example.pdf") == b"pdf"
    assert storage.create_download_url("digemid/example.pdf", 300) == (
        "https://s3.test/documents/digemid/example.pdf?expires=300"
    )
