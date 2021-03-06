import os
import ast
import json

from math import ceil
from datetime import datetime

from flask import Flask, render_template, send_from_directory, flash, request, redirect, url_for, abort, jsonify, Response
from log import app, db
from models import Item, ItemForm, NewItemForm
from helpers import *
from flask.ext.login import login_required, current_user
from urlparse import urljoin
from werkzeug.contrib.atom import AtomFeed
from mongoengine import ValidationError

items_per_page = app.config['ITEMS_PER_PAGE']
post_types = app.config['POST_TYPES']
log_title = app.config['TITLE']
items_in_feed = app.config['ITEMS_IN_NEWSFEED']
author = app.config['AUTHOR']
year = app.config['CURRENT_YEAR']

@app.errorhandler(404)
def error_not_found(e):
    return render_template('error.html', code=404), 404


@app.errorhandler(500)
def error_server(e):
    return render_template('error.html', code=500), 500


# http://flask.pocoo.org/snippets/10/
# Validated using http://feedvalidator.org/docs/howto/install_and_run.html
@app.route('/feed')
def feed_atom():
    feed = AtomFeed(log_title, feed_url=request.url, url=request.url_root)
    items = Item.objects[0:items_in_feed].order_by('-posted')
    for item in items:
        feed.add(item.title, 
                 unicode(item.content),
                 content_type='html',
                 published=item.posted,
                 updated=item.posted,
                 author=author,
                 id="tag:" + log_title + "," + year + ":/" + str(item.id) + "/")
    return feed.get_response()


@app.route('/type/<string:post_type>')
def search_by_type(post_type=None):
    if post_type in [ short_type for short_type, long_type in post_types]:
        return render_template("index.html", items=Item.objects(post_type__exact = post_type))
    else:
        abort(404)
    

@app.route('/tag/<tagname>')
@app.route('/tags/<tagname>')
def search_by_tags(tagname=None):
    tag_list = tagname.strip().split("+")
    return render_template("index.html", items=Item.objects(tags__in = tag_list))


@app.route('/post', methods=['GET', 'POST'])
def form_post():
    """ Show the form to post items. Perhaps the only form on the site...
    """

    # Can use the @login_required decorator as well
    # http://pythonhosted.org/Flask-Login/#protecting-views
    if not current_user.is_authenticated():
        flash("I'm sorry Jane, I cannot let you do that. Want to log in?", "error")
        return redirect(url_for("index"))

    form = NewItemForm()
    if request.method == 'POST' and form.validate():
        item = Item(title=request.form['title'],
                    content=request.form['content'],
                    post_type=request.form['post_type'],
                    tags=request.form['hidden-tags'].split(','),
                    posted=datetime.now())
        item.save()
        flash('Saved item', 'success')
        return redirect(url_for("index")) # There's a reason why this is used instead of "/"
    return render_template("forms/post.html", form=form)


@app.route('/item/<string:post_id>')
def item(post_id):
    try:
        item = Item.objects.get(id__exact = post_id)   
    except Item.DoesNotExist, e:
        abort(404)
    except Item.MultipleObjectsReturned, e:
        abort(500)
    except ValidationError, e:
        abort(500)
    else:
        return render_template("item.html", item=Item.objects.get(id__exact = post_id))


@app.route('/page/<int:page_number>')
@app.route('/page')
@app.route('/')
@app.route('/index')
def index(page_number=1):
    """ Display a paginated home page of items, ordered by posting date.
        Implement this when you understand it fully:
        http://flask.pocoo.org/snippets/44/
    """
    # Clean up the page number. I found out that Python's 'pass-by-object'
    # when writing this simple method and my head's a little... shaken.
    page_number = enforce_integer(page_number)

    # Quick calculations for pagination
    number_of_items = Item.objects().count()
    number_of_pages = int(ceil(number_of_items / float(items_per_page)))
    start = (page_number - 1) * items_per_page
    end = start + items_per_page

    # Use array splicing (docs-recommended over start() and limit())
    # to paginate results
    return render_template("index.html",
                           items=Item.objects[start:end].order_by('-posted'), **locals())


@app.route('/favicon.ico')
def favicon():
    """ Send the favicon.
    """
    return send_from_directory(os.path.join(app.root_path, 'static/img'),
                               'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')
