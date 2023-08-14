from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import PasswordField
from wtforms import StringField
from wtforms.fields import EmailField

from wtforms.validators import DataRequired
from wtforms.validators import Email
from wtforms.validators import InputRequired
from wtforms.validators import Length
from wtforms.validators import EqualTo
from wtforms.validators import ValidationError

from .models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()],
        render_kw={"class": "form-control", "autocomplete": "off", 'placeholder': 'Username'})
    password = PasswordField(
        "Password",
        [DataRequired()],
        render_kw={"class": "form-control", "autocomplete": "off", 'placeholder':'Password'},
    )


class RegistrationForm(FlaskForm):
    """ Registration Form """

    username = StringField('Username', validators=[DataRequired()],
        render_kw={'placeholder': 'Username alphanumeric and - allowed'
        })

    password = PasswordField(
        "New Password",
        validators=[
            InputRequired("Password is required"),
            Length(
                min=6,
                max=25,
                message="Password must be between 6 and 25 characters",
            ),
            EqualTo("confirm", message="Passwords must match"),
        ],
        render_kw={
        'placeholder': 'Password min. 6 chars'
        }
    )
    confirm = PasswordField(
        "New Password",
        validators=[
            InputRequired("Password is required"),
            Length(
                min=6,
                max=25,
                message="Password must be between 6 and 25 characters",
            ),
            EqualTo("confirm", message="Passwords must match"),
        ],
        render_kw={
        'placeholder': 'Reconfirm password'
        }
    )

    def validate_email(self, field):
        """
        Inline validator for email. Checks to see if a user object with
        entered email already present in the database

        Args:
            field : The form field that contains email data.

        Raises:
            ValidationError: if the username entered in the field is already
            in the database
        """
        user = User.query.filter(
            func.lower(User.email) == func.lower(field.data)
        ).scalar()

        if user is not None:
            raise ValidationError(f"email '{field.data}' is already in use.")
