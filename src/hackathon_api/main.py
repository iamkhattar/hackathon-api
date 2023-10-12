from typing import Annotated

import jwt
from datetime import datetime
import uvicorn
from fastapi import FastAPI, Response, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
from jose import JWTError
from pydantic import BaseModel

from db import create_db_and_tables, Appointment, Client, AppUser
from config import settings
from sqlmodel import Session, create_engine, select

app = FastAPI()
engine = create_engine(settings.DB_CONNECTION_STRING, echo=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class Token(BaseModel):
    access_token: str
    token_type: str


@app.on_event("startup")
def on_startup():
    create_db_and_tables(engine)


@app.post("/api/v1/users")
def register_user(user: AppUser):
    with Session(engine) as session:
        if user.type != "worker" and user.type != "manager":
            return Response(status_code=422)
        db_user = user
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, "secret", algorithms="HS256")
        user = AppUser(
            email=payload.get("email"),
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            type=payload.get("type"),
            phone=payload.get("phone"),
        )
    except JWTError:
        raise credentials_exception
    if user is None:
        raise credentials_exception
    return user


@app.get("/api/v1/users/me")
def whoami(current_user: Annotated[AppUser, Depends(get_current_user)]):
    with Session(engine) as session:
        user = session.exec(
            select(AppUser).where(AppUser.email == current_user.email)
        ).all()
        if not user:
            return Response(status_code=401)
        return user[0]


@app.post("/api/v1/users/login")
def login_user(credentials: Annotated[HTTPBasicCredentials, Depends(HTTPBasic())]):
    email = credentials.username
    password = credentials.password
    if password.strip() != "codefest":
        return Response(status_code=401)
    with Session(engine) as session:
        user = session.exec(select(AppUser).where(AppUser.email == email)).all()
        if not user:
            return Response(status_code=401)
        user_details = AppUser.as_dict(user[0])
        return Response(
            status_code=200,
            headers={
                "Authorization": f"""Bearer {
                jwt.encode(user_details, 'secret', algorithm='HS256')
                }"""
            },
        )


@app.get("/api/v1/appointments")
def get_appointments_for_worker(
    current_user: Annotated[AppUser, Depends(get_current_user)]
):
    # TODO
    with Session(engine) as session:
        if current_user.type == "worker":
            appointments = session.exec(select(Appointment)).all()
        else:
            now = datetime.now()
            print("hello", now)
            appointments = session.exec(select(Appointment).where()).all()
        return appointments


@app.get("/api/v1/appointments/{id}")
def get_appointment_by_id(id):
    with Session(engine) as session:
        result = session.exec(
            select(Appointment, Client, AppUser)
            .where(Appointment.id == id)
            .join(Client)
            .where(Appointment.client_id == Client.id)
            .join(AppUser)
            .where(AppUser.id == Appointment.worker_id)
        ).one()
        return {
            "end_time": result['Appointment'].end_time,
            "long": result["Appointment"].long,
            "appointment_status": result["Appointment"].appointment_status,
            "start_time": result["Appointment"].start_time,
            "id": result["Appointment"].id,
            "lat": result["Appointment"].lat,
            "address": result["Appointment"].address,
            "severity_status": result["Appointment"].severity_status,
            "client": result["Client"],
            "worker": result["AppUser"]
        }



@app.post("/api/v1/appointments")
def create_appointment(appointment: Appointment):
    with Session(engine) as session:
        worker = session.exec(
            select(AppUser).where(AppUser.id == appointment.worker_id)
        ).one()
        if not worker or worker.type != "worker":
            return Response(status_code=422)
        db_appointment = appointment
        session.add(db_appointment)
        session.commit()
        session.refresh(db_appointment)
        return db_appointment


@app.delete("/api/v1/appointments/{appointment_id}")
def delete_appointment(appointment_id):
    # TODO
    with Session(engine) as session:
        session.delete(Appointment.id == appointment_id)


@app.get("/api/v1/clients")
def get_clients():
    with Session(engine) as session:
        clients = session.exec(select(Client)).all()
    return clients


@app.delete("/api/v1/clients/{client_id}")
def delete_client_by_id(client_id):
    with Session(engine) as session:
        session.query(Client).filter(Client.id == client_id).delete()
        session.commit()


@app.post("/api/v1/clients")
def create_client(client: Client):
    with Session(engine) as session:
        db_client = client
        session.add(db_client)
        session.commit()
        session.refresh(db_client)
        return db_client


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)
