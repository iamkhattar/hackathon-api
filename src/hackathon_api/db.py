import datetime
from typing import Optional
from sqlmodel import Field, Session, SQLModel, create_engine, select


class AppUser(SQLModel, table=True):
    email: str = Field(default=None, primary_key=True)
    first_name: str = Field(default=None)
    last_name: str = Field(default=None)
    type: str = Field(default=None)
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Client(SQLModel, table=True):
    email: str = Field(default=None, primary_key=True)
    first_name: str = Field(default=None)
    last_name: str = Field(default=None)
    phone: str = Field(default=None)


class Appointment(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    client_email: str = Field(default=None, foreign_key="client.email")
    worker_email: str = Field(default=None, foreign_key="appuser.email")
    timestamp: datetime.datetime = Field(default=None)
    lat: str = Field(default=None)
    long: str = Field(default=None)
    address: str = Field(default=None)


class Rating(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    client_email: str = Field(default=None, foreign_key="client.email")
    value: int = Field(default=None)
    notes: str = Field(default=None)
    appointment_id: int = Field(default=None, foreign_key="appointment.id")


def create_db_and_tables(engine):
    SQLModel.metadata.create_all(engine)
