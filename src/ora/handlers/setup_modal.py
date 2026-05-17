"""/ora setup — Block Kit modal that collects birth data and computes charts."""

import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ora import subjects

logger = logging.getLogger(__name__)

CALLBACK_ID = "ora_setup"

# Default coords used when we can't geocode the birth place. Most clone members
# are in Korea, so Seoul is a sensible fallback. TODO: real geocoding (geopy
# or similar) — for now we trust the asker's tz to handle most of the math and
# only the Western Ascendant would be off if their city differs significantly
# from Seoul. We tell them in the confirmation message.
_DEFAULT_LAT, _DEFAULT_LON = 37.5665, 126.9780


def modal_view() -> dict:
    return {
        "type": "modal",
        "callback_id": CALLBACK_ID,
        "title": {"type": "plain_text", "text": "tell ora about you"},
        "submit": {"type": "plain_text", "text": "save"},
        "close": {"type": "plain_text", "text": "cancel"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "give me your birth date and place so i can read your chart. "
                        "birth time is optional — if you don't know it, the chart still "
                        "works, just a little less precise (no hour pillar, no Ascendant)."
                    ),
                },
            },
            {
                "type": "input",
                "block_id": "birth_date",
                "label": {"type": "plain_text", "text": "birth date"},
                "element": {
                    "type": "datepicker",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "pick a date"},
                },
            },
            {
                "type": "input",
                "block_id": "birth_time",
                "optional": True,
                "label": {"type": "plain_text", "text": "birth time (optional)"},
                "element": {
                    "type": "timepicker",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "pick a time"},
                },
            },
            {
                "type": "input",
                "block_id": "birth_place",
                "label": {"type": "plain_text", "text": "birth place"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "Seoul, South Korea"},
                    "initial_value": "Seoul, South Korea",
                },
            },
            {
                "type": "input",
                "block_id": "birth_tz",
                "label": {"type": "plain_text", "text": "timezone"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "initial_value": "Asia/Seoul",
                },
                "hint": {
                    "type": "plain_text",
                    "text": "IANA tz: Asia/Seoul, America/Los_Angeles, Europe/Berlin, etc.",
                },
            },
        ],
    }


def open_modal(client, trigger_id: str) -> None:
    client.views_open(trigger_id=trigger_id, view=modal_view())


def handle_submission(ack, view, body, client):
    values = view["state"]["values"]
    birth_date = values["birth_date"]["value"]["selected_date"]
    birth_time = values["birth_time"]["value"].get("selected_time")
    birth_place = values["birth_place"]["value"]["value"].strip()
    birth_tz = values["birth_tz"]["value"]["value"].strip()

    errors = {}
    try:
        ZoneInfo(birth_tz)
    except ZoneInfoNotFoundError:
        errors["birth_tz"] = f"'{birth_tz}' isn't a valid IANA tz name."
    if errors:
        ack(response_action="errors", errors=errors)
        return
    ack()

    user_id = body["user"]["id"]
    try:
        user_info = client.users_info(user=user_id)["user"]
        profile = user_info.get("profile", {})
        display_name = (
            profile.get("display_name")
            or profile.get("real_name")
            or user_info.get("name", user_id)
        )
    except Exception:
        logger.exception("users_info failed; using fallback name")
        display_name = user_id

    try:
        subjects.upsert_with_charts(
            kind="person",
            slack_user_id=user_id,
            display_name=display_name,
            birth_date=birth_date,
            birth_time=birth_time,
            birth_tz=birth_tz,
            birth_place=birth_place,
            birth_lat=_DEFAULT_LAT,
            birth_lon=_DEFAULT_LON,
            notes=None,
        )
    except Exception:
        logger.exception("upsert_with_charts failed for user %s", user_id)
        _dm(client, user_id,
            "something broke while saving your chart. give me a minute and try again.")
        return

    geo_note = ""
    if birth_place.lower() not in ("seoul", "seoul, south korea", "seoul, korea"):
        geo_note = (
            f" (heads up: i computed the Western chart against Seoul coords for now — "
            f"saju is exact, but the Ascendant/houses won't be quite right for {birth_place}. "
            f"good enough for v0.)"
        )
    _dm(client, user_id,
        f"got it. chart's saved.{geo_note} ask me anything in DM, or `/ora me` for a quick read.")


def _dm(client, user_id: str, text: str) -> None:
    try:
        im = client.conversations_open(users=user_id)
        client.chat_postMessage(channel=im["channel"]["id"], text=text)
    except Exception:
        logger.exception("failed to DM %s", user_id)
