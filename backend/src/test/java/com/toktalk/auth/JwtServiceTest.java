package com.toktalk.auth;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;

final class JwtServiceTest {
    private static final String SECRET = "test-secret-that-is-at-least-thirty-two-bytes-long";
    private static final Instant NOW = Instant.parse("2026-10-23T00:00:00Z");

    @Test
    void issuesAndVerifiesRequiredClaims() {
        var service = service(SECRET, "issuer", "audience", NOW);
        var claims = service.verify(service.issue("alice"));

        assertEquals("alice", claims.getSubject());
        assertEquals("issuer", claims.getIssuer());
        assertEquals(NOW, claims.getIssuedAt().toInstant());
        assertEquals(NOW.plusSeconds(900), claims.getExpiration().toInstant());
    }

    @Test
    void rejectsExpiredToken() {
        String token = service(SECRET, "issuer", "audience", NOW).issue("alice");
        var later = service(SECRET, "issuer", "audience", NOW.plusSeconds(901));
        assertThrows(ExpiredJwtException.class, () -> later.verify(token));
    }

    @Test
    void rejectsTokenIssuedInTheFuture() {
        String token = service(SECRET, "issuer", "audience", NOW.plusSeconds(60)).issue("alice");
        assertThrows(IllegalArgumentException.class,
                () -> service(SECRET, "issuer", "audience", NOW).verify(token));
    }

    @Test
    void rejectsWrongSignatureIssuerAndAudience() {
        String token = service(SECRET, "issuer", "audience", NOW).issue("alice");
        assertThrows(JwtException.class, () -> service(
                "different-secret-that-is-at-least-thirty-two-bytes", "issuer", "audience", NOW).verify(token));
        assertThrows(JwtException.class, () -> service(SECRET, "wrong", "audience", NOW).verify(token));
        assertThrows(JwtException.class, () -> service(SECRET, "issuer", "wrong", NOW).verify(token));
    }

    @Test
    void rejectsShortSecret() {
        assertThrows(IllegalArgumentException.class,
                () -> new JwtService("short", "issuer", "audience", Duration.ofMinutes(15)));
    }

    @Test
    void verifiesTokenProducedByPythonService() {
        String pythonToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                + "eyJzdWIiOiJpbnRlcm9wLXVzZXIiLCJpc3MiOiJzaW1wbGUtYXV0aC1zZXJ2ZXIiLCJhdWQiOiJ0b2stdGFsay1hcGkiLCJpYXQiOjE3OTI3MTM2MDAsImV4cCI6MTc5MjcxNDUwMCwianRpIjoiaW50ZXJvcC10b2tlbi1pZCJ9."
                + "EfLSXNQ7sQYD388yLJsTKk828lZhoVD-69lVjMjNow4";
        var verifier = service(SECRET, "simple-auth-server", "tok-talk-api", NOW);
        assertEquals("interop-user", verifier.verify(pythonToken).getSubject());
    }

    private static JwtService service(String secret, String issuer, String audience, Instant now) {
        return new JwtService(secret, issuer, audience, Duration.ofMinutes(15),
                Clock.fixed(now, ZoneOffset.UTC));
    }
}
