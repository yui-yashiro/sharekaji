from django import forms
from django.contrib.auth.forms import UserCreationForm
from app.models import User, Family, Task, Recurrence
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

class AccountEditForm(forms.ModelForm):
    new_password = forms.CharField(required=False, widget=forms.PasswordInput())
    new_password_confirm = forms.CharField(required=False, widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ['name', 'email', 'family_relationship', "password", "new_password", "new_password_confirm"]
    
    def clean(self):
        print("AccountEditFormのcleanが呼び出されました")
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        new_password_confirm = cleaned_data.get('new_password_confirm')
        if new_password and new_password != new_password_confirm:
            self.add_error('new_password_confirm', 'パスワードが一致しません。')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
        return user
    
class FamilyEditForm(forms.ModelForm):
    class Meta:
        model = Family
        fields = ['name']

class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['profile_image']

class RecurringTaskForm(forms.ModelForm):
    class Meta:
        model = Recurrence
        fields = ['task_name', 'user', 'start_date', 'due_time', 'estimated_time', 'recurrence_type', 'weekday', 'day_of_month', 'end_date']

class IndividualTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['task_name', 'user', 'estimated_time', 'due_datetime']        