from pydantic import BaseModel
from app.schemas.document import Document

class Metadata(BaseModel):
    documents: list[Document] = []
    