from typing import Annotated

import jwt
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
        user = session.exec(select(AppUser).where(AppUser.email == current_user.email)).all()
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


@app.get("/appointments")
def get_appointments_for_worker(
    current_user: Annotated[AppUser, Depends(get_current_user)]
):
    with Session(engine) as session:
        appointments = session.exec(select(Appointment)).all()
        return appointments


@app.get("/appointments/{id}")
def get_appointment_by_id(id):
    with Session(engine) as session:
        appointment = session.exec(
            select(Appointment).where(Appointment.id == id)
        ).all()
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
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)
