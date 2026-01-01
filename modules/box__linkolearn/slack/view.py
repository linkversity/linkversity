import json
import re
import requests
import traceback
from flask import request
from flask import jsonify
from flask import render_template
from flask import current_app
from flask import redirect
from flask import url_for
from flask_login import login_required
from flask_login import current_user

from shopyo.api.module import ModuleHelp
from modules.box__default.auth.models import User
from modules.box__linkolearn.linkolearn.models import Path, Section, Link
from modules.box__linkolearn.slack.models import SlackUser, SlackWorkspace
from init import db, csrf

mhelp = ModuleHelp(__file__, __name__)
globals()[mhelp.blueprint_str] = mhelp.blueprint
module_blueprint = globals()[mhelp.blueprint_str]

@module_blueprint.route("/")
@login_required
def index():
    return render_template("linkolearn_theme/templates/slack.html")

@module_blueprint.route("/install")
@login_required
def install():
    client_id = current_app.config.get('SLACK_CLIENT_ID')
    scope = "commands,chat:write"
    user_scope = "identify"
    redirect_uri = url_for('slack.oauth_callback', _external=True)
    
    slack_url = f"https://slack.com/oauth/v2/authorize?client_id={client_id}&scope={scope}&user_scope={user_scope}&redirect_uri={redirect_uri}"
    return redirect(slack_url)

@module_blueprint.route("/oauth_callback")
@login_required
def oauth_callback():
    code = request.args.get('code')
    if not code:
        return "Error: No code provided", 400
    
    client_id = current_app.config.get('SLACK_CLIENT_ID')
    client_secret = current_app.config.get('SLACK_CLIENT_SECRET')
    redirect_uri = url_for('slack.oauth_callback', _external=True)

    resp = requests.post(
        "https://slack.com/api/oauth.v2.access",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri
        }
    )
    
    data = resp.json()
    if not data.get('ok'):
        return f"Slack OAuth Error: {data.get('error')}", 400

    team_id = data.get('team', {}).get('id')
    team_name = data.get('team', {}).get('name')
    bot_token = data.get('access_token')
    slack_user_id = data.get('authed_user', {}).get('id')

    workspace = SlackWorkspace.query.filter_by(team_id=team_id).first()
    if not workspace:
        workspace = SlackWorkspace(team_id=team_id, team_name=team_name, bot_token=bot_token)
        db.session.add(workspace)
    else:
        workspace.bot_token = bot_token
    
    slack_user = SlackUser.query.filter_by(slack_user_id=slack_user_id).first()
    if not slack_user:
        slack_user = SlackUser(slack_user_id=slack_user_id, user_id=current_user.id, team_id=team_id)
        db.session.add(slack_user)
    else:
        slack_user.user_id = current_user.id
        slack_user.team_id = team_id
    
    db.session.commit()
    return redirect(url_for('slack.connected'))

@module_blueprint.route("/connected")
@login_required
def connected():
    return render_template("linkolearn_theme/templates/connected.html")

@module_blueprint.route("/payload", methods=["POST"])
@csrf.exempt
def payload():
    try:
        payload_raw = request.form.get("payload")
        if not payload_raw:
            return jsonify({"error": "No payload"}), 400
        
        data = json.loads(payload_raw)
        slack_user_id = data.get("user", {}).get("id")
        team_id = data.get("team", {}).get("id")
        trigger_id = data.get("trigger_id")

        workspace = SlackWorkspace.query.filter_by(team_id=team_id).first()
        if not workspace:
            return jsonify({
                "response_action": "errors",
                "errors": {
                    "main": "App not installed correctly."
                }
            }), 200
        
        bot_token = workspace.bot_token

        if data.get("type") == "message_action":
            if data.get("callback_id") == "save_to_linkversity":
                slack_user = SlackUser.query.filter_by(slack_user_id=slack_user_id).first()
                
                message = data.get("message", {})
                text = message.get("text", "")
                links = re.findall(r'<(https?://[^\s>|]+)', text)
                link_to_save = links[0] if links else ""

                if not slack_user:
                    open_token_modal(trigger_id, link_to_save, bot_token)
                else:
                    open_save_modal(trigger_id, slack_user.user, link_to_save, bot_token)
                
                return "", 200

        elif data.get("type") == "view_submission":
            view = data.get("view", {})
            callback_id = view.get("callback_id")
            
            if callback_id == "link_account_modal":
                values = view.get("state", {}).get("values", {})
                token = ""
                for b_id, b_val in values.items():
                    if "token_input" in b_val:
                        token = b_val["token_input"].get("value")
                
                user = User.query.filter_by(api_token=token).first()
                if user:
                    slack_user = SlackUser.query.filter_by(slack_user_id=slack_user_id).first()
                    if not slack_user:
                        slack_user = SlackUser(slack_user_id=slack_user_id, user_id=user.id, team_id=team_id)
                        db.session.add(slack_user)
                    else:
                        slack_user.user_id = user.id
                        slack_user.team_id = team_id
                    db.session.commit()
                    
                    link_to_save = view.get("private_metadata")
                    open_save_modal(trigger_id, user, link_to_save, bot_token)
                    return jsonify({"response_action": "clear"})
                else:
                    return jsonify({
                        "response_action": "errors",
                        "errors": {
                            "token_block": "Invalid API Token."
                        }
                    })

            elif callback_id == "save_link_modal":
                values = view.get("state", {}).get("values", {})
                section_id = ""
                for b_id, b_val in values.items():
                    if "section_select" in b_val:
                        section_id = b_val["section_select"].get("selected_option", {}).get("value")

                url = view.get("private_metadata")
                if section_id and url:
                    new_link = Link(url=url, section_id=int(section_id))
                    db.session.add(new_link)
                    db.session.commit()
                    return jsonify({"response_action": "clear"})

    except Exception as e:
        print(f"Slack Payload Error: {str(e)}")
        return "", 200

    return "", 200

def open_token_modal(trigger_id, link_to_save, bot_token):
    if not bot_token: return
    view = {
        "type": "modal",
        "callback_id": "link_account_modal",
        "title": {"type": "plain_text", "text": "Link Linkversity"},
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": "It looks like your Slack account isn't linked yet."}},
            {
                "type": "input",
                "block_id": "token_block",
                "element": {"type": "plain_text_input", "action_id": "token_input", "placeholder": {"type": "plain_text", "text": "Enter your API Token"}},
                "label": {"type": "plain_text", "text": "API Token"}
            }
        ],
        "submit": {"type": "plain_text", "text": "Link Account"},
        "private_metadata": link_to_save
    }
    requests.post("https://slack.com/api/views.open",
        headers={"Authorization": f"Bearer {bot_token}"},
        json={"trigger_id": trigger_id, "view": view}
    )

def open_save_modal(trigger_id, user, link_to_save, bot_token):
    if not bot_token: return
    sections = []
    for path in user.paths:
        for section in path.sections:
            sections.append({
                "text": {"type": "plain_text", "text": f"{path.slug} > {section.title}"},
                "value": str(section.id)
            })
    
    if not sections:
        view = {
            "type": "modal",
            "title": {"type": "plain_text", "text": "Save Link"},
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "No sections found. Create one on Linkversity first."}}]
        }
    else:
        view = {
            "type": "modal",
            "callback_id": "save_link_modal",
            "title": {"type": "plain_text", "text": "Save Link"},
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"Saving: *{link_to_save}*"}},
                {
                    "type": "input",
                    "block_id": "section_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "section_select",
                        "placeholder": {"type": "plain_text", "text": "Select a section"},
                        "options": sections[:100]
                    },
                    "label": {"type": "plain_text", "text": "Section"}
                }
            ],
            "submit": {"type": "plain_text", "text": "Save"},
            "private_metadata": link_to_save
        }
    requests.post("https://slack.com/api/views.open",
        headers={"Authorization": f"Bearer {bot_token}"},
        json={"trigger_id": trigger_id, "view": view}
    )

@module_blueprint.route("/options", methods=["POST"])
@csrf.exempt
def options():
    payload_raw = request.form.get("payload")
    data = json.loads(payload_raw)
    if data.get("type") == "block_suggestion":
        slack_user_id = data.get("user", {}).get("id")
        slack_user = SlackUser.query.filter_by(slack_user_id=slack_user_id).first()
        if slack_user:
            sections = []
            for path in slack_user.user.paths:
                for section in path.sections:
                    sections.append({
                        "text": {"type": "plain_text", "text": f"{path.slug} > {section.title}"},
                        "value": str(section.id)
                    })
            query = data.get("value", "").lower()
            filtered_sections = [s for s in sections if query in s["text"]["text"].lower()]
            return jsonify({"options": filtered_sections[:100]})
    return jsonify({"options": []})

# --- Chrome Extension API ---

@module_blueprint.route("/chrome_ext_auth")
@login_required
def chrome_ext_auth():
    redirect_uri = request.args.get("redirect_uri")
    if not redirect_uri:
        return "Missing redirect_uri", 400
    
    token = current_user.get_api_token()
    # Redirect back to Chrome extension with the token
    return redirect(f"{redirect_uri}?token={token}")

@module_blueprint.route("/api/paths", methods=["GET"])
@csrf.exempt
def api_get_paths():
    token = request.args.get("token")
    user = User.query.filter_by(api_token=token).first()
    if not user:
        return jsonify({"error": "Invalid token"}), 401
    
    paths = [{"id": p.id, "title": p.slug} for p in user.paths]
    return jsonify(paths)

@module_blueprint.route("/api/sections", methods=["GET"])
@csrf.exempt
def api_get_sections():
    token = request.args.get("token")
    path_id = request.args.get("path_id")
    user = User.query.filter_by(api_token=token).first()
    if not user:
        return jsonify({"error": "Invalid token"}), 401
    
    path = Path.query.get(path_id)
    if not path or path.user_id != user.id:
        return jsonify({"error": "Path not found"}), 404
        
    sections = [{"id": s.id, "title": s.title} for s in path.sections]
    return jsonify(sections)

@module_blueprint.route("/api/save-link", methods=["POST"])
@csrf.exempt
def api_save_link():
    data = request.get_json()
    token = data.get("token")
    url = data.get("url")
    section_id = data.get("section_id")
    
    user = User.query.filter_by(api_token=token).first()
    if not user:
        return jsonify({"success": False, "error": "Invalid token"}), 401
        
    section = Section.query.get(section_id)
    if not section or section.section_path.user_id != user.id:
        return jsonify({"success": False, "error": "Section not found"}), 404

    new_link = Link(url=url, section_id=section_id)
    db.session.add(new_link)
    db.session.commit()
    
    return jsonify({"success": True})
