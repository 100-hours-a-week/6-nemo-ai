from google.cloud import aiplatform
from google.oauth2 import service_account
from src.config import PROJECT_ID, REGION, CREDENTIAL_PATH

credentials = service_account.Credentials.from_service_account_file(
    CREDENTIAL_PATH
)

aiplatform.init(
    project=PROJECT_ID,
    location=REGION,
    credentials=credentials
)