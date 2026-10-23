package com.toktalk.auth;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import io.jsonwebtoken.JwtException;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.URLDecoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Executors;
import org.mindrot.jbcrypt.BCrypt;

/** Account authentication server and JWT issuer. */
public final class Main {
    private static final String ACCESS_COOKIE = "ACCESS_TOKEN";
    private static String dummyPasswordHash;
    private static AuthConfig config;
    private static JwtService jwt;
    private static UserRepository users;

    private Main() {}

    public static void main(String[] args) throws IOException, SQLException {
        int healthPort = readHealthcheckPort();
        if (args.length == 1 && args[0].equals("--healthcheck")) {
            System.exit(checkLiveness(healthPort));
            return;
        }
        if (args.length != 0) throw new IllegalArgumentException("Supported argument: --healthcheck");

        config = AuthConfig.fromEnvironment(System.getenv());
        jwt = new JwtService(config.jwtSecret(), config.jwtIssuer(), config.jwtAudience(), config.accessTokenTtl());
        users = new UserRepository(config.jdbcUrl(), config.dbUser(), config.dbPassword());
        users.ensureSchema();
        dummyPasswordHash = BCrypt.hashpw("not-a-real-password", BCrypt.gensalt(12));

        var server = HttpServer.create(new InetSocketAddress("0.0.0.0", config.port()), 0);
        var executor = Executors.newVirtualThreadPerTaskExecutor();
        server.setExecutor(executor);
        server.createContext("/", Main::handleRequest);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> { server.stop(1); executor.close(); }));
        server.start();
        System.out.printf("tok-talk-auth listening on 0.0.0.0:%d%n", config.port());
    }

    private static void handleRequest(HttpExchange exchange) throws IOException {
        try {
            addCorsHeaders(exchange);
            if (exchange.getRequestMethod().equals("OPTIONS")) {
                exchange.getResponseHeaders().set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
                exchange.getResponseHeaders().set("Access-Control-Allow-Headers", "Content-Type");
                exchange.sendResponseHeaders(204, -1);
                return;
            }
            if (exchange.getRequestMethod().equals("POST") && !hasAllowedOrigin(exchange)) {
                respond(exchange, 403, "{\"error\":\"forbidden_origin\"}");
                return;
            }
            String path = exchange.getRequestURI().getPath();
            if (path.equals("/health/live")) {
                requireMethod(exchange, "GET");
                respond(exchange, 200, "{\"service\":\"auth\",\"status\":\"alive\"}");
                return;
            }
            if (path.equals("/health")) {
                requireMethod(exchange, "GET");
                respond(exchange, 200, "{\"service\":\"auth\",\"status\":\"ready\",\"auth_ready\":true}");
                return;
            }
            if (path.equals("/api/signup")) { requireMethod(exchange, "POST"); signup(exchange); return; }
            if (path.equals("/api/login")) { requireMethod(exchange, "POST"); login(exchange); return; }
            if (path.equals("/api/auth/check")) { requireMethod(exchange, "GET"); checkAuth(exchange); return; }
            if (path.equals("/api/logout")) { requireMethod(exchange, "POST"); logout(exchange); return; }
            respond(exchange, 404, "{\"error\":\"not_found\"}");
        } catch (MethodNotAllowed ignored) {
            // Response was already sent.
        } catch (SQLException exception) {
            System.err.println("Database operation failed: SQLState=" + exception.getSQLState());
            respond(exchange, 503, "{\"error\":\"database_unavailable\"}");
        } catch (IllegalArgumentException exception) {
            respond(exchange, 400, "{\"error\":\"invalid_request\"}");
        } finally {
            exchange.close();
        }
    }

    private static void signup(HttpExchange exchange) throws IOException, SQLException {
        var form = readForm(exchange);
        String username = validUsername(form.get("username"));
        String password = validPassword(form.get("password"));
        boolean created = users.create(username, BCrypt.hashpw(password, BCrypt.gensalt(12)));
        if (!created) { respond(exchange, 409, "{\"error\":\"username_exists\"}"); return; }
        exchange.getResponseHeaders().set("Location", "/login");
        respond(exchange, 302, "{\"ok\":true}");
    }

    private static void login(HttpExchange exchange) throws IOException, SQLException {
        var form = readForm(exchange);
        String username = validUsername(form.get("username"));
        String password = validPassword(form.get("password"));
        var hash = users.passwordHash(username);
        boolean passwordMatches = BCrypt.checkpw(password, hash.orElse(dummyPasswordHash));
        if (hash.isEmpty() || !passwordMatches) {
            respond(exchange, 401, "{\"error\":\"invalid_credentials\"}");
            return;
        }
        exchange.getResponseHeaders().add("Set-Cookie", accessCookie(jwt.issue(username)));
        respond(exchange, 200, "{\"ok\":true,\"redirect\":\"/\"}");
    }

    private static void checkAuth(HttpExchange exchange) throws IOException {
        String token = cookie(exchange, ACCESS_COOKIE);
        if (token == null) { unauthorized(exchange); return; }
        try {
            String subject = jwt.verify(token).getSubject();
            String escaped = json(subject);
            respond(exchange, 200, "{\"ok\":true,\"via\":\"jwt\",\"username\":\""
                    + escaped + "\",\"sub\":\"" + escaped + "\"}");
        } catch (JwtException | IllegalArgumentException exception) {
            unauthorized(exchange);
        }
    }

    private static void logout(HttpExchange exchange) throws IOException {
        exchange.getResponseHeaders().add("Set-Cookie", clearCookie());
        exchange.getResponseHeaders().set("Location", "/login");
        respond(exchange, 302, "{\"ok\":true}");
    }

    private static Map<String, String> readForm(HttpExchange exchange) throws IOException {
        String type = exchange.getRequestHeaders().getFirst("Content-Type");
        if (type == null || !type.toLowerCase().startsWith("application/x-www-form-urlencoded")) {
            throw new IllegalArgumentException("form content type required");
        }
        byte[] bytes = exchange.getRequestBody().readNBytes(8193);
        if (bytes.length > 8192) throw new IllegalArgumentException("form too large");
        Map<String, String> form = new HashMap<>();
        for (String pair : new String(bytes, StandardCharsets.UTF_8).split("&")) {
            String[] parts = pair.split("=", 2);
            if (parts.length == 2) form.put(decode(parts[0]), decode(parts[1]));
        }
        return form;
    }

    private static String validUsername(String value) {
        if (value == null || !value.matches("[A-Za-z0-9._-]{3,64}"))
            throw new IllegalArgumentException("invalid username");
        return value;
    }

    private static String validPassword(String value) {
        if (value == null || value.length() < 12 || value.length() > 128)
            throw new IllegalArgumentException("invalid password");
        return value;
    }

    private static String accessCookie(String token) {
        return ACCESS_COOKIE + "=" + token + "; Path=/; Max-Age=" + config.accessTokenTtl().toSeconds()
                + "; HttpOnly; SameSite=Strict" + (config.secureCookie() ? "; Secure" : "");
    }

    private static String clearCookie() {
        return ACCESS_COOKIE + "=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"
                + (config.secureCookie() ? "; Secure" : "");
    }

    private static String cookie(HttpExchange exchange, String name) {
        for (String header : exchange.getRequestHeaders().getOrDefault("Cookie", java.util.List.of())) {
            for (String item : header.split(";")) {
                String[] parts = item.trim().split("=", 2);
                if (parts.length == 2 && parts[0].equals(name)) return parts[1];
            }
        }
        return null;
    }

    private static void addCorsHeaders(HttpExchange exchange) {
        String origin = exchange.getRequestHeaders().getFirst("Origin");
        if (origin != null && config.corsOrigins().contains(origin)) {
            exchange.getResponseHeaders().set("Access-Control-Allow-Origin", origin);
            exchange.getResponseHeaders().set("Access-Control-Allow-Credentials", "true");
            exchange.getResponseHeaders().set("Vary", "Origin");
        }
    }

    private static boolean hasAllowedOrigin(HttpExchange exchange) {
        String origin = exchange.getRequestHeaders().getFirst("Origin");
        return origin == null || config.corsOrigins().contains(origin);
    }

    private static void requireMethod(HttpExchange exchange, String expected) throws IOException {
        if (!exchange.getRequestMethod().equals(expected)) {
            exchange.getResponseHeaders().set("Allow", expected);
            respond(exchange, 405, "{\"error\":\"method_not_allowed\"}");
            throw new MethodNotAllowed();
        }
    }

    private static void unauthorized(HttpExchange exchange) throws IOException {
        exchange.getResponseHeaders().add("Set-Cookie", clearCookie());
        respond(exchange, 401, "{\"error\":\"unauthorized\"}");
    }

    private static String decode(String value) { return URLDecoder.decode(value, StandardCharsets.UTF_8); }
    private static String json(String value) { return value.replace("\\", "\\\\").replace("\"", "\\\""); }

    private static void respond(HttpExchange exchange, int status, String bodyText) throws IOException {
        byte[] body = bodyText.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.getResponseHeaders().set("Cache-Control", "no-store");
        exchange.sendResponseHeaders(status, body.length);
        exchange.getResponseBody().write(body);
    }

    private static int readHealthcheckPort() {
        try { return Integer.parseInt(System.getenv().getOrDefault("PORT", "8080")); }
        catch (NumberFormatException exception) { return 8080; }
    }

    private static int checkLiveness(int port) {
        try (var client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build()) {
            var request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/health/live"))
                    .timeout(Duration.ofSeconds(3)).GET().build();
            return client.send(request, HttpResponse.BodyHandlers.discarding()).statusCode() == 200 ? 0 : 1;
        } catch (InterruptedException exception) { Thread.currentThread().interrupt(); return 1; }
        catch (IOException exception) { return 1; }
    }

    private static final class MethodNotAllowed extends RuntimeException {}
}
