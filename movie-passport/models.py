"""SQLAlchemy models for Warbler."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()



# class Movie(db.Model):

#     __tablename__ = "movies"


#     title = db.Column(db.Text, nullable=False, primary_key=True)
#     year = db.Column(db.Integer, nullable=False)


    # # Map to clubs through reads
    # clubs = db.relationship('Club', secondary="reads", backref="books")
    # # Map directly to reads (important for finding whether this is the current book or not)
    # reads = db.relationship('Read', overlaps="books,clubs", cascade="all, delete-orphan")

    # # Map directly to notes so you can see the notes a on each book
    # notes = db.relationship('Note', backref="books")

class Likes(db.Model):
    """Mapping user likes to warbles."""

    __tablename__ = 'likes' 

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
    )
    # playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id', ondelete="CASCADE"))



class User(db.Model):
    """User in the system."""

    __tablename__ = 'users'
    
    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    username = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )
    email = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )
    first_name = db.Column(
        db.Text,
        nullable=False,
    )
    last_name = db.Column(
        db.Text,
        nullable=False,
    )

    image_url = db.Column(
        db.Text,
        default="/static/images/default-pic.png",
    )


    password = db.Column(
        db.Text,
        nullable=False,
    )

    playlists = db.relationship('Playlist')

    likes = db.relationship(
        'Likes'
    )

    @classmethod
    def signup(cls, username, email, password, first_name, last_name, image_url):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=hashed_pwd,
            image_url=image_url,
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False


class Playlist(db.Model):
    """An individual playlist"""

    __tablename__ = 'playlists'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    playlist_name = db.Column(
        db.String,
        nullable=False,
    )

    playlist_about = db.Column(
        db.String,
        nullable=False,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )

    user = db.relationship('User')

    movies = db.relationship('Playlist_Movies', cascade='all,delete')



class Playlist_Movies(db.Model):
    """movie to playlist map"""

    __tablename__ = 'playlist_movies'

    id = db.Column(
        db.Integer, 
        autoincrement=True, 
        primary_key=True
        )

    playlist_id = db.Column(
        db.Integer, 
        db.ForeignKey('playlists.id', ondelete="CASCADE")
        ) 

    movie_id = db.Column(db.String, nullable=False)




def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)
