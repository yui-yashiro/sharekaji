from typing import Any
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.base_user import AbstractBaseUser
from django.http.request import HttpRequest

from app.models import User

class UserAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
       print("UserAuthBackendが呼び出されました")
       email = username
       try:
           user = User.objects.get(email=email)
           if user.check_password(password):
               return user 
       except User.DoesNotExist:
           return None
       
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    