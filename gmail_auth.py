from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

flow = InstalledAppFlow.from_client_secrets_file(
    "credentials.json", SCOPES
)

creds = flow.run_local_server(port=0)

with open("token.pickle", "wb") as token:
    pickle.dump(creds, token)

print("OAuth setup complete. Token saved.")
