
def format_result(success = 1, message = None, result = None, status = None):
    ret = {
        "success": success,
        "message": {
            "errorMsg": message
        },
        "data": {
            "status": status,
            "result": result
        }
    }

    return ret