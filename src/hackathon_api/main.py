import base64
import json

import jwt
import uvicorn
from fastapi import FastAPI, Request, Response
from db import create_db_and_tables, Appointment, Client, AppUser
from sqlmodel import Field, Session, SQLModel, create_engine, select

app = FastAPI()
engine = create_engine("postgresql://user:secret@localhost:5432/hackathon", echo=True)

@app.on_event("startup")
def on_startup():
    create_db_and_tables(engine)


@app.post("/users")
def register_user(user: AppUser):
    with Session(engine) as session:
        session.add(user)
        session.commit()


@app.post("/users/login")
def login_user(req: Request):
    try:
        authorization_header = req.headers["Authorization"]
        credentials = authorization_header.replace("Basic ", "")
        convertedbytes = base64.b64decode(credentials)
        decodedsample = convertedbytes.decode("ascii")
    except:
        return Response(status_code=401)
    email = decodedsample.split(":")[0].strip()
    password = decodedsample.split(":")[1].strip()
    if password != "codefest":
        return Response(status_code=401)
    with Session(engine) as session:
        user = session.exec(select(AppUser).where(AppUser.email == email)).all()
        if (len(user) < 1):
            return Response(status_code=401)
        user_details = AppUser.as_dict(user[0])
        return Response(status_code=200, headers={
            "Authorization": "Bearer " + jwt.encode(user_details, "secret", algorithm="HS256")
        });


@app.get("/appointments")
def get_appointments_for_worker():
    with Session(engine) as session:
        appointments = session.exec(select(Appointment)).all()
        return appointments


@app.get("/appointments/{id}")
def get_appointment_by_id(id):
    with Session(engine) as session:
        appointment = session.exec(select(Appointment).where(Appointment.id == id)).all()
        return appointment


@app.post("/appointments")
def create_appointment(appointment: Appointment):
    with Session(engine) as session:
        session.add(appointment)
        session.commit()


@app.delete("/appointments/{id}")
def delete_appointment(id):
    with Session(engine) as session:
        session.delete(Appointment.id == id)


@app.get("/clients")
def get_clients():
    pass


@app.get("/clients/{id}")
def get_client_by_id(id):
    pass


@app.delete("/clients/{id}")
def delete_client_by_id(id):
    pass


def create_client(client: Client):
    pass


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=80)
