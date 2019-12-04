from flask import request, Blueprint

bp = Blueprint('practice', __name__, url_prefix='/practice')

@bp.route('/get', methods=['GET'])
def get_bird():
    media_type = request.args.get("media", "images", str)
    addons = request.args.get("addon", "", str)
    bw = bool(request.args.get("bw", False, int))
    session_id = request.args.get("session_id", None, int)
    return {"media":media_type, "addons":addons, "bw":bw, "session":session_id}

@bp.route('/check', methods=['GET'])
def check_bird():
    bird_guess = request.args.get("guess", "", str)
    return {"bird_guess": bird_guess}

@bp.route('/skip', methods=['GET'])
def skip_bird():

    return {"success": 200}

@bp.route('/hint', methods=['GET'])
def hint_bird():

    return {"success": 200}