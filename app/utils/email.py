import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import cached_property

from pydantic import BaseModel, EmailStr

from app.utils.base_ import AppUtilBase


class EmailModel(BaseModel):
    to: EmailStr
    subject: str
    message: str


class EmailAppUtil(AppUtilBase):
    @cached_property
    def send_server(self) -> smtplib.SMTP:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(
            self.app_settings.SENDER_MAIL, self.app_settings.SENDER_MAIL_PASSWORD
        )
        return server

    def send_email(self, mail_model: EmailModel) -> None:
        mail = MIMEMultipart()
        mail["Subject"] = mail_model.subject
        mail["From"] = self.app_settings.SENDER_MAIL
        mail["To"] = mail_model.to

        mail.attach(MIMEText(mail_model.message, "plain"))

        self.send_server.sendmail(
            self.app_settings.SENDER_MAIL, mail_model.to, mail.as_string()
        )
