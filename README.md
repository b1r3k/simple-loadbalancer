## Problem description

Create a load balancing server to handle HTTP requests and distribute them to microservices. The server should offer the following endpoints:

    /register: Receives parameters for URL path, IP address, and port. Upon receiving this request, the load balancer will start sending requests to the corresponding microservice.

Requests to other endpoints are forwarded to microservices based on a Round Robin load balancing scheme. Replies are then sent back to the client.

Example:

Microservice A registers: http://<load balancer>/register "/test", ip address, port
Microservice B registers: http://<load balancer>/register "/test2", ip address, port
Microservice C registers: http://<load balancer>/register "/test", ip address, port
Microservice D registers: http://<load balancer>/register "/test", ip address, port

When a client calls http://<load balancer>/test, the request will be forwarded to either A, C, or D.

Guidelines:

- Time limit: 50 minutes
- Focus on load balancer code; microservices implementation is not required.
- Emphasize code structure, readability, and production-ready quality.
- In-memory data structures (no need for a database).
- You can use any Python web framework you're comfortable with (but **do not** use Django)

## Howto

### Run

1. Make sure you have poetry installed and pyenv wouldn't hurt too
2. Install dependencies: `make install`
3. Start async based solution: `make run-async`

### Test

1. Register target

```bash
curl -i -L -X POST \
   -H "Content-Type:application/json" \
   -d \
'{
  "ip_address": "99.83.207.200",
  "port": 80
}' \
 'http://localhost:8000/register'
```

2. Send request

```bash
curl -i -L -X GET 'http://localhost:8000/hello/world'
```
