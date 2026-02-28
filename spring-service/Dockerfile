FROM maven:3.9-eclipse-temurin-21 as build
WORKDIR /src
COPY pom.xml /src/pom.xml
RUN mvn -q -DskipTests package || true
COPY src /src/src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/target/sample-spring-service-0.1.0.jar /app/app.jar
EXPOSE 8080
ENTRYPOINT ["java","-jar","/app/app.jar"]
