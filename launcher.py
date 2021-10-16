import uvicorn

from app import Server, init_environment

init_environment()

server = Server()

if __name__ == '__main__':
    uvicorn.run(server.web_app, host='0.0.0.0', port=12345)
else:
    web_app = server.web_app
