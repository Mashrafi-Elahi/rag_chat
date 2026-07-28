from django.urls import path

from .views import (
    ChangePasswordView,
    DashboardSummaryView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    ProfileView,
    SignupView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", SignupView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path(
        "forgot-password/",
        ForgotPasswordView.as_view(),
        name="forgot-password",
    ),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard-summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
]