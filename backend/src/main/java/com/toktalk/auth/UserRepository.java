package com.toktalk.auth;

import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.SQLIntegrityConstraintViolationException;
import java.util.Optional;

final class UserRepository {
    private final String jdbcUrl;
    private final String dbUser;
    private final String dbPassword;

    UserRepository(String jdbcUrl, String dbUser, String dbPassword) {
        this.jdbcUrl = jdbcUrl;
        this.dbUser = dbUser;
        this.dbPassword = dbPassword;
    }

    void ensureSchema() throws SQLException {
        try (var connection = DriverManager.getConnection(jdbcUrl, dbUser, dbPassword);
             var statement = connection.createStatement()) {
            statement.executeUpdate("""
                    CREATE TABLE IF NOT EXISTS auth_users (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(64) NOT NULL UNIQUE,
                        password_hash VARCHAR(100) NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
                    """);
        }
    }

    boolean create(String username, String passwordHash) throws SQLException {
        try (var connection = DriverManager.getConnection(jdbcUrl, dbUser, dbPassword);
             var statement = connection.prepareStatement(
                     "INSERT INTO auth_users (username, password_hash) VALUES (?, ?)")) {
            statement.setString(1, username);
            statement.setString(2, passwordHash);
            statement.executeUpdate();
            return true;
        } catch (SQLIntegrityConstraintViolationException duplicate) {
            return false;
        }
    }

    Optional<String> passwordHash(String username) throws SQLException {
        try (var connection = DriverManager.getConnection(jdbcUrl, dbUser, dbPassword);
             var statement = connection.prepareStatement(
                     "SELECT password_hash FROM auth_users WHERE username = ?")) {
            statement.setString(1, username);
            try (var result = statement.executeQuery()) {
                return result.next() ? Optional.of(result.getString(1)) : Optional.empty();
            }
        }
    }
}
