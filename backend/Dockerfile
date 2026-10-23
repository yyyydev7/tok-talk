FROM eclipse-temurin:21-jdk AS build
WORKDIR /workspace
COPY gradlew gradlew.bat settings.gradle build.gradle ./
COPY gradle ./gradle
COPY src ./src
RUN chmod +x gradlew && ./gradlew --no-daemon installDist

FROM build AS development
ENV PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD ["./build/install/tok-talk-auth/bin/tok-talk-auth", "--healthcheck"]
CMD ["./build/install/tok-talk-auth/bin/tok-talk-auth"]

FROM eclipse-temurin:21-jre AS release
RUN groupadd --gid 10001 toktalk \
    && useradd --uid 10001 --gid 10001 --create-home toktalk
WORKDIR /app
COPY --from=build --chown=10001:10001 /workspace/build/install/tok-talk-auth/ ./
USER 10001:10001
ENV PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD ["./bin/tok-talk-auth", "--healthcheck"]
CMD ["./bin/tok-talk-auth"]
