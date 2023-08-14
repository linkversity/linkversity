from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms import PasswordField
from wtforms.validators import DataRequired

class ChangeNameForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()], render_kw={'autocomplete':'off'})
    last_name = StringField('Last Name', validators=[DataRequired()], render_kw={'autocomplete':'off'})


class ChangePasswordForm(FlaskForm):
    password1 = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Reconfirm password', validators=[DataRequired()])

