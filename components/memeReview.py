import shelve
import operator
import math
import discord

import common.utils as ut
from common.periodicTask import PeriodicTask

notMeme = "kekegolaughands"
badMeme = "thumbsdown"
ehMeme = "one"
goodMeme = "two"
bestMeme = "three"

_BEST_ANNOUNCEMENT_TASK = None
_RESET_LIMIT_TASK = None


def init():
    """Start the periodic meme tasks: weekly best-of announcement + daily reset."""
    global _BEST_ANNOUNCEMENT_TASK, _RESET_LIMIT_TASK
    _BEST_ANNOUNCEMENT_TASK = PeriodicTask.weekly(
        (ut.env["ANNOUNCEMENT_DAY"] - 1) % 7,
        ut.env["ANNOUNCEMENT_HOUR"],
        ut.env["ANNOUNCEMENT_MIN"],
        lambda: best_announcement_task(ut.mainChannel),
    )
    _RESET_LIMIT_TASK = PeriodicTask.every(86400, resetLimit)
    _BEST_ANNOUNCEMENT_TASK.start()
    _RESET_LIMIT_TASK.start()


def isMeme(attachment: discord.Attachment) -> bool:
    return is_image(attachment.url) or is_video(attachment.url)


def is_image(attachment_url: str) -> bool:
    formatList = ["jpg", "jpeg", "JPG", "JPEG", "png", "PNG", "gif", "gifv"]
    fileFormat = get_attachment_format(attachment_url)
    return any(fileFormat.startswith(format) for format in formatList)


def is_video(attachment_url: str) -> bool:
    formatList = ["webm", "mp4", "wav", "mov"]
    fileFormat = get_attachment_format(attachment_url)
    return any(fileFormat.startswith(format) for format in formatList)


def get_attachment_format(attachment_url: str) -> bool:
    fileUrl = attachment_url.split("?")[0]
    fileFormat = fileUrl.split(".")[-1]
    return fileFormat


def getUser(message):
    return message.embeds[0].description[2:-1]


async def check_meme(message, guild, channel, memeChannel):
    try:
        # if message is not a meme
        if len(message.attachments) == 0 or not isMeme(message.attachments[0]) or message.channel.id != channel.id:
            return

        # if author already sent a meme
        with shelve.open("./database/meme_leaderboard.db") as memeLeaderboard:
            if (
                memeLeaderboard.get(str(message.author.id)) is not None
                and memeLeaderboard[str(message.author.id)][1] >= 1
            ):
                await message.channel.send("Meme not counted. Only one meme a day, <@" + str(message.author.id) + ">")
                return False

            # Count it as meme. Struct: [Memer Score, Daily Meme Count]
            if memeLeaderboard.get(str(message.author.id)) is None:
                memeLeaderboard[str(message.author.id)] = [0, 1]
            else:
                memeLeaderboard[str(message.author.id)] = [
                    memeLeaderboard[str(message.author.id)][0],
                    memeLeaderboard[str(message.author.id)][1] + 1,
                ]

        embed = discord.Embed(description="<@" + str(message.author.id) + ">")
        embed.set_image(url=message.attachments[0].url)
        if is_video(message.attachments[0].url):
            await memeChannel.send(content=message.attachments[0].url)
        memeMessage = await memeChannel.send(embed=embed)

        # Add reactions
        for emoji in guild.emojis:
            if emoji.name == notMeme:
                await memeMessage.add_reaction(emoji)
                break
        for emoji in guild.emojis:
            if emoji.name == badMeme:
                await memeMessage.add_reaction(emoji)
                break
        for emoji in guild.emojis:
            if emoji.name == ehMeme:
                await memeMessage.add_reaction(emoji)
                break
        for emoji in guild.emojis:
            if emoji.name == goodMeme:
                await memeMessage.add_reaction(emoji)
                break
        for emoji in guild.emojis:
            if emoji.name == bestMeme:
                await memeMessage.add_reaction(emoji)
                break

        # Structure of list is: GoodMemeCount, isNotMeme, [memeAuthorName, memeAuthorId], memeLink
        with shelve.open("./database/meme_review.db") as memeDatabase:
            memeDatabase[str(memeMessage.id)] = [0, True, message.author.id, message.attachments[0].url]

    except Exception as e:
        await message.channel.send("Error Checking Meme: " + str(e))


async def add_meme_reactions(payload, channel, guild, adminRole):
    try:
        payloadUser = guild.get_member(payload.user_id)

        payloadEmoji = payload.emoji
        if isinstance(payload.emoji, str):
            payloadEmoji = payload.emoji.name

        # If the message is not a meme or the bot added the reaction or the reaction is not valid, leave
        isValidEmote = (
            isNotMemeReaction(payloadEmoji) or isGoodMemeReaction(payloadEmoji) or isBadMemeReaction(payloadEmoji)
        )
        if payloadUser.bot or not isValidEmote or payload.channel_id != channel.id:
            return isValidEmote

        message = await channel.fetch_message(payload.message_id)
        if not isMeme(message.embeds[0].image):
            return isValidEmote

        # check if reactor is Admin or is the sender of the meme
        isAdmin = str(payload.user_id) == getUser(message)
        for member in adminRole.members:
            if member.id == payload.user_id:
                isAdmin = True

        with shelve.open("./database/meme_review.db") as memeDatabase:
            if memeDatabase.get(str(message.id)) is None:
                memeDatabase[str(message.id)] = [0, True, getUser(message), message.embeds[0].image.url]

        # These emotes don't count towards the leaderboard
        # if isGoodMemeReaction(payloadEmoji) or isBadMemeReaction(payloadEmoji):
        #    s = shelve.open('./database/weekly_georgechamp_shelf.db')
        #    s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')
        #    emoteKey = None
        #    if payload.emoji.is_custom_emoji():
        #        emoteKey = "<:" + payload.emoji.name + ":" + str(payload.emoji.id) + ">"
        #    elif payload.emoji.is_unicode_emoji():
        #        emoteKey = payload.emoji.name
        #    s_all_time[emoteKey] -= 1
        #    s[emoteKey] -= 1
        #    s.close()
        #    s_all_time.close()

        # check whether the message is a considered a meme
        for reaction in message.reactions:
            reactionEmoji = reaction.emoji
            if isinstance(reactionEmoji, str):
                reactionEmoji = reaction.emoji.name
            if isNotMemeReaction(reactionEmoji):
                # If the Admin is reacting "Not A Meme", leave
                if reactionEmoji == payloadEmoji and isAdmin:
                    with shelve.open("./database/meme_review.db") as memeDatabase:
                        # Reduce daily meme by 1
                        if memeDatabase[str(message.id)][1] is True:
                            with shelve.open("./database/meme_leaderboard.db") as memeLeaderboard:
                                if memeLeaderboard.get(getUser(message)) is None:
                                    memeLeaderboard[getUser(message)] = [0, -1]
                                else:
                                    memeLeaderboard[getUser(message)] = [
                                        memeLeaderboard[getUser(message)][0],
                                        memeLeaderboard[getUser(message)][1] - 1,
                                    ]
                        memeDatabase[str(message.id)] = addToDatabase(memeDatabase[str(message.id)], 1, False)

                    return isValidEmote
                # If the  message is considered "Not A Meme", remove payloadReaction
                elif reaction.count > 1:
                    await message.remove_reaction(payload.emoji, payloadUser)
                    return isValidEmote

        if isGoodMemeReaction(payloadEmoji):
            with shelve.open("./database/meme_review.db") as memeDatabase:
                memeDatabase[str(message.id)] = addToDatabase(
                    memeDatabase[str(message.id)], 0, memeDatabase[str(message.id)][0] + getScore(payloadEmoji)
                )
        elif not isBadMemeReaction(payloadEmoji):
            await channel.send("Error adding meme reaction (1)")

        # Adding points for reacting
        if isGoodMemeReaction(payloadEmoji) or isBadMemeReaction(payloadEmoji):
            with shelve.open("./database/meme_leaderboard.db") as memeLeaderboard:
                if memeLeaderboard.get(str(payload.user_id)) is None:
                    memeLeaderboard[str(payload.user_id)] = [1, 0]
                else:
                    memeLeaderboard[str(payload.user_id)] = [
                        memeLeaderboard[str(payload.user_id)][0] + 1,
                        memeLeaderboard[str(payload.user_id)][1],
                    ]

        for reaction in message.reactions:
            reactionEmoji = reaction.emoji
            if isinstance(reactionEmoji, str):
                reactionEmoji = reaction.emoji.name
            if isGoodMemeReaction(reactionEmoji) or isBadMemeReaction(reactionEmoji):
                sameUser = False
                async for user in reaction.users():
                    sameUser = sameUser or (user.id == payload.user_id)
                # if user alredy voted before, replace the previous emote with current one
                if reactionEmoji != payloadEmoji and sameUser:
                    await message.remove_reaction(reaction.emoji, payloadUser)
                # can't react to your own meme
                if reactionEmoji == payloadEmoji and str(payload.user_id) == getUser(message):
                    await message.remove_reaction(reaction.emoji, payloadUser)

        return isValidEmote

    except Exception as e:
        await channel.send("Error adding meme reactions: " + str(e))
        return True


async def remove_meme_reactions(payload, channel):
    try:
        payloadEmoji = payload.emoji
        if isinstance(payload.emoji, str):
            payloadEmoji = payload.emoji.name

        # If the message is not a meme or the bot added the reaction or the reaction is not valid, leave
        isValidEmote = (
            isNotMemeReaction(payloadEmoji) or isGoodMemeReaction(payloadEmoji) or isBadMemeReaction(payloadEmoji)
        )
        if not isValidEmote or payload.channel_id != channel.id:
            return

        message = await channel.fetch_message(payload.message_id)
        if not isMeme(message.embeds[0].image):
            return

        notMemeReaction = None
        for reaction in message.reactions:
            notMemeReaction = reaction.emoji
            if isinstance(notMemeReaction, str):
                notMemeReaction = reaction.emoji.name
            if isNotMemeReaction(notMemeReaction):
                notMemeReaction = reaction
                break

        # Remove 1 Point for reacting
        if (isGoodMemeReaction(payloadEmoji) or isBadMemeReaction(payloadEmoji)) and (
            notMemeReaction is not None and notMemeReaction.count <= 1
        ):
            with shelve.open("./database/meme_leaderboard.db") as memeLeaderboard:
                if memeLeaderboard.get(str(payload.user_id)) is None:
                    memeLeaderboard[str(payload.user_id)] = [-1, 0]
                else:
                    memeLeaderboard[str(payload.user_id)] = [
                        memeLeaderboard[str(payload.user_id)][0] - 1,
                        memeLeaderboard[str(payload.user_id)][1],
                    ]

        # Reduce Emote count
        # s = shelve.open('./database/weekly_georgechamp_shelf.db')
        # s_all_time = shelve.open('./database/all_time_georgechamp_shelf.db')
        # emoteKey = None
        # if payload.emoji.is_custom_emoji():
        #     emoteKey = "<:" + payload.emoji.name + ":" + str(payload.emoji.id) + ">"
        # elif payload.emoji.is_unicode_emoji():
        #     emoteKey = payload.emoji.name
        # s_all_time[emoteKey] -= 1
        # s[emoteKey] -= 1
        # s.close()
        # s_all_time.close()

        with shelve.open("./database/meme_review.db") as memeDatabase:
            if memeDatabase.get(str(message.id)) is None:
                memeDatabase[str(message.id)] = [0, True, getUser(message), message.embeds[0].image.url]
            if isGoodMemeReaction(payloadEmoji):
                memeDatabase[str(message.id)] = addToDatabase(
                    memeDatabase[str(message.id)], 0, memeDatabase[str(message.id)][0] - getScore(payloadEmoji)
                )
            elif isNotMemeReaction(payloadEmoji) and notMemeReaction is not None and notMemeReaction.count <= 1:
                # Reduce number of daily meme by 1
                if not memeDatabase[str(message.id)][1]:
                    with shelve.open("./database/meme_leaderboard.db") as memeLeaderboard:
                        if memeLeaderboard.get(getUser(message)) is None:
                            memeLeaderboard[getUser(message)] = [0, 1]
                        else:
                            memeLeaderboard[getUser(message)]
                            memeLeaderboard[getUser(message)] = [
                                memeLeaderboard[getUser(message)][0],
                                memeLeaderboard[getUser(message)][1] + 1,
                            ]
                memeDatabase[str(message.id)] = addToDatabase(memeDatabase[str(message.id)], 1, True)

    except Exception as e:
        await channel.send("Error removing meme reactions: " + str(e))


def isNotMemeReaction(inputEmoji):
    return inputEmoji == notMeme


def isBadMemeReaction(inputEmoji):
    return inputEmoji == badMeme


def isGoodMemeReaction(inputEmoji):
    return inputEmoji in [ehMeme, goodMeme, bestMeme]


def addToDatabase(memeDatabase, index, value):
    tempDatabase = memeDatabase[:index]
    tempDatabase.append(value)
    tempDatabase += memeDatabase[(index + 1) :]
    return tempDatabase


def getScore(inputEmoji):
    if inputEmoji == ehMeme:
        return 1
    if inputEmoji == goodMeme:
        return 2
    if inputEmoji == bestMeme:
        return 4


async def best_announcement_task(channel, deleteAfter=None):
    try:
        with (
            shelve.open("./database/meme_review.db") as memeDatabase,
            shelve.open("./database/meme_leaderboard.db") as memeLeaderboard,
        ):
            shelf_as_dict = dict(memeDatabase)

            if len(shelf_as_dict) == 0:
                await channel.send("No memes this week. :sadkek:")
                return

            sorted_database = sorted(shelf_as_dict.items(), key=lambda item: item[1][0], reverse=True)
            points = [75, 50, 30, 15, 5]
            i = 0
            for meme1 in sorted_database:
                meme = meme1[1]
                if meme[1]:
                    if i < 5 and deleteAfter is None:
                        if memeLeaderboard.get(str(meme[2])) is None:
                            memeLeaderboard[str(meme[2])] = [points[i], 0]
                        else:
                            memeLeaderboard[str(meme[2])] = [
                                memeLeaderboard[str(meme[2])][0] + points[i],
                                memeLeaderboard[str(meme[2])][1],
                            ]
                    i += 1
            sendMsg = (
                "Memer of the Week: :first_place:"
                + "<@"
                + str(sorted_database[0][1][2])
                + "> "
                + " :partying_face::partying_face::partying_face:\n"
            )
            if len(sorted_database) >= 2:
                sendMsg += "Second Place: :second_place:" + "<@" + str(sorted_database[1][1][2]) + "> " + "\n"
            if len(sorted_database) >= 3:
                sendMsg += "Third Place: :third_place:" + "<@" + str(sorted_database[2][1][2]) + "> " + "\n"
            embed = discord.Embed(title="Best Meme:")
            embed.set_image(url=sorted_database[0][1][3])
            if is_video(sorted_database[0][1][3]):
                sendMsg += "Best Meme:\n" + sorted_database[0][1][3]
                await channel.send(content=sendMsg, delete_after=deleteAfter)
            else:
                await channel.send(sendMsg, delete_after=deleteAfter, embed=embed)

            if deleteAfter is None:
                memeDatabase.clear()
    except Exception as e:
        await channel.send("Error Printing Best Meme of the Week: " + str(e))


async def get_memerboard_text(page: int, guild) -> str:
    try:
        with shelve.open("./database/meme_leaderboard.db") as memeLeaderboard:
            shelf_as_dict = dict(memeLeaderboard)
            sorted_memers = sorted(shelf_as_dict.items(), key=operator.itemgetter(1), reverse=True)

            page = max(1, page)
            start = (page - 1) * 5
            end = start + 5

            page_slice = sorted_memers[start:end]
            total_page_num = math.ceil(len(memeLeaderboard) / 5) if len(memeLeaderboard) else 1

            if len(page_slice) == 0:
                return "Doesn't look like there are memers here :( Try another page."

            leaderboard_msg = "Meme Leaderboard\nMemer - Points \n"
            for i in range(5):
                if i < len(page_slice):
                    placement = start + i + 1
                    displayedMember = await guild.fetch_member(int(page_slice[i][0]))
                    displayedName = (
                        displayedMember.nick if displayedMember.nick is not None else displayedMember.display_name
                    )
                    leaderboard_msg = (
                        leaderboard_msg
                        + str(placement)
                        + ". "
                        + displayedName
                        + " - "
                        + str(page_slice[i][1][0])
                        + "\n"
                    )
            leaderboard_msg += "Page " + str(page) + "/" + str(int(total_page_num))
            return leaderboard_msg
    except Exception as e:
        return f"Error Printing Leaderboard: {e}"


async def resetLimit():
    with shelve.open("./database/meme_leaderboard.db") as memeLeaderboard:
        for memer in memeLeaderboard:
            memeLeaderboard[memer] = [memeLeaderboard[memer][0], 0]
