"""
Temporary notice:

Need help?

- Join the discord https://discord.com/invite/k37Ef6w
- Raise an issue https://github.com/shopyo/shopyo/issues/new/choose
- Mail maintainers https://github.com/shopyo/shopyo#-contact

Hope it helps! We welcome all questions and even requests for walkthroughs
"""
import importlib
import os
import sys

import click
import jinja2
from flask import Flask
from flask_admin import Admin
from flask_admin.menu import MenuLink
from flask_login import current_user

from shopyo.api.assets import register_devstatic
from shopyo.api.debug import is_yo_debug
from shopyo.api.file import trycopy



base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_path)
from config import app_config

from modules.box__default.auth.models import User
from modules.box__linkolearn.linkolearn.models import Path
from modules.box__linkolearn.linkolearn.models import LikeList
from modules.box__linkolearn.linkolearn.models import BookmarkList
from modules.box__linkolearn.linkolearn.models import Section
from modules.box__linkolearn.linkolearn.models import Link
from modules.box__linkolearn.linkolearn.models import Emoji 
from modules.box__linkolearn.linkolearn.models import ActivationCode

from shopyo_admin import DefaultModelView

from init import db
from init import load_extensions
from init import modules_path




try:
    from init import installed_packages
except ImportError:
    click.echo(
        "This version of Shopyo requires that\n"
        "init.py contains the line\n"
        "installed_packages = []\n"
        "please add it."
    )
    sys.exit()

from shopyo_admin import MyAdminIndexView


def create_app(config_name="development"):
    from dotenv import load_dotenv
    load_dotenv()

    global_template_variables = {}
    global_configs = {}
    app = Flask(
        __name__,
        instance_path=os.path.join(base_path, "instance"),
        instance_relative_config=True,
    )

    try:
        app.config.from_pyfile('config.py')
    except:
        pass 
    from werkzeug.middleware.proxy_fix import ProxyFix
    from flask import request, jsonify
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    load_plugins(app, global_template_variables, global_configs, config_name)
    load_config_from_obj(app, config_name)
    load_config_from_instance(app, config_name)
    create_config_json()
    load_extensions(app)

    # Connection pool settings
    app.config['SQLALCHEMY_POOL_SIZE'] = 5  # Number of connections to keep in the pool
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 10  # Extra connections beyond pool_size
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30  # Maximum wait time for a connection
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 1800  # Recycle connections every 30 minutes

    # Disable track_modifications to save memory
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SESSION_COOKIE_SECURE'] = True  # Ensures cookies are only sent over HTTPS
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # or 'None' if cross-site


    setup_flask_admin(app)
    register_devstatic(app, modules_path)
    load_blueprints(app, config_name, global_template_variables, global_configs)
    setup_theme_paths(app)
    inject_global_vars(app, global_template_variables)


    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'User':User}
    return app


def load_plugins(app, global_template_variables, global_configs, config_name):
    for plugin in installed_packages:
        if plugin not in ["shopyo_admin"]:
            try:
                mod = importlib.import_module(f"{plugin}.view")
                app.register_blueprint(getattr(mod, f"{plugin}_blueprint"))
            except AttributeError:
                # print("[ ] Blueprint skipped:", e)
                pass

            # global's available everywhere template vars
            try:
                mod_global = importlib.import_module(f"{plugin}.global")
                global_template_variables.update(mod_global.available_everywhere)
            except ImportError as e:
                if is_yo_debug():
                    print("[ ] Not loading template variable", e)

            except AttributeError as e:
                if is_yo_debug():
                    print("[ ] Not loading template variable", e)

            # load configs
            try:
                mod_global = importlib.import_module(f"{plugin}.global")
                if config_name in mod_global.configs:
                    global_configs.update(mod_global.configs.get(config_name))
            except ImportError as e:
                # print(f"[ ] {e}")
                if is_yo_debug():
                    print("[ ] Not loading template variable", e)
            except AttributeError as e:
                # click.echo('info: config not found in global')
                if is_yo_debug():
                    print("[ ] Not loading template variable", e)


def load_config_from_obj(app, config_name):
    try:
        configuration = app_config[config_name]
    except KeyError as e:
        print(
            f"[ ] Invalid config name {e}. Available configurations are: "
            f"{list(app_config.keys())}\n"
        )
        sys.exit(1)

    app.config.from_object(configuration)


def load_config_from_instance(app, config_name):
    if config_name != "testing":
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)

    # create empty instance folder and empty config if not present
    try:
        os.makedirs(app.instance_path)
        with open(os.path.join(app.instance_path, "config.py"), "a"):
            pass
    except OSError:
        pass


def create_config_json():
    if not os.path.exists("config.json"):
        trycopy("config_demo.json", "config.json")


def setup_flask_admin(app):
    admin = Admin(
        app,
        name="My App",
        template_mode="bootstrap4",
        index_view=MyAdminIndexView(),
    )
    admin.add_view(DefaultModelView(User, db.session))
    admin.add_view(DefaultModelView(Path, db.session))
    admin.add_view(DefaultModelView(LikeList, db.session))
    admin.add_view(DefaultModelView(BookmarkList, db.session))
    admin.add_view(DefaultModelView(Section, db.session))
    admin.add_view(DefaultModelView(Link, db.session))
    admin.add_view(DefaultModelView(Emoji, db.session))
    admin.add_view(DefaultModelView(ActivationCode, db.session))
    admin.add_link(MenuLink(name="Logout", category="", url="/auth/logout?next=/admin"))


def load_blueprints(app, config_name, global_template_variables, global_configs):
    """
    - Registers blueprints
    - Adds global template objects from modules
    - Adds global configs from modules
    """
    for folder in os.listdir(os.path.join(base_path, "modules")):
        if folder.startswith("__"):  # ignore __pycache__
            continue

        if folder.startswith("box__"):
            # boxes
            for sub_folder in os.listdir(os.path.join(base_path, "modules", folder)):
                if sub_folder.startswith("__"):  # ignore __pycache__
                    continue
                elif sub_folder.endswith(".json"):  # box_info.json
                    continue
                try:
                    sys_mod = importlib.import_module(
                        f"modules.{folder}.{sub_folder}.view"
                    )
                    app.register_blueprint(getattr(sys_mod, f"{sub_folder}_blueprint"))
                except AttributeError:
                    pass
                try:
                    mod_global = importlib.import_module(
                        f"modules.{folder}.{sub_folder}.global"
                    )
                    global_template_variables.update(mod_global.available_everywhere)
                except ImportError as e:
                    if is_yo_debug():
                        print("[ ] skipped", e)

                except AttributeError as e:
                    if is_yo_debug():
                        print("[ ] skipped", e)

                # load configs
                try:
                    mod_global = importlib.import_module(
                        f"modules.{folder}.{sub_folder}.global"
                    )
                    if config_name in mod_global.configs:
                        global_configs.update(mod_global.configs.get(config_name))
                except ImportError as e:
                    if is_yo_debug():
                        print("[ ] skipped", e)

                except AttributeError as e:
                    # click.echo('info: config not found in global')
                    if is_yo_debug():
                        print("[ ] skipped", e)
        else:
            # apps
            try:
                mod = importlib.import_module(f"modules.{folder}.view")
                app.register_blueprint(getattr(mod, f"{folder}_blueprint"))
            except AttributeError as e:
                if is_yo_debug():
                    print("[ ] skipped", e)

            # global's available everywhere template vars
            try:
                mod_global = importlib.import_module(f"modules.{folder}.global")
                global_template_variables.update(mod_global.available_everywhere)
            except ImportError as e:
                # print(f"[ ] {e}")
                if is_yo_debug():
                    print("[ ] skipped", e)

            except AttributeError as e:
                if is_yo_debug():
                    print("[ ] skipped", e)

            # load configs
            try:
                mod_global = importlib.import_module(f"modules.{folder}.global")
                if config_name in mod_global.configs:
                    global_configs.update(mod_global.configs.get(config_name))
            except ImportError as e:
                # print(f"[ ] {e}")
                if is_yo_debug():
                    print("[ ] skipped", e)
            except AttributeError as e:
                # click.echo('info: config not found in global')
                if is_yo_debug():
                    print("[ ] skipped", e)

    app.config.update(**global_configs)


def setup_theme_paths(app):
    with app.app_context():
        front_theme_dir = os.path.join(
            app.config["BASE_DIR"], "static", "themes", "front"
        )
        back_theme_dir = os.path.join(
            app.config["BASE_DIR"], "static", "themes", "back"
        )

        if os.path.exists(front_theme_dir) and os.path.exists(back_theme_dir):
            my_loader = jinja2.ChoiceLoader(
                [
                    app.jinja_loader,
                    jinja2.FileSystemLoader([front_theme_dir, back_theme_dir]),
                ]
            )
            app.jinja_loader = my_loader


def inject_global_vars(app, global_template_variables):
    @app.context_processor
    def inject_global_vars():
        APP_NAME = os.environ.get('APP_NAME', 'PLEASE SET APP NAME in .env')

        base_context = {
            "APP_NAME": APP_NAME,
            "len": len,
            "current_user": current_user,
        }
        base_context.update(global_template_variables)

        return base_context

app = create_app(os.environ.get('FLASK_ENV', 'production'))

@app.cli.command("update-password")
@click.argument("username")
@click.argument("password")
def update_password(username, password):
    """Update user password."""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.password = password
            db.session.commit()
            print(f"Password for user '{username}' updated successfully.")
        else:
            print(f"User '{username}' not found.")
