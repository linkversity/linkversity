# Welcome to linkversity

Learn from links. [#7 featured product](https://www.producthunt.com/products/contriblearn#contriblearn) on ProductHunt. free & opensource!


<a href='https://ko-fi.com/S6S2GDNC7' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

## QuickStart


1.

```
python -m pip install -r requirements.txt
```

2.

Create .env with the following (or add the following environment variables) or add those to instance/config.py

```.env
SQLALCHEMY_DATABASE_URI = "sqlite:///linkversity.db"

SALT = "some-salt"

RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY= ''
SECRET_KEY = 'secret-secret'
```

Optional

```
APP_NAME = ''
ACTIVE_FRONT_THEME = ''
ACTIVE_BACK_THEME = ''
```

If using gunicorn locally, use this

```py
import os
from dotenv import load_dotenv

for env_file in ('.env', '.flaskenv'):
    env = os.path.join(os.getcwd(), env_file)
    if os.path.exists(env):
        load_dotenv(env)
```

3.

Add config.json file in root dir with content

```json
{
    "admin_user": {
      "username": "appinv",
      "email": "admin@domain.com",
      "password": "pass"
    },
    "settings": {
      "APP_NAME": "Demo",
      "ACTIVE_FRONT_THEME": "blogus",
      "ACTIVE_BACK_THEME": "boogle",
      "CURRENCY": "MUR"
    }
}
```

4.

Run

```
shopyo initialise --no-clear-migration
flask run --debug
```

## Frontend


Frontend files located at /static/themes/front/linkolearn_theme

## Enterprise Mode

Linkversity offers an enterprise plan (subscription_plan=2) with advanced features for teams and organizations:

### Features

- **URL Encryption**: Enterprise links can be encrypted at rest in the database using per-organization encryption keys
- **Dedicated Database**: Optional isolated database per enterprise for complete tenant data separation
- **Audit Logging**: Full action logging for compliance (who did what and when)
- **Click Analytics**: Built-in analytics tracking with referrer, device type, and geographic data
- **Team Management**: Add team members with roles (admin, member, viewer)
- **Custom Domains**: Connect your own domain to your enterprise workspace
- **White Label**: Custom branding options for enterprise deployments

### Enterprise Models

| Model | Description |
|-------|-------------|
| `EnterpriseTeam` | Team/organization entity owned by a user |
| `EnterpriseSettings` | Encryption keys, domain config, feature flags |
| `EnterpriseAuditLog` | Compliance audit trail |
| `EnterpriseAnalytics` | Click/event tracking data |
| `EnterpriseTeamMember` | Team member associations |
| `EnterpriseCustomDomain` | Custom domain mappings |

### API Usage

```python
from modules.box__default.auth.models import User
from modules.box__linkolearn.linkolearn.encryption import encrypt_url, decrypt_url

# Create enterprise team
team = current_user.create_enterprise_team("My Company")

# Get enterprise settings
settings = current_user.get_enterprise_settings()

# Encrypt a link
link.set_encrypted_url(settings.encryption_key)

# Decrypt when needed
url = link.decrypt_url(settings.encryption_key)
```

### Enterprise Database

For strict data isolation, enterprises can use dedicated SQLite databases:

```python
from modules.box__linkolearn.linkolearn.enterprise_db import EnterpriseDatabaseManager

# Create dedicated database
db_manager = EnterpriseDatabaseManager()
db_manager.create_enterprise_database("company_name")

# Query isolated data
with enterprise_db_session("company_name") as session:
    paths = session.query(Path).all()
```