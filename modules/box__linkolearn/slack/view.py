import json
import re
import requests
import traceback
from flask import request
from flask import jsonify
from flask import render_template
from flask import current_app
from flask_login import login_required
from flask_login import current_user

from shopyo.api.module import ModuleHelp
from modules.box__default.auth.models import User
from modules.box__linkolearn.linkolearn.models import Path, Section, Link
from modules.box__linkolearn.slack.models import SlackUser
from init import db

mhelp = ModuleHelp(__file__, __name__)
globals()[mhelp.blueprint_str] = mhelp.blueprint
module_blueprint = globals()[mhelp.blueprint_str]

@module_blueprint.route("/")
def index():
    return "Slack Module"

@module_blueprint.route("/token")
@login_required
def get_token():
    token = current_user.get_api_token()
    return render_template("linkolearn_theme/templates/slack.html", token=token)

@module_blueprint.route("/payload", methods=["POST"])
def payload():
    try:
        payload_raw = request.form.get("payload")
        if not payload_raw:
            print("Slack Error: No payload found in request")
            return jsonify({"error": "No payload"}), 400
        
        data = json.loads(payload_raw)
        slack_user_id = data.get("user", {}).get("id")
        trigger_id = data.get("trigger_id")

        if data.get("type") == "message_action":
            if data.get("callback_id") == "save_to_linkversity":
                slack_user = SlackUser.query.filter_by(slack_user_id=slack_user_id).first()
                
                message = data.get("message", {})
                text = message.get("text", "")
                # Find links like <http://google.com> or <http://google.com|google>
                links = re.findall(r'<(https?://[^\s>|]+)', text)
                link_to_save = links[0] if links else ""

                if not slack_user:
                    open_token_modal(trigger_id, link_to_save)
                else:
                    open_save_modal(trigger_id, slack_user.user, link_to_save)
                
                return "", 200

        elif data.get("type") == "view_submission":
            view = data.get("view", {})
            callback_id = view.get("callback_id")
            
            if callback_id == "link_account_modal":
                values = view.get("state", {}).get("values", {})
                # Accessing values safely
                token = ""
                for b_id, b_val in values.items():
                    if "token_input" in b_val:
                        token = b_val["token_input"].get("value")
                
                user = User.query.filter_by(api_token=token).first()
                if user:
                    new_slack_user = SlackUser(slack_user_id=slack_user_id, user_id=user.id)
                    db.session.add(new_slack_user)
                    db.session.commit()
                    
                    link_to_save = view.get("private_metadata")
                    open_save_modal(trigger_id, user, link_to_save)
                    return jsonify({"response_action": "clear"})
                else:
                    return jsonify({
                        "response_action": "errors",
                        "errors": {
                            "token_block": "Invalid API Token. Please check your Linkversity settings."
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
        traceback.print_exc()
        return "", 200 # Always return 200 to Slack to avoid "Sorry, did not work" if possible, but the error happened anyway

    return "", 200

def open_token_modal(trigger_id, link_to_save):
    bot_token = current_app.config.get('SLACK_BOT_TOKEN')
    if not bot_token:
        print("Error: SLACK_BOT_TOKEN not configured in app.config")
        return

    view = {
        "type": "modal",
        "callback_id": "link_account_modal",
        "title": {"type": "plain_text", "text": "Link Linkversity"},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "It looks like your Slack account isn't linked to Linkversity yet."}
            },
            {
                "type": "input",
                "block_id": "token_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "token_input",
                    "placeholder": {"type": "plain_text", "text": "Enter your API Token"}
                },
                "label": {"type": "plain_text", "text": "API Token"}
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "Find your token in your profile settings."}
                ]
            }
        ],
        "submit": {"type": "plain_text", "text": "Link Account"},
        "private_metadata": link_to_save
    }
    
    resp = requests.post(
        "https://slack.com/api/views.open",
        headers={"Authorization": f"Bearer {bot_token}"},
        json={"trigger_id": trigger_id, "view": view}
    )
    if not resp.json().get('ok'):
        print(f"Slack API Error (views.open): {resp.json()}")

def open_save_modal(trigger_id, user, link_to_save):
    bot_token = current_app.config.get('SLACK_BOT_TOKEN')
    if not bot_token:
        print("Error: SLACK_BOT_TOKEN not configured in app.config")
        return
    
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
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "You don't have any sections in your paths yet. Please create one on Linkversity first."}
                }
            ]
        }
    else:
        view = {
            "type": "modal",
            "callback_id": "save_link_modal",
            "title": {"type": "plain_text", "text": "Save Link"},
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"Saving link: *{link_to_save}*"}
                },
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

    resp = requests.post(
        "https://slack.com/api/views.open",
        headers={"Authorization": f"Bearer {bot_token}"},
        json={"trigger_id": trigger_id, "view": view}
    )
    if not resp.json().get('ok'):
        print(f"Slack API Error (views.open): {resp.json()}")