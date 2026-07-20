from django.http import HttpResponse

class CustomCorsMiddleware:
    """ 
    Ensures CORS headers (Access-Control-Allow-Origin, Methods, Headers) 
    are attached to all API responses and OPTIONS preflight requests.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "*")
        
        if request.method == "OPTIONS":
            response = HttpResponse()
            response.status_code = 200
        else:
            response = self.get_response(request)

        response["Access-Control-Allow-Origin"] = origin if origin else "*"
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, X-Requested-With, Origin, X-CSRFToken"
        return response
