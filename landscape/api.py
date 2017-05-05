from landscape import app, db
from landscape.models import User, Widget, WidgetType
from flask import request, jsonify, abort, session, url_for
from flask_login import logout_user, login_user, login_required
from sqlalchemy.sql import or_


@app.route('/api/v01/login', methods=['POST'], endpoint='api_login')
def api_login():
    username = request.json['username']
    password = request.json['password']
    registered_user = User.query.filter(or_(User.username == username, User.email == username),
                                        User.password == User.encode_password(password)).first()
    if registered_user is None:
        abort(status=401)  # 401 Unauthorized
    login_user(registered_user)
    return jsonify({'success': True})


@app.route('/api/v01/logout', methods=['GET'], endpoint='api_logout')
@login_required
def api_logout():
    logout_user()
    return jsonify({'success': True})


@app.route('/api/v01/user/<user_id>/widget/<widget_id>', methods=['GET', 'DELETE'], endpoint='api_widget')
@login_required
def api_widget(user_id, widget_id):
    if str(session['user_id']) != user_id:  # ok you are logged but you are not god!
        return abort(status=403)
    if request.method == 'GET':
        widget = Widget.query.filter_by(user_id=user_id, id=widget_id).first()
        if widget is not None:
            return jsonify({'widget': widget.to_dict()})
        return abort(status=404)

    if request.method == 'DELETE':
        widget = Widget.query.filter_by(user_id=user_id, id=widget_id).first()
        db.session.delete(widget)
        db.session.commit()
        return jsonify({'widget': widget.to_dict(limited=True)})


@app.route('/api/v01/user/<user_id>/widgets', methods=['GET', 'CREATE', 'POST'], endpoint='api_widgets')
@login_required
def api_widgets(user_id):
    if str(session['user_id']) != user_id:  # ok you are logged but you are not god!
        return abort(status=403)
    # return the widgets configured (if GET)
    if request.method == 'GET':
        db_widgets = Widget.query.filter_by(user_id=session['user_id']).all()
        widgets = []
        for w in db_widgets:
            d = w.to_dict(limited=True)
            d['url'] = url_for('api_widget', user_id=session['user_id'], widget_id=w.id, _external=True)
            widgets.append(d)
        return jsonify({'widgets': widgets})
    # update the widgets (if POST)
    if request.method == 'POST':
        db_widgets = Widget.query.filter_by(user_id=session['user_id']).all()
        db_widgets = {w.id: w for w in db_widgets}
        for widget in request.json['widgets']:
            try:
                db_widget = db_widgets[int(widget['i'])]
            except (KeyError, ValueError):
                app.logger.warning('unknown widget (possible threat): %s for %s', widget['i'], session['user_id'])
                continue
            db_widget.x = widget['x']
            db_widget.y = widget['y']
            db_widget.height = widget['h']
            db_widget.width = widget['w']
        db.session.commit()
        return jsonify({'success': True})

    # create a new widget (if CREATE)
    if request.method == 'CREATE':
        coord = Widget.new_coordinates(session['user_id'])
        if request.form['type'] == str(WidgetType.FEED.value):
            widget = Widget(type=WidgetType.FEED, user_id=session['user_id'], uri=request.form['url'],
                            title=request.form['title'], refresh_freq=request.form.get('freq', 60), **coord)
        else:
            return abort(status=422, description='Invalid type')

        db.session.add(widget)
        db.session.commit()
        return jsonify({'success': True, 'widget': widget.to_dict(limited=True)})