import shelve
import sys

sys.path.insert(1, "../common")
import discord
import common.utils as ut
from common.asyncTask import make_periodic_task, aligned_interval

twitch_OAuth_token = None
# Key: User_Name; Value: discord.Message
twitch_curr_livestreams = {}
STREAMER_DB_PATH = "./database/twitch_streamer_list.db"
_LIVE_CHECK_TASK = None


def init():
    """Start the periodic Twitch live-streamers check (every 15 minutes aligned)."""
    global _LIVE_CHECK_TASK
    _LIVE_CHECK_TASK = make_periodic_task(
        aligned_interval(900),
        lambda: check_twitch_live(ut.mainChannel),
    )
    _LIVE_CHECK_TASK.start()


async def check_twitch_live(channel):
    global twitch_OAuth_token
    global twitch_curr_livestreams

    try:
        # Need to generate OAuth token on startup and failed generation
        if not twitch_OAuth_token:
            await generate_twitch_OAuth_token(channel)

        with shelve.open(STREAMER_DB_PATH) as streamer_list_shelf:
            if not streamer_list_shelf:
                return

            # Request list of live streamers currently online from Twitch
            # Documentation: https://dev.twitch.tv/docs/api/reference/#get-streams
            twitch_streamers = "?user_login=" + "&user_login=".join(streamer_list_shelf.keys())
            url = "https://api.twitch.tv/helix/streams" + twitch_streamers
            headers = {"Client-ID": ut.env["TWITCH_CLIENT_ID"], "Authorization": "Bearer " + twitch_OAuth_token}

            stream = await ut.async_get_request(url, headers=headers)
            # Let stream fail once before generating twitch OAuth token
            # This will reduce the number of calls made by the application over time
            if not stream:
                if not await validate_twitch_OAuth_token(channel):
                    await generate_twitch_OAuth_token(channel)
                stream = await ut.async_get_request(url, headers=headers)
            # If it fails with a newly generated OAuth, then Twitch is probably down
            if not stream:
                raise Exception("Twitch is probably not online. Ignoring request")

            # If livestream is new, create message
            # else update the viewer count
            fetched_livestreams = {}
            for livestream in stream.get("data"):
                user_name = livestream["user_name"]
                if user_name not in twitch_curr_livestreams:
                    message = await channel.send(generate_message(livestream))
                else:
                    message = await twitch_curr_livestreams[user_name].edit(content=generate_message(livestream))
                fetched_livestreams[user_name] = message
            twitch_curr_livestreams = fetched_livestreams

    except Exception as e:
        await channel.send("Error Obtaining Live Twitch Streamer List: " + str(e))


def generate_message(livestream):
    message_content = livestream["user_name"] + " is live"

    # Don't show viewer_count if it is zero :(
    if not livestream["viewer_count"]:
        message_content += "!"
    else:
        message_content += " with " + str(livestream["viewer_count"]) + " viewers!"

    message_content += " Go support them at https://twitch.tv/" + livestream["user_name"]
    return message_content


async def validate_twitch_OAuth_token(channel):
    global twitch_OAuth_token

    if twitch_OAuth_token is not None:
        try:
            url = "https://id.twitch.tv/oauth2/validate"
            headers = {"Authorization": "OAuth " + twitch_OAuth_token}

            response = await ut.async_get_request(url, headers=headers)

            if not response or ("status" in response and response.get("status")) == 401:
                return False

            return True
        except Exception as e:
            await channel.send("Error Validating Twitch OAuth Token: " + str(e))
    return False


async def generate_twitch_OAuth_token(channel):
    global twitch_OAuth_token

    url = "https://id.twitch.tv/oauth2/token"
    twitch_OAuth_generation_body = {"client_id": ut.env["TWITCH_CLIENT_ID"], "client_secret": ut.env["TWITCH_CLIENT_SECRET"], "grant_type": "client_credentials"}

    try:
        response = await ut.async_post_request(url, twitch_OAuth_generation_body)
        twitch_OAuth_token = response["access_token"]
    except Exception as e:
        await channel.send("Error Generating Twitch OAuth Token: " + str(e))
        twitch_OAuth_token = None


# Validates a Twitch username against the Twitch Helix API. Handles OAuth internally.
# Returns False on any failure (network, auth, unknown user). Tests mock this directly.
async def _validate_twitch_username(twitch_username: str) -> bool:
    global twitch_OAuth_token
    try:
        if not twitch_OAuth_token:
            token_url = "https://id.twitch.tv/oauth2/token"
            body = {
                "client_id": ut.env["TWITCH_CLIENT_ID"],
                "client_secret": ut.env["TWITCH_CLIENT_SECRET"],
                "grant_type": "client_credentials",
            }
            response = await ut.async_post_request(token_url, body)
            twitch_OAuth_token = response["access_token"]

        headers = {
            "Client-ID": ut.env["TWITCH_CLIENT_ID"],
            "Authorization": "Bearer " + twitch_OAuth_token,
        }
        url = "https://api.twitch.tv/helix/users?login=" + twitch_username
        user = await ut.async_get_request(url, headers=headers)
        return bool(user and user.get("data"))
    except Exception:
        return False


# Add a streamer to the tracking list. Returns the message to display.
async def add_streamer_to_db(member: discord.Member, twitch_username: str) -> str:
    try:
        if not await _validate_twitch_username(twitch_username):
            return twitch_username + " is not a valid argument."

        db = shelve.open(STREAMER_DB_PATH)
        try:
            if db.get(twitch_username) is None:
                db[twitch_username] = member.name
                return f"Successfully added {member.name}"
            else:
                return "This entry already exists."
        finally:
            db.close()
    except Exception as e:
        return f"Error Adding Streamer: {e}"


# Remove a streamer from the tracking list. Takes the twitch_username (the
# unique DB key) so direct lookup works regardless of Discord renames.
async def remove_streamer_from_db(twitch_username: str) -> str:
    try:
        db = shelve.open(STREAMER_DB_PATH)
        try:
            if twitch_username in db:
                removed_name = db[twitch_username]
                del db[twitch_username]
                return f"Successfully removed {removed_name}"
            return f"{twitch_username} isn't being tracked"
        finally:
            db.close()
    except Exception as e:
        return f"Error Removing Streamer: {e}"


# Autocomplete for /admin twitch remove. Pulls from the DB so the picker
# shows stored names (survives Discord renames). The choice value is the
# twitch_username (the unique DB key), so remove can do a direct lookup.
async def tracked_twitch_streamer_autocomplete(interaction, current: str):
    matches = []
    db = shelve.open(STREAMER_DB_PATH)
    try:
        for twitch_username, member_name in db.items():
            label = f"{member_name} (twitch: {twitch_username})"
            if current.lower() in label.lower():
                matches.append((label, twitch_username))
    finally:
        db.close()
    matches.sort()
    return [discord.app_commands.Choice(name=label, value=twitch_username) for label, twitch_username in matches[:25]]


# Returns the text listing currently tracked streamers.
async def list_streamers_text() -> str:
    try:
        db = shelve.open(STREAMER_DB_PATH)
        try:
            if len(db) == 0:
                return "We are not tracking anyone currently."
            msg = "Here's everyone we're tracking:\n"
            for tw_user, member_name in db.items():
                msg += f"{member_name}: {tw_user}\n"
            return msg
        finally:
            db.close()
    except Exception as e:
        return f"Error Retrieving Streamers: {e}"
