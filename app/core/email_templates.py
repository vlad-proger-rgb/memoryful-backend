from app.enums import EmailTemplate

EMAIL_TEMPLATES = {
    EmailTemplate.CONFIRMATION_CODE: "confirmation_code.html",
    EmailTemplate.SUCCESSFUL_REGISTRATION: "successful_registration.html",
    EmailTemplate.LOGIN_ALERT: "login_alert.html",
    EmailTemplate.WEEKLY_REPORT: "weekly_report.html",
    EmailTemplate.MONTHLY_REPORT: "monthly_report.html",
}
