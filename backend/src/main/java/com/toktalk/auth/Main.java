package com.toktalk.auth;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.Executors;

/** Java 인증 서버의 실행 골격. 인증과 데이터베이스 연결은 아직 구현하지 않는다. */
public final class Main {
    private Main() {}

    public static void main(String[] args) throws IOException {
        int port = readPort();
        if (args.length == 1 && args[0].equals("--healthcheck")) {
            System.exit(checkLiveness(port));
            return;
        }
        if (args.length != 0) {
            throw new IllegalArgumentException("Supported argument: --healthcheck");
        }
        var server = HttpServer.create(new InetSocketAddress("0.0.0.0", port), 0);
        var executor = Executors.newVirtualThreadPerTaskExecutor();
        server.setExecutor(executor);
        server.createContext("/", Main::handleRequest);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.stop(1);
            executor.close();
        }));

        server.start();
        System.out.printf("tok-talk-auth listening on 0.0.0.0:%d (authentication not implemented)%n", port);
    }

    private static int checkLiveness(int port) {
        try (var client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build()) {
            var request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/health/live"))
                    .timeout(Duration.ofSeconds(3))
                    .GET()
                    .build();
            var response = client.send(request, HttpResponse.BodyHandlers.discarding());
            return response.statusCode() == 200 ? 0 : 1;
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            return 1;
        } catch (IOException exception) {
            return 1;
        }
    }

    private static int readPort() {
        String value = System.getenv().getOrDefault("PORT", "8080");
        try {
            int port = Integer.parseInt(value);
            if (port < 1 || port > 65535) {
                throw new NumberFormatException();
            }
            return port;
        } catch (NumberFormatException exception) {
            throw new IllegalArgumentException("PORT must be an integer between 1 and 65535", exception);
        }
    }

    private static void handleRequest(HttpExchange exchange) throws IOException {
        try (exchange) {
            String path = exchange.getRequestURI().getPath();
            if (!path.equals("/health/live") && !path.equals("/health")) {
                respond(exchange, 404, "{\"error\":\"not_found\"}");
                return;
            }
            if (!exchange.getRequestMethod().equals("GET")) {
                exchange.getResponseHeaders().set("Allow", "GET");
                respond(exchange, 405, "{\"error\":\"method_not_allowed\"}");
                return;
            }
            if (path.equals("/health/live")) {
                respond(exchange, 200, "{\"service\":\"auth\",\"status\":\"alive\"}");
                return;
            }
            respond(exchange, 503,
                    "{\"service\":\"auth\",\"status\":\"not_ready\",\"auth_ready\":false,"
                            + "\"reason\":\"authentication_not_implemented\"}");
        }
    }

    private static void respond(HttpExchange exchange, int status, String json) throws IOException {
        byte[] body = json.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.getResponseHeaders().set("Cache-Control", "no-store");
        exchange.sendResponseHeaders(status, body.length);
        exchange.getResponseBody().write(body);
    }
}
