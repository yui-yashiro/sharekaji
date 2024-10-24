"""sharekaji URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from app.views import SignUpView, LoginView, HomeView, TodayTasksView, RecurringTaskListView, RecurringTaskCreateView, Individual_TaskCreateView, TaskAnalysisView, MyPageView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',LoginView.as_view(), name="login"),
    path('signup/',SignUpView.as_view(), name="signup"),
    path('home/',HomeView.as_view(), name="home"),
    path('home/<int:year>/<int:month>/', HomeView.as_view(), name="home_with_date"),
    path('today_tasks/', TodayTasksView.as_view(), name="today_tasks"),
    path('recurring_tasks/', RecurringTaskListView.as_view(), name="recurring_tasks"),
    path('task_analysis/', TaskAnalysisView.as_view(), name="task_analysis"),
    path('mypage/', MyPageView.as_view(), name="mypage"),
    path('add_recurring_tasks/', RecurringTaskCreateView.as_view(), name="add_recurring_tasks"),
    path('add_individual_tasks/', Individual_TaskCreateView.as_view(), name="add_individual_tasks"),
]
