from fastapi.responses import JSONResponse
import copy

RESPONSES = {
    "read_only": {
        "status": 403,
        "message": "Forbidden",
        "details": "The archive is in read-only mode. Try again later or contact the archive's administrator."
    },

    "wrong_content_type": {
        "status": 400,
        "message": "Bad Request",
        "details": "The file uploaded does not meet the expected MIME type."
    },

    "no_api_key": {
        "status": 401,
        "message": "Unauthorized",
        "details": "You need an API key to access this endpoint."
    },

    "invalid_api_key": {
        "status": 403,
        "message": "Forbidden",
        "details": "The provided API key is not valid."
    },

    "insufficient_permissions": {
        "status": 403,
        "message": "Forbidden",
        "details": "You lack the required permissions to perform this action."
    },

    "blacklisted": {
        "status": 403,
        "message": "Forbidden",
        "details": "Your IP address has been blacklisted. Try again later or contact the archive's administrator."
    },

    "disabled_feature": {
        "status": 403,
        "message": "Forbidden",
        "details": "This feature has been disabled."
    },

    "not_in_archive": {
        "status": 404,
        "message": "Not Found",
        "details": "The media requested was not found it the archive."
    },

    "not_found": {
        "status": 404,
        "message": "Not Found",
        "details": "The requested URL was not found on this server."
    },

    "already_exists": {
        "status": 409,
        "message": "Exists",
        "details": "The resource you're trying to create already exists."
    },

    "resource_created": {
        "status": 201,
        "message": "Created",
        "details": "Resource has been successfully created."
    },

    "resource_updated": {
        "status": 200,
        "message": "OK",
        "details": "Resource has been successfully updated."
    },

    "upload_succeeded": {
        "status": 200,
        "message": "OK",
        "details": "Your file has been added to the archive."
    },

    "little_teapot": {
        "status": 418,
        "message": "I'm a Teapot",
        "details": "The server refuses to brew coffee, for it is, and always shall be, a teapot."
    },
}


def respond(response_code: str, **kwargs):
    """
    Give the client a detailed response from a template

    :param response_code: The code to respond with. e.g. 'resource_created'
    :param kwargs: Data to append to the response under the `extra` field.
    :return:
    """
    content = copy.copy(RESPONSES[response_code])

    content['code'] = response_code

    if kwargs:
        # noinspection PyTypeChecker
        content['extra'] = kwargs

    resp = JSONResponse(
        content=content,
        status_code=content['status']
    )
    return resp
