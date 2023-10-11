import datetime
from sqlmodel import Field, SQLModel


class AppUser(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    email: str = Field(default=None)
    first_name: str = Field(default=None)
    last_name: str = Field(default=None)
    type: str = Field(default=None)
    phone: str = Field(default=None)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Client(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    email: str = Field(default=None)
    first_name: str = Field(default=None)
    last_name: str = Field(default=None)
    phone: str = Field(default=None)


class Appointment(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    client_id: int = Field(default=None, foreign_key="client.id")
    worker_id: int = Field(default=None, foreign_key="appuser.id")
    start_time: datetime.datetime = Field(default=None)
    end_time: datetime.datetime = Field(default=None)
    lat: float = Field(default=None)
    long: float = Field(default=None)
    address: str = Field(default=None)
    appointment_status: str = Field(default=None)
    severity_status: str = Field(default=None)


def create_db_and_tables(engine):
    SQLModel.metadata.create_all(engine)
