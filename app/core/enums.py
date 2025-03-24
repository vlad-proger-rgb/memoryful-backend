from enum import StrEnum

class EmailTemplate(StrEnum):
    CONFIRMATION_CODE = "confirmation_code"
    SUCCESSFUL_REGISTRATION = "successful_registration"
    LOGIN_ALERT = "login_alert"
    WEEKLY_REPORT = "weekly_report"
    MONTHLY_REPORT = "monthly_report"
