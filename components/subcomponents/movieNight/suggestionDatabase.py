'''
A class to allow adding, removing and listing movie suggestions persistent using shelve library
Each entry in the database consists of:
    - Discord Member Name (str) as its key
    - List of Movies (list[Movies]) as its value
'''
import shelve
import discord
from .movie import Movie

CONST_MAX_SUGGESTIONS = 10

class Suggestions:
    def __init__(self, database_path):
        self.database_path = database_path

    def has_space(self, member: str) -> bool:
        db = shelve.open(self.database_path)
        has_space = False

        if db.get(member) is None or len(db[member]) < CONST_MAX_SUGGESTIONS:
            has_space = True
        db.close()

        return has_space

    def get_movie(self, member: str, movie_name: str) -> Movie | None:
        db = shelve.open(self.database_path)
        movie = None

        if db.get(member):
            movie = next((movie for movie in db[member] if movie.name == movie_name), None)
        db.close()

        return movie

    # If number of suggestions must be limited, then use has_space() before add_suggestion()
    def add_suggestion(self, member:str, suggested_movie: Movie) -> discord.Embed:
        # Update Database
        db = shelve.open(self.database_path)
        if db.get(member) is None:
            db[member] = [suggested_movie]
        else:
            db[member] = db[member] + [suggested_movie]
        db.close()

        # Reply using Embed
        reply = embed_movie(suggested_movie)
        reply.title="Movie successfully added to " + member + "'s list !"
        return reply

    def remove_suggestion(self, member:str, movie_name: str) -> discord.Embed:
        reply = discord.Embed(colour= 0x4f4279)

        movie = self.get_movie(member, movie_name)
        if movie:
            db = shelve.open(self.database_path)
            new_suggestion_list = db.get(member)
            new_suggestion_list.remove(movie)
            db[member] = new_suggestion_list
            db.close()

            reply = embed_movie(movie)
            reply.title="Movie Successfully Removed from " + member + "'s list !"
        else:
            reply.title="Removal Unsuccessful!"
            reply.description = "The movie `" + movie_name + "` was not found in " + member + "'s suggestion list."

        return reply

    def get_suggestion_names(self, member:str) -> [str]:
        db = shelve.open(self.database_path)

        suggested_movies_names = []
        if db.get(member):
            suggested_movies = db[member]
            suggested_movies_names = [movie.name for movie in suggested_movies]
        db.close()

        return suggested_movies_names

    def get_suggestions_embed(self, member:str) -> discord.Embed:
        reply = discord.Embed(colour= 0x4f4279)

        suggested_movies_names = self.get_suggestion_names(member)
        if suggested_movies_names:
            reply.title = member + "'s Suggestion List"
            reply.description = "\n".join(suggested_movies_names)
        else:
            reply.title = "Movies not found!"
            reply.description = member + "'s suggestion list is empty."

        return reply

    def get_suggestion_embed(self, member:str, movie_name: str) -> discord.Embed:
        reply = discord.Embed(colour= 0x4f4279)

        movie = self.get_movie(member, movie_name)
        if movie:
            reply = embed_movie(movie)
            reply.title = member + "'s Suggestion"
        else:
            reply.title = "Movie not found!"
            reply.description = "The movie `" + movie_name + "` was not found in " + member + "'s suggestion list."

        return reply

# Generic title; change it after
def embed_movie(movie: Movie) -> discord.Embed:
    embed = discord.Embed(colour= 0x4f4279)
    embed.title = "Movie Suggestion"
    embed.description = "**Name:** " + movie.name
    embed.description += "\n**Genre:** " + movie.genre
    embed.description += "\n**Reason for Picking:** " + movie.picking_reason
    return embed
