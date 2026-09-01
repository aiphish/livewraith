
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import DateTime, func

class PKs(SQLModel, table=False):
    """
    Adds an integer primary key and a public UUID key to a model.
    """
    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True, index=True)

class APIScope(StrEnum):
    """
    API key scope.
    """
    GLOBAL = "global"
    ORG = "org"
    TENANT = "tenant"

class APIKeys(PKs, table=True):
    """
    API key table.
    """
    scope: APIScope

class BackendModels(StrEnum):
    """
    Lipsyncing models that work with the app.
    """
    MUSETALK = "musetalk"

class Wraiths(PKs, table=True):
    """
    Each entry represents a cloned identity available for livestreaming.
    """
    tenant_public_id: UUID
    org_public_id: UUID
    folder_path: str
    remote_path: bool
    model: BackendModels

class JobStatus(StrEnum):
    """
    Wraith creation status.
    """
    PENDING = "pending"
    COMPLETED = "completed"
    ERROR = "error"

class WraithCreateJobs(PKs, table=True):
    """
    Each entry represents an Wraith creation job. Can be polled for status.
    """

    wraith_id: int | None = Field(
        default=None,
        foreign_key="wraiths.id",
        index=True,
        ondelete="CASCADE"
    )
    status: JobStatus
    start_time: datetime = Field(
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            'server_default': func.now() # pylint: disable=not-callable
        },
        nullable=False
    )
    end_time: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True
    )
    tenant_public_id: UUID
    org_public_id: UUID
    file_path: str
    remote_path: bool
    model: BackendModels

    wraith: "Wraiths | None" = Relationship()
