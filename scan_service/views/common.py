from flask import make_response

def build_reponse(args):
    reponse = make_response(args)
    reponse.headers["Content-Type"] = "application/json"
    return reponse