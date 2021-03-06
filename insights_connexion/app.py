import asyncio
from .config import config
import connexion
from connexion.resolver import RestyResolver
from connexion.decorators.response import ResponseValidator
from connexion.decorators.validation import RequestBodyValidator
from connexion.exceptions import NonConformingResponseBody, NonConformingResponseHeaders
from .db import gino as db
import json
# from jsonschema import ValidationError
# from .logger import log
# from sqlalchemy.exc import IntegrityError
# from sqlalchemy.orm.exc import NoResultFound
from . import util, responses


# By default validate_response will return the full stack trace to the client.
# This will instead return a simple 500
class CustomResponseValidator(ResponseValidator):
    def validate_response(self, data, status_code, headers, url):
        try:
            super().validate_response(data, status_code, headers, url)
        except(NonConformingResponseBody, NonConformingResponseHeaders):
            raise Exception()


# This enables a custom error message for invalid request bodies to be sent to the client.
class RequestBodyValidator(RequestBodyValidator):
    def validate_schema(self, data, url):
        if self.is_null_value_valid and connexion.utils.is_null(data):
            return None
        self.validator.validate(data)


validator_map = {
    'response': CustomResponseValidator,
    'body': RequestBodyValidator
}
debug = util.string_to_bool(config.debug)

app = connexion.AioHttpApp('__main__',
                           specification_dir='swagger/',
                           validator_map=validator_map,
                           debug=debug)
app.add_api('api.spec.yaml',
            resolver=RestyResolver('api'),
            validate_responses=True,
            strict_validation=True,
            pass_context_arg_name='request')


def exists_handler(exception):
    return responses.resource_exists()


def no_result_handler(exception):
    return responses.not_found()


def validation_error_handler(exception):
    return responses.invalid_request_parameters()


# app.add_error_handler(NoResultFound, no_result_handler)
# app.add_error_handler(IntegrityError, exists_handler)
# app.add_error_handler(ValidationError, validation_error_handler)

application = app.app


# @application.teardown_appcontext
# def shutdown_session(exception=None):
# session.remove()


def _parse_headers(dict_in):
    return json.dumps(
        {k: v for k, v in dict_in})


def _parse_params(params):
    return params.to_dict(flat=False)


# @application.before_request
# def before_req():
    # log.info(msg={'headers': _parse_headers(connexion.request.headers),
    # 'params': _parse_params(connexion.request.args),
    # 'body': connexion.request.json,
    # 'url': connexion.request.url,
    # 'method': connexion.request.method})


# @application.after_request
# def after_req(res):
    # log.info(msg={'status_code': res.status_code,
    # 'headers': _parse_headers(res.headers),
    # 'content_type': res.content_type,
    # 'mimetype': res.mimetype,
    # 'body': res.get_json()})
    # return res


@asyncio.coroutine
async def setup_app(app):
    await db.init()
    app['db'] = db
    return app


def start():
    app_copy = app.app
    app.app = setup_app(app_copy)
    app.run(port=int(config.port))
