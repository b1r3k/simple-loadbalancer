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
