import json
from fastapi import FastAPI, requests, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
import os
import requests
import uvicorn
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from dotenv import load_dotenv


def load_creds():
    if os.path.exists(TOKEN_FILE_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE_PATH, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE_PATH, "w") as token_file:
                token_file.write(creds.to_json())

        return creds
    return None


app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
TOKEN_FILE_PATH = os.getenv("TOKEN_FILE_PATH")
CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE")
FRONTEND_URL = os.getenv("FRONTEND_URL")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
with open(CLIENT_SECRET_FILE, "r") as f:
    data = json.load(f)
    GOOGLE_CLIENT_ID = data["installed"]["client_id"]
    GOOGLE_CLIENT_SECRET = data["installed"]["client_secret"]
    GOOGLE_REDIRECT_URI = data["installed"]["redirect_uris"][0] + ":8000/auth/google"


@app.get("/")
async def root():
    return {"Hello": "World"}


@app.get("/demo")
async def demo():
    print("Reached backend")
    return {"Reached": "Backend"}


@app.get("/login/google")
async def login_google():
    return {
        "url": f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"
    }


@app.get("/auth/google")
async def auth_google(code: str):
    token_url = "https://accounts.google.com/o/oauth2/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data)
    access_token = response.json().get("access_token")
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})

    frontend_redirect_url = f"{FRONTEND_URL}?name={user_info.json()['name']}&email={user_info.json()['email']}"
    # print(user_info.json()["name"], user_info.json()["email"])
    return RedirectResponse(url=frontend_redirect_url)


@app.get("/token")
async def get_token(token: str = Depends(oauth2_scheme)):
    return jwt.decode(token, GOOGLE_CLIENT_SECRET, algorithms=["HS256"])


# @app.get("/auth")
# async def auth():
#     creds = load_creds()
#     if not creds:
#         flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
#         creds = flow.run_local_server(port=0)
#         with open(TOKEN_FILE_PATH, "w") as token_file:
#             token_file.write(creds.to_json())
#
#     # print(creds)
#     print(creds.to_json())
#     return {"message": "Successfully logged in"}


# @app.get("/drive/list")
# async def list_files():
#     creds = load_creds()
#     if not creds:
#         return {"message": "User not authenticated"}
#
#     service = build("drive", "v3", credentials=creds)
#     results = service.files().list(fields="files(id, name)").execute()
#     items = results.get("files", [])
#
#     files_with_info = [{"id": item["id"], "name": item["name"]} for item in items]
#
#     return files_with_info


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)