from typing import Annotated

import jwt
from datetime import datetime
import uvicorn
from fastapi import FastAPI, Response, Depends, HTTPException, status, Body
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import Date

from db import create_db_and_tables, Appointment, Client, AppUser
from config import settings
from sqlmodel import Session, create_engine, select

app = FastAPI()
engine = create_engine(settings.DB_CONNECTION_STRING, echo=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@app.on_event("startup")
def on_startup():
    create_db_and_tables(engine)


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, "secret", algorithms="HS256")
        user = AppUser(
            id=payload.get("id"),
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


@app.post("/api/v1/users")
def register_user(
    current_user: Annotated[AppUser, Depends(get_current_user)], user: AppUser
):
    with Session(engine) as session:
        if user.type != "worker" and user.type != "manager":
            return Response(status_code=422)
        db_user = user
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user


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
    with Session(engine) as session:
        if current_user.type == "worker":
            appointments = session.exec(
                select(Appointment, Client, AppUser)
                .where(Appointment.worker_id == current_user.id)
                .join(Client)
                .where(Appointment.client_id == Client.id)
                .join(AppUser)
                .where(AppUser.id == Appointment.worker_id)
            ).all()
            response = []
            for appointment in appointments:
                response.append(
                    {
                        "end_time": appointment["Appointment"].end_time,
                        "long": appointment["Appointment"].long,
                        "appointment_status": appointment[
                            "Appointment"
                        ].appointment_status,
                        "start_time": appointment["Appointment"].start_time,
                        "id": appointment["Appointment"].id,
                        "lat": appointment["Appointment"].lat,
                        "address": appointment["Appointment"].address,
                        "severity_status": appointment["Appointment"].severity_status,
                        "client": appointment["Client"],
                        "worker": appointment["AppUser"],
                    }
                )
            return response
        else:
            appointments = session.exec(
                select(Appointment).where(
                    Appointment.start_time.cast(Date) == datetime.now().date()
                )
            ).all()
        return appointments


@app.get("/api/v1/appointments/{appointment_id}")
def get_appointment_by_id(
    current_user: Annotated[AppUser, Depends(get_current_user)], appointment_id
):
    with Session(engine) as session:
        result = session.exec(
            select(Appointment, Client, AppUser)
            .where(Appointment.id == appointment_id)
            .join(Client)
            .where(Appointment.client_id == Client.id)
            .join(AppUser)
            .where(AppUser.id == Appointment.worker_id)
        ).one()
        return {
            "end_time": result["Appointment"].end_time,
            "long": result["Appointment"].long,
            "appointment_status": result["Appointment"].appointment_status,
            "start_time": result["Appointment"].start_time,
            "id": result["Appointment"].id,
            "lat": result["Appointment"].lat,
            "address": result["Appointment"].address,
            "severity_status": result["Appointment"].severity_status,
            "client": result["Client"],
            "worker": result["AppUser"],
        }


@app.post("/api/v1/appointments")
def create_appointment(
    current_user: Annotated[AppUser, Depends(get_current_user)],
    appointment: Appointment,
):
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
def delete_appointment(
    current_user: Annotated[AppUser, Depends(get_current_user)], appointment_id
):
    with Session(engine) as session:
        session.query(Appointment).filter(Appointment.id == appointment_id).delete()
        session.commit()


@app.get("/api/v1/clients")
def get_clients(current_user: Annotated[AppUser, Depends(get_current_user)]):
    with Session(engine) as session:
        clients = session.exec(select(Client)).all()
    return clients


@app.delete("/api/v1/clients/{client_id}")
def delete_client_by_id(
    current_user: Annotated[AppUser, Depends(get_current_user)], client_id
):
    with Session(engine) as session:
        session.query(Client).filter(Client.id == client_id).delete()
        session.commit()


@app.post("/api/v1/clients")
def create_client(
    current_user: Annotated[AppUser, Depends(get_current_user)], client: Client
):
    with Session(engine) as session:
        db_client = client
        session.add(db_client)
        session.commit()
        session.refresh(db_client)
        return db_client


@app.put("/api/v1/appointments/{appointment_id}/{status_field}")
def change_appointment_status(
    current_user: Annotated[AppUser, Depends(get_current_user)],
    appointment_id,
    status_field,
    updated_status: Annotated[str, Body(alias="status", embed=True)],
):
    with Session(engine) as session:
        appointment = session.exec(
            select(Appointment).where(Appointment.id == appointment_id)
        ).one()

        match status_field:
            case "status":
                appointment.appointment_status = updated_status

            case "severity":
                appointment.severity_status = updated_status

        session.add(appointment)
        session.commit()
        session.refresh(appointment)
        return appointment


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)
