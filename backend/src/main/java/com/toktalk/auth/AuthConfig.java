package com.toktalk.auth;

import java.time.Duration;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

record AuthConfig(int port, String jwtSecret, String jwtIssuer, String jwtAudience,
        Duration accessTokenTtl, boolean secureCookie, Set<String> corsOrigins,
        String jdbcUrl, String dbUser, String dbPassword) {

    static AuthConfig fromEnvironment(Map<String, String> env) {
        int port = integer(env, "PORT", 8080, 1, 65535);
        int ttlSeconds = integer(env, "JWT_ACCESS_TTL_SECONDS", 900, 60, 86_400);
        String secret = required(env, "JWT_SECRET");
        if (secret.getBytes(java.nio.charset.StandardCharsets.UTF_8).length < 32) {
            throw new IllegalArgumentException("JWT_SECRET must be at least 32 bytes");
        }
        String host = env.getOrDefault("DB_HOST", "127.0.0.1");
        int dbPort = integer(env, "DB_PORT", 3306, 1, 65535);
        String dbName = env.getOrDefault("DB_NAME", "tok_talk");
        String jdbcUrl = "jdbc:mariadb://" + host + ":" + dbPort + "/" + dbName
                + "?useUnicode=true&characterEncoding=utf8";
        return new AuthConfig(port, secret,
                env.getOrDefault("JWT_ISSUER", "simple-auth-server"),
                env.getOrDefault("JWT_AUDIENCE", "tok-talk-api"),
                Duration.ofSeconds(ttlSeconds),
                Boolean.parseBoolean(env.getOrDefault("COOKIE_SECURE", "false")),
                parseOrigins(env.getOrDefault("CORS_ORIGINS", "http://localhost:5174")),
                jdbcUrl, required(env, "DB_USER"), required(env, "DB_PASSWORD"));
    }

    private static Set<String> parseOrigins(String value) {
        Set<String> origins = java.util.Arrays.stream(value.split(","))
                .map(String::trim).filter(origin -> !origin.isEmpty())
                .collect(Collectors.toUnmodifiableSet());
        if (origins.isEmpty()) throw new IllegalArgumentException("CORS_ORIGINS must not be empty");
        return origins;
    }

    private static String required(Map<String, String> env, String name) {
        String value = env.get(name);
        if (value == null || value.isBlank()) throw new IllegalArgumentException(name + " must be set");
        return value;
    }

    private static int integer(Map<String, String> env, String name, int fallback, int min, int max) {
        String value = env.get(name);
        if (value == null || value.isBlank()) return fallback;
        try {
            int parsed = Integer.parseInt(value);
            if (parsed < min || parsed > max) throw new NumberFormatException();
            return parsed;
        } catch (NumberFormatException exception) {
            throw new IllegalArgumentException(name + " must be between " + min + " and " + max, exception);
        }
    }
}
