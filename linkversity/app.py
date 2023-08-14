import importlib
import os
import json
import jinja2
from flask import Flask
from flask import send_from_directory
from flask import redirect
from flask import url_for
from flask import request
from flask_login import current_user
from flask_wtf.csrf import CSRFProtect
from flask_admin import Admin
from flask_admin.contrib import sqla as flask_admin_sqla
from flask_admin import AdminIndexView
from flask_admin import expose
from flask_admin.menu import MenuLink
from shopyo.api.debug import is_yo_debug

from modules.box__default.settings.helpers import get_setting
from modules.box__default.settings.models import Settings
from modules.box__linkolearn.linkolearn.models import Path
from modules.box__linkolearn.linkolearn.models import Section
from modules.box__linkolearn.linkolearn.models import Link
from modules.box__linkolearn.linkolearn.models import Emoji

from config import app_config

from init import db
from init import login_manager
from init import ma
from init import migrate
from init import mail
from init import modules_path
from shopyo.api.file import trycopy

#
# Flask admin setup
#


class DefaultModelView(flask_admin_sqla.ModelView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for("auth.login", next=request.url))


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for("auth.login", next=request.url))

    @expose("/")
    def index(self):
        if (not current_user.is_authenticated and not current_user.is_admin):
            return redirect(url_for("auth.login"))
        return super(MyAdminIndexView, self).index()

    @expose("/dashboard")
    def indexs(self):
        if not current_user.is_authenticated and current_user.is_admin:
            return redirect(url_for("auth.login"))
        return super(MyAdminIndexView, self).index()


#
# secrets files
#


try:
    if not os.path.exists("config.json"):
        trycopy("config_demo.json", "config.json")
except PermissionError as e:
    print(
        "Cannot continue, permission error"
        "initializing config.py and config.json, "
        "copy and rename them yourself!"
    )
    raise e


base_path = os.path.dirname(os.path.abspath(__file__))


def create_app(config_name):

    app = Flask(__name__, instance_relative_config=True)
    configuration = app_config[config_name]
    app.config.from_object(configuration)

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

    migrate.init_app(app, db)
    db.init_app(app)
    ma.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    csrf = CSRFProtect(app)  # noqa

    admin = Admin(
        app,
        name="My App",
        template_mode="bootstrap4",
        index_view=MyAdminIndexView(),
    )
    admin.add_view(DefaultModelView(Settings, db.session))
    admin.add_view(DefaultModelView(Path, db.session))
    admin.add_view(DefaultModelView(Section, db.session))
    admin.add_view(DefaultModelView(Link, db.session))
    admin.add_view(DefaultModelView(Emoji, db.session))
    admin.add_link(
        MenuLink(name="Logout", category="", url="/auth/logout?next=/admin")
    )

    #
    # dev static
    #

    @app.route("/devstatic/<path:boxormodule>/f/<path:filename>")
    def devstatic(boxormodule, filename):
        if app.config["DEBUG"]:
            module_static = os.path.join(modules_path, boxormodule, "static")
            return send_from_directory(module_static, filename=filename)

    available_everywhere_entities = {

    }
    global_configs = {}


    load_blueprints(app, config_name, available_everywhere_entities, global_configs)

    #
    # custom templates folder
    #
    with app.app_context():
        front_theme_dir = os.path.join(
            app.config["BASE_DIR"], "static", "themes", "front"
        )
        back_theme_dir = os.path.join(
            app.config["BASE_DIR"], "static", "themes", "back"
        )
        my_loader = jinja2.ChoiceLoader(
            [
                app.jinja_loader,
                jinja2.FileSystemLoader([front_theme_dir, back_theme_dir]),
            ]
        )
        app.jinja_loader = my_loader

    #
    # global vars
    #
    @app.context_processor
    def inject_global_vars():
        APP_NAME = get_setting("APP_NAME")

        base_context = {
            "APP_NAME": APP_NAME,
            "len": len,
            "current_user": current_user,
        }
        base_context.update(available_everywhere_entities)

        return base_context

    # end of func
    return app


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
                    print(mod_global.available_everywhere)
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
                print(mod_global, mod_global.available_everywhere)
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

with open(os.path.join(base_path, "config.json")) as f:
    config_json = json.load(f)
environment = config_json["environment"]
app = create_app(environment)


if __name__ == "__main__":

    app.run(debug=False, host="0.0.0.0")
