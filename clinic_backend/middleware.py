from django.http import HttpResponse

class CustomCorsMiddleware:
    """ 
    Ensures CORS headers (Access-Control-Allow-Origin, Methods, Headers) 
    are attached to all API responses and OPTIONS preflight requests.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get("HTTP_ORIGIN") or request.headers.get("Origin") or "*"

        if request.method == "OPTIONS":
            response = HttpResponse("", content_type="text/plain", status=200)
        else:
            response = self.get_response(request)

        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, X-Requested-With, Origin, X-CSRFToken, Access-Control-Request-Method, Access-Control-Request-Headers"
        return response
