from django import forms
from django.contrib.auth.forms import UserCreationForm
from app.models import User
from django.contrib.auth import authenticate

class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["name", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField()
    
    def clean(self):
        print("LoginFormのcleanが呼び出されました")
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")
        print(email, password)
        if not email:
            raise forms.ValidationError("メールアドレスを入力してください")
        if not password:
            raise forms.ValidationError("パスワードを入力してください")
        self.user = authenticate(email=email, password=password)
        if not self.user:
            raise forms.ValidationError("認証に失敗しました")
        return self.cleaned_data