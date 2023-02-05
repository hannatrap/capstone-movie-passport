import os

from flask import Flask, render_template, request, flash, redirect, session, g, abort
import random
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
import requests
from forms import UserAddForm, LoginForm, EditUserForm, NewPlaylistForm, LikeAddForm
from models import db, connect_db, User, Playlist, Playlist_Movies

CURR_USER_KEY = "curr_user"
# API_KEY = "43cfb6f4"
API_BASE_URL = "http://www.omdbapi.com/?apikey=43cfb6f4&/"

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///movie-passport1'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

app.debug=True



with app.app_context():
    connect_db(app)
    db.create_all()


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )

            db.session.add(user)
            db.session.commit()


        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)
        flash('Successfully Created Your Account! Welcome to Movie Passport!', "success")

        return redirect("/")

    else:
        flash('TRY AGAIN!', "success")
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""
        
    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)



@app.route('/logout')
def logout():
    """Handle logout of user."""
    do_logout()

    flash("You have successfully logged out of Warbler", 'success')

    return redirect('/login')


    # IMPLEMENT THIS


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging playlists in order from the database;
    # user.playlist won't be in order by default
    playlist = (Playlist
                .query
                .filter(Playlist.user_id == user_id)
                .limit(5)
                .all())
    
    return render_template('users/show.html', user=user, playlist=playlist)





@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""
    # IMPLEMENT THIS

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    user = g.user
    form = EditUserForm(obj=user)
   


    if form.validate_on_submit():
        if User.authenticate(user.username, form.password.data):
            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data or "/static/images/default-pic.png"
            # user.header_image_url = form.header_image_url.data or "/static/images/warbler-hero.jpg"
            # user.bio = form.bio.data

            db.session.commit()
            return redirect(f"/users/{user.id}")

        flash("Incorrect password, please try again", 'danger')

    return render_template('users/edit.html', form=form, user_id=user.id)
        

@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Playlists routes:

@app.route('/playlists/new', methods=["GET", "POST"])
def playlists_add():
    """Add a playlist:

    Show form if GET. If valid, update playlist and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = NewPlaylistForm()
    user = g.user
    if form.validate_on_submit():
        playlists = Playlist(playlist_name=form.playlist_name.data, playlist_about=form.playlist_about.data,)
        user.playlists.append(playlists)
        db.session.add(playlists)
        db.session.commit()

        return redirect(f"/users/{user.id}")

    return render_template('playlists/new.html', form=form)


@app.route('/playlists/<id>', methods=["GET"])
def show_playlist_details(id):
    """Show a specific playlist."""

    playlist = Playlist.query.get_or_404(id)

    p_movie_ids = [x.movie_id for x in playlist.movies]
    p_movies = []
    # for each movie in the playlist
    for m_id in p_movie_ids:
        # appending each movie details into the list variable
        movie = requests.get(f"{API_BASE_URL}", params={"i":m_id}).json()        
        p_movies.append(movie)
        

    return render_template('playlists/show.html', playlist = playlist, playlist_movies = p_movies, movie=movie)


@app.route('/playlists/add/<playlist_id>/<movie_id>', methods=['GET'])
def add_movie_to_playlist(playlist_id, movie_id):
    # print('something is happening')
    
    pm = Playlist_Movies(playlist_id = playlist_id, movie_id=movie_id)

    db.session.add(pm)
    db.session.commit()
    return redirect(f"/playlists/{playlist_id}")


@app.route('/playlists/delete/<playlist_id>/<movie_id>', methods=['POST'])
def remove_movie_from_playlist(playlist_id, movie_id):
    # print('something is happening')
    
    playlist = Playlist.query.get_or_404(playlist_id)
    
    pm = Playlist_Movies.query.filter_by(playlist_id = playlist_id, movie_id=movie_id).first()

    if g.user.id != playlist.user_id:
        return render_template('/404.html')

    db.session.delete(pm)
    db.session.commit()
    return redirect(f"/playlists/{playlist_id}")



@app.route('/users/<int:user_id>/playlists', methods=["GET"])
def list_user_playlists(user_id):
    """Show a playlist."""
    
    user = User.query.get_or_404(user_id)

    playlist = (Playlist
                .query
                .filter(Playlist.user_id == user_id))
    
    return render_template('users/playlists.html', playlist=playlist, user=user)


@app.route('/playlists', methods=["GET"])
def playlists_show_all():
    """Show a playlist."""
    user = g.user
    playlists = Playlist.query.all()
    return render_template('playlists/index.html', playlists=playlists, user=user)

##############################################################################
# Movie pages

@app.route('/movies/search_results', methods=['GET'])
def show_search_results():

    """Logic for sending an API request and displaying the JSON response as an HTML. Expects a GET request."""
    
    movies = []
    s = request.args.get("s")

    if not s:

        return redirect('/')

    else:
        results = requests.get(f"{API_BASE_URL}search/movies/",params={"s": s}).json()

        results = results['Search']

        for movie in results:
            id = movie['imdbID']
            movies.append(movie)
            

    return render_template('movies/search_results.html',movies=movies, s=s, id=id)



@app.route('/movies/<id>')
def show_movie_details(id):
    """For displaying information about the individual movie. Not a list. GET request only."""
    
    # getting the movie information from API and storing into variable
    movie = requests.get(f"{API_BASE_URL}", params={"i":id}).json()
    # rendering a template and passing the json version of the results, also passing the genres and the page number
    id = movie['imdbID']
    return render_template('movies/detail.html', movie = movie, id = id)
    
 

##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    """
    playlists = Playlist.query.all()

    if g.user:

        playlist = (Playlist
                .query
                .filter(Playlist.user_id != g.user.id))
        # liked_playlist_ids = [playlist.id for playlist in g.user.likes]

        return render_template('home.html', playlist=playlist, playlists=playlists)

    else:
        return render_template('home-anon.html')


@app.errorhandler(404)
def page_not_found(e):
    """404 NOT FOUND page."""

    return render_template('404.html'), 404

##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req



# def get_movie_information():
#     """Retrieve movie information from api"""
#     q = request.args.get("s")
#     results = requests.get(f"{API_BASE_URL}/search/movies",params={"s": q}).json()

#     for movie in results:
#         movie = Movie(id = movie['imdbID'], title = movie['Title'], released = ['Year'])

#     db.session.commit()
