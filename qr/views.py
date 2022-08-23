import base64
from io import BytesIO

import redis

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse, NoReverseMatch
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response

from qr.utils import salted_hash, generate_random_string, make_qr_code

QR_CODE_EXPIRATION_TIME = getattr(settings, "QR_CODE_EXPIRATION_TIME", 120)
QR_CODE_REDIS_KWARGS = getattr(settings, "QR_CODE_REDIS_KWARGS", {})
QR_CODE_HASH_LENGTH = getattr(settings, "QR_CODE_HASH_LENGTH", 50)


def uses_redis(func):
    def wrapper(*args, **kwargs):
        kwargs["redis"] = redis.StrictRedis(**QR_CODE_REDIS_KWARGS)
        return func(*args, **kwargs)
    return wrapper


class QrCodeAPIMixin:
    REDIRECT_URL_NAME = ''

    @method_decorator(uses_redis)
    def get(self, request, *args, **kwargs):
        redis_storage = kwargs['redis']

        current_site = get_current_site(request)
        scheme = request.is_secure() and "https" or "http"
        code_hash = salted_hash(generate_random_string(QR_CODE_HASH_LENGTH))

        try:
            redirect_link = f"{scheme}://{current_site.domain}{reverse(self.REDIRECT_URL_NAME, args=(code_hash,))}"
        except NoReverseMatch:
            return Response({'message': 'Redirect url is not found.'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user.id if hasattr(request.user, 'id') else None  # Anonymous user will have id -1
        redis_storage.hmset(f"qr_{code_hash}", QR_CODE_EXPIRATION_TIME, {'user_id': user_id,
                                                                         'redirect_url_name': self.REDIRECT_URL_NAME})

        buffered = BytesIO()
        img = make_qr_code(redirect_link)
        img.save(buffered, format="PNG")
        img_data = base64.b64encode(buffered.getvalue())
        return Response({'qr': img_data}, status=status.HTTP_200_OK)


class QrCodeConfirmAPIMixin:
    @method_decorator(uses_redis)
    def get(self, request, *args, **kwargs):
        redis_storage = kwargs['redis']
        code_hash = request.query_params.get('code_hash')

        qr_data = redis_storage.hgetall(f"qr_{code_hash}")

        # Process not existed QR
        if not qr_data:
            return Response(status=status.HTTP_404_NOT_FOUND)

        qr_user_id = qr_data.get('user_id', None)
        redirect_url_name = qr_data.get('redirect_url_name', None)

        # Process QR with wrong redirect url
        if redirect_url_name != '':
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Process anonymous QR with anonymous user
        if not qr_user_id and hasattr(request.user, 'id'):
            return self.get_successful_response(request, qr_user_id, *args, is_login=False, **kwargs)

        # Process anonymous QR with authenticated user
        if not qr_user_id and hasattr(request.user, 'id'):
            return self.get_successful_response(request, qr_user_id, *args, is_login=True, **kwargs)

        # Process user QR with anonymous user
        if qr_user_id > 0 and not hasattr(request.user, 'id'):
            return self.get_successful_response(request, qr_user_id, *args, is_login=True, **kwargs)

        # Process user QR with the same authenticated user
        if qr_user_id > 0 and hasattr(request.user, 'id') and qr_user_id == request.user.id:
            return self.get_successful_response(request, qr_user_id, *args, is_login=False, **kwargs)

        # Process user QR with another authenticated user
        if qr_user_id > 0 and hasattr(request.user, 'id') and qr_user_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def get_successful_response(self, request, qr_user_id, *args, **kwargs):
        # Process login
        if kwargs.get('is_login', False):
            response_data = self.confirm_qr_login(request, qr_user_id, *args, **kwargs)
            if not response_data:
                raise SyntaxError("You need to override `confirm_qr_login` method.")
            return Response(status=status.HTTP_200_OK, data=response_data)
        # Process other confirmation
        if self.confirm_qr_code(request, qr_user_id, *args, **kwargs):
            return Response(status=status.HTTP_200_OK)
        raise SyntaxError("You need to override `confirm_qr_code` method.")

    def confirm_qr_code(self, request, qr_user_id, *args, **kwargs):
        return False

    def confirm_qr_login(self, request, qr_user_id, *args, **kwargs):
        return False
