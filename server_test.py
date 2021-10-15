from wsgiref.simple_server import make_server

class Server:

    def run_server(self, app_instance):

        self.app_instance = app_instance

        with make_server('', 8000, self.app_instance) as server:
            print("Serving on Port 8000...")
            server.serve_forever()