from app.Extensions.Database import db


class ContactUsEntry(db.Model):
    __tablename__ = "marketing_contactus"

    id = db.Column("id", db.Integer, primary_key=True)
    first_name = db.Column("first_name", db.String)
    last_name = db.Column("last_name", db.String, default=None)
    email = db.Column("email", db.String)
    lead = db.Column("lead", db.String, default=None)
    question = db.Column("question", db.Text)

    def __init__(self, first_name: str, last_name: str, email: str, lead: str, question: str):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.lead = lead
        self.question = question

    def to_email(self) -> dict:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "lead": self.lead,
            "question": self.question,
        }
