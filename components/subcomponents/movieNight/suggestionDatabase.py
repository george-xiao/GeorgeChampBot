'''
A class to allow adding, removing and listing movie suggestions persistent using shelve library
Each entry in the database consists of:
    - Discord Member Name (str) as its key
    - List of Movies (list[Movies]) as its value
'''
import discord
from common.orderedShelve import OrderedShelve
from .movie import Movie

CONST_MAX_SUGGESTIONS = 10

class Suggestions:
    def __init__(self, database_path):
        self.shelve = OrderedShelve(database_path)

    def has_space(self, member: str) -> bool:
        db = self.shelve.open()
        has_space = False

        if db.get(member) is None or len(db[member]) < CONST_MAX_SUGGESTIONS:
            has_space = True
        self.shelve.close(db)

        return has_space

    def get_members(self) -> [str]:
        db = self.shelve.open()
        members = list(db.keys())
        self.shelve.close(db)

        return members

    def get_movie(self, member: str, movie_name: str) -> Movie | None:
        db = self.shelve.open()
        movie = None

        movies = db.get(member)
        if movies:
            movie = next((movie for movie in movies if movie.name == movie_name), None)
        self.shelve.close(db)

        return movie

    # If number of suggestions must be limited, then use has_space() before add_suggestion()
    def add_suggestion(self, member:str, suggested_movie: Movie) -> discord.Embed:
        # Update Database
        db = self.shelve.open()
        if db.get(member) is None:
            db[member] = [suggested_movie]
        else:
            db[member] = db[member] + [suggested_movie]
        self.shelve.close(db)

        # Reply using Embed
        reply = self.__embed_movie(suggested_movie)
        reply.title="Movie successfully added to " + member + "'s list !"
        return reply

    def remove_suggestion(self, member:str, movie_name: str) -> discord.Embed:
        reply = discord.Embed(colour= 0x4f4279)

        movie = self.get_movie(member, movie_name)
        if movie:
            db = self.shelve.open()
            new_suggestion_list = db.get(member)
            new_suggestion_list.remove(movie)
            db[member] = new_suggestion_list
            self.shelve.close(db)

            reply = self.__embed_movie(movie)
            reply.title="Movie Successfully Removed from " + member + "'s list !"
        else:
            reply.title="Removal Unsuccessful!"
            reply.description = "The movie `" + movie_name + "` was not found in " + member + "'s suggestion list."

        return reply

    def get_suggestion_names(self, member:str) -> [str]:
        db = self.shelve.open()

        suggested_movies_names = []
        suggested_movies = db.get(member)
        if suggested_movies:
            suggested_movies_names = [movie.name for movie in suggested_movies]
        self.shelve.close(db)

        return suggested_movies_names

    def get_list_embed(self) -> discord.Embed:
        reply = discord.Embed(colour= 0x4f4279)

        members = self.get_members()
        if members:
            reply.title = "Suggestion List"
            reply.description = ""
            for member in members:
                # Format list
                suggested_names_str = ", ".join(self.get_suggestion_names(member))
                reply.description += "**" + member + "**: " + suggested_names_str + "\n"
        else:
            reply.title = "Movies not found!"
            reply.description = "Everyone's suggestion list is empty."

        return reply

    def get_suggestion_embed(self, member:str, movie_name: str) -> discord.Embed:
        reply = discord.Embed(colour= 0x4f4279)

        movie = self.get_movie(member, movie_name)
        if movie:
            reply = self.__embed_movie(movie)
            reply.title = member + "'s Suggestion"
        else:
            reply.title = "Movie not found!"
            reply.description = "The movie `" + movie_name + "` was not found in " + member + "'s suggestion list."

        return reply

    # Bumps member to the end of the shelve
    def bump_member(self, member: str) -> bool:
        successful = False
        db = self.shelve.open()
        movies = db.get(member)

        if movies:
            del db[member]
            db[member] = movies
            successful = True
        self.shelve.close(db)

        return successful

    # Embedded message has a generic title; change it after
    def __embed_movie(self, movie: Movie) -> discord.Embed:
        embed = discord.Embed(colour= 0x4f4279)
        embed.title = "Movie Suggestion"
        embed.description = "**Name:** " + movie.name
        embed.description += "\n**Genre:** " + movie.genre
        embed.description += "\n**Reason for Picking:** " + movie.picking_reason
        return embed
