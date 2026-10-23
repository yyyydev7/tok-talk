package com.toktalk.auth;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

final class AuthConfigTest {
    @Test
    void readsSecurityDefaults() {
        var config = AuthConfig.fromEnvironment(requiredEnvironment());
        assertEquals("simple-auth-server", config.jwtIssuer());
        assertEquals("tok-talk-api", config.jwtAudience());
        assertEquals(Duration.ofMinutes(15), config.accessTokenTtl());
    }

    @Test
    void rejectsShortSecret() {
        var environment = requiredEnvironment();
        environment.put("JWT_SECRET", "short");
        assertThrows(IllegalArgumentException.class, () -> AuthConfig.fromEnvironment(environment));
    }

    private static Map<String, String> requiredEnvironment() {
        var environment = new HashMap<String, String>();
        environment.put("JWT_SECRET", "test-secret-that-is-at-least-thirty-two-bytes-long");
        environment.put("DB_USER", "test");
        environment.put("DB_PASSWORD", "test");
        return environment;
    }
}
