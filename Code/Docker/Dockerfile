# Use an official JDK as base image
FROM eclipse-temurin:17-jdk-alpine

# Set working directory
WORKDIR /app

# Copy the Maven wrapper files and POM to leverage caching
COPY mvnw pom.xml ./
COPY .mvn .mvn

# Download dependencies before copying source code for better caching
RUN ./mvnw dependency:go-offline

# Copy the entire project
COPY . .

# Build the application
RUN ./mvnw clean package -DskipTests

# Run the Spring Boot app
CMD ["java", "-jar", "target/your-app.jar"]
