from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from core.data_models import TradingParameters

# Set up credentials
SERVICE_ACCOUNT_FILE = 'google-service-account.json'
SCOPES = [
    'https://www.googleapis.com/auth/forms.responses.readonly',
    'https://www.googleapis.com/auth/forms',
    'https://www.googleapis.com/auth/drive.readonly'
]

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Google Forms API setup
forms_service = build('forms', 'v1', credentials=creds)

# Cache for registered users
registered_users_cache = []
last_update_time = datetime.min

def get_registered_users(force_update=False, form_id=None):
    """Fetch registered users from the Google Form."""
    global registered_users_cache, last_update_time

    if form_id is None:
        form_id = TradingParameters().google_form_id

    # Check if we need to update the cache
    if force_update or datetime.now() - last_update_time > timedelta(minutes=5):
        try:
            # Get form structure
            form = forms_service.forms().get(formId=form_id).execute()
            questions = {item['questionItem']['question']['questionId']: item['title'] 
                         for item in form['items'] if 'questionItem' in item}

            # Get form responses
            responses = forms_service.forms().responses().list(formId=form_id).execute()

            # Process responses
            registered_users_cache = []
            for response in responses.get('responses', []):
                for question_id, answer in response['answers'].items():
                    question_title = questions.get(question_id, "Unknown Question")
                    if question_title == "Gmail":
                        email = answer['textAnswers']['answers'][0]['value'] + "@gmail.com"
                        registered_users_cache.append(email)

            last_update_time = datetime.now()
        except HttpError:
            pass

    return registered_users_cache

def is_user_registered(email, form_id=None):
    """Check if a user's email is registered in the Google Form or is an admin."""
    username = email.split('@')[0]
    if username in TradingParameters().admin_users:
        return True
    registered_emails = get_registered_users(form_id=form_id)
    return email in registered_emails

def update_form_id(new_form_id):
    """Update the form ID (in case it changes)."""
    params = TradingParameters()
    params.google_form_id = new_form_id
    get_registered_users(force_update=True, form_id=new_form_id)

def is_user_admin(email):
    """Check if a user's email is in the admin list."""
    username = email.split('@')[0]
    return username in TradingParameters().admin_users
