from django.contrib.auth.models import User
from prison.models import Visitor

def log_activity(user, action, model, object_id, details):
    # Example logging logic (adjust to match your activity model)
    print(f"LOG: {user} {action} {model} {object_id} - {details}")