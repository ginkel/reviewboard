import logging

from django.conf import settings
from django.contrib import auth

from reviewboard.admin.checks import check_updates_required
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.admin.views import manual_updates_required
from reviewboard.webapi.json import service_not_configured


class LoadSettingsMiddleware:
    """
    Middleware that loads the settings on each request.
    """
    def process_request(self, request):
        # Load all site settings.
        load_site_config()


class CheckUpdatesRequiredMiddleware:
    """
    Middleware that checks if manual updates need to be made on the
    installation. If updates are required, all attempts to access a
    URL will be redirected to the updates page (or an appropriate
    error response for API calls.
    """
    def process_request(self, request):
        """
        Checks whether updates are required and returns the appropriate
        response if they are.
        """
        path_info = request.META['PATH_INFO']

        if (check_updates_required() and
            not path_info.startswith(settings.MEDIA_URL)):
            if path_info.startswith(settings.SITE_ROOT + "api/"):
                return service_not_configured(request)

            return manual_updates_required(request)

        # Let another handler handle this.
        return None


class X509AuthMiddleware(object):
    """
    Middleware that authenticates a user using the environment variables set by
    mod_ssl.

    Apache needs to be configured with mod_ssl. For Review Board to be usable
    with x.509 client certificate authentication, the 'SSLVerifyClient'
    configuration directive should be set to 'optional'. This will ensure that
    basic authentication will still work, allowing the post-review tool to work
    with a username and password.
    """
    def process_request(self, request):
        # @todo Determine if this middleware should be optional. Not every
        #       deployment using SSL to serve Review Board will have a Public
        #       Key Infrastructure, so that might make sense. Leaving it
        #       enabled shouldn't hurt, though.
        if not request.is_secure():
            return None

        requestType = request.__class__.__name__

        if requestType == 'WSGIRequest':
            env = request.environ
        elif requestType == 'ModPythonRequest':
            env = request._req.subprocess_env
        else:
            # Unknown request type; bail out gracefully.
            logging.error("X509AuthMiddleware: unknown request type '%s'" %
                    requestType)
            env = {}

        x509_field = env.get(str(getattr(settings, 'X509_USERNAME_FIELD',
            None)))

        if x509_field:
            user = auth.authenticate(x509_field=x509_field)

            if user:
                request.user = user
                auth.login(request, user)

        return None
