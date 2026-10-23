package com.toktalk.auth;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.UnsupportedJwtException;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import java.util.Set;
import java.util.UUID;
import javax.crypto.SecretKey;

final class JwtService {
    private static final Set<String> REQUIRED_CLAIMS = Set.of("sub", "iss", "aud", "iat", "exp", "jti");
    private final SecretKey key;
    private final String issuer;
    private final String audience;
    private final Duration ttl;
    private final Clock clock;

    JwtService(String secret, String issuer, String audience, Duration ttl) {
        this(secret, issuer, audience, ttl, Clock.systemUTC());
    }

    JwtService(String secret, String issuer, String audience, Duration ttl, Clock clock) {
        byte[] bytes = secret.getBytes(StandardCharsets.UTF_8);
        if (bytes.length < 32) throw new IllegalArgumentException("JWT secret must be at least 32 bytes");
        this.key = Keys.hmacShaKeyFor(bytes);
        this.issuer = issuer;
        this.audience = audience;
        this.ttl = ttl;
        this.clock = clock;
    }

    String issue(String username) {
        Instant now = clock.instant();
        return Jwts.builder().subject(username).issuer(issuer)
                .audience().add(audience).and()
                .issuedAt(Date.from(now)).expiration(Date.from(now.plus(ttl)))
                .id(UUID.randomUUID().toString())
                .signWith(key, Jwts.SIG.HS256).compact();
    }

    Claims verify(String token) {
        var parsed = Jwts.parser().verifyWith(key).requireIssuer(issuer)
                .requireAudience(audience).clock(() -> Date.from(clock.instant()))
                .build().parseSignedClaims(token);
        if (!"HS256".equals(parsed.getHeader().getAlgorithm())) {
            throw new UnsupportedJwtException("Only HS256 is accepted");
        }
        Claims claims = parsed.getPayload();
        if (!claims.keySet().containsAll(REQUIRED_CLAIMS)
                || claims.getSubject() == null || claims.getSubject().isBlank()
                || claims.getId() == null || claims.getId().isBlank()) {
            throw new IllegalArgumentException("JWT is missing a required claim");
        }
        if (claims.getIssuedAt().toInstant().isAfter(clock.instant())) {
            throw new IllegalArgumentException("JWT issued-at time is in the future");
        }
        return claims;
    }
}
