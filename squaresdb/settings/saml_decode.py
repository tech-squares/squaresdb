#!/usr/bin/python

import base64
import sys
import urllib
import zlib

# Based on https://lists.oasis-open.org/archives/saml-dev/200910/msg00003.html

def decode_authn_request(authn_request):
    """ AuthnRequest is always deflated, base64 encoded and url-escaped.

    :Parameters:
    -`authn_request`: AuthnRequest

    :Return:
     The decoded AuthnRequest if successful else empty string.
    """
    decoded = ''
    a = urllib.unquote(authn_request)
    a = a.strip('SAMLRequest=')
    try:
         decoded = zlib.decompress(base64.b64decode(a), -8)
    except (zlib.error, TypeError):
        try:
             decoded = zlib.decompress(base64.b64decode(a))
        except (zlib.error, TypeError):
             pass
    return decoded

if __name__ == '__main__':
    print(decode_authn_request(sys.stdin.read()))
