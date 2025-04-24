package com.example.sh_be.controllers;

import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;

import org.slf4j.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import com.example.sh_be.dto.res.UserLoginOAuthDto;


@RestController
public class AuthenticationController {

    private final RestTemplate restTemplate = new RestTemplate();
    private final Logger logger = LoggerFactory.getLogger(AuthenticationController.class);
    private ConcurrentHashMap<String, CompletableFuture<UserLoginOAuthDto>> userLoginOAuthMap = new ConcurrentHashMap<>();
    private ConcurrentHashMap<String, UserLoginOAuthDto> userMap = new ConcurrentHashMap<>(); // map email => UserLoginOAuthDto
    
    @Value("${google.oauth2.client_id}")
    private String clientId;

    @Value("${google.oauth2.client_secret}")
    private String clientSecret;

    @Value("${google.oauth2.redirect_uri}")
    private String redirectUri;

    @Value("${google.oauth2.auth_uri}")
    private String authEndpoint;

    @Value("${google.oauth2.token_uri}")
    private String tokenUri;


    @GetMapping("/verify_token")
    public ResponseEntity<?> handleGoogleCallback(@RequestParam("code") String code) {
        // 1. Exchange auth code for access token
        logger.info("Received auth code: {}", code);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);

        MultiValueMap<String, String> params = new LinkedMultiValueMap<>();
        params.add("code", code);
        params.add("client_id", clientId);
        params.add("client_secret", clientSecret);
        params.add("redirect_uri", redirectUri);
        params.add("grant_type", "authorization_code");

        HttpEntity<MultiValueMap<String, String>> request = new HttpEntity<>(params, headers);

        ResponseEntity<Map> tokenResponse = restTemplate.postForEntity(tokenUri, request, Map.class);

        if (!tokenResponse.getStatusCode().is2xxSuccessful()) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body("Token exchange failed");
        }

        String accessToken = (String) tokenResponse.getBody().get("access_token");
        logger.info("Access token: {}", accessToken);

        // 2. Fetch user info using access token
        String userInfoEndpoint = "https://www.googleapis.com/oauth2/v3/userinfo";

        HttpHeaders userInfoHeaders = new HttpHeaders();
        userInfoHeaders.setBearerAuth(accessToken);

        HttpEntity<Void> userInfoRequest = new HttpEntity<>(userInfoHeaders);
        ResponseEntity<Map> userInfoResponse = restTemplate.exchange(
            userInfoEndpoint,
            HttpMethod.GET,
            userInfoRequest,
            Map.class
        );

        if (!userInfoResponse.getStatusCode().is2xxSuccessful()) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body("Failed to fetch user info");
        }

        Map<String, Object> userInfo = userInfoResponse.getBody();
        logger.info("User info: {}", userInfo);

        // 3. Store data in the map
        String email = (String) userInfo.get("email");
        String name = (String) userInfo.get("name");
        String givenName = (String) userInfo.get("given_name");
        String familyName = (String) userInfo.get("family_name");
        String picture = (String) userInfo.get("picture");
        boolean emailVerified = (boolean) userInfo.get("email_verified");
        UserLoginOAuthDto userLoginOAuthDto = new UserLoginOAuthDto(name, givenName, familyName, picture, email, emailVerified);
        userMap.put(email, userLoginOAuthDto);
        CompletableFuture<UserLoginOAuthDto> future = userLoginOAuthMap.get(email);
        if (future != null) {
            future.complete(userLoginOAuthDto);
        } else {
            CompletableFuture<UserLoginOAuthDto> newFuture = new CompletableFuture<>();
            newFuture.complete(userLoginOAuthDto);
            userLoginOAuthMap.put(email, newFuture);
        }
        
        // 4. Return or handle user info (e.g., register/login)
        return ResponseEntity.ok(userInfo);
    }

    @GetMapping("/login-oauth")
    private CompletableFuture<ResponseEntity<UserLoginOAuthDto>> loginOauthAsync(@RequestBody String email) throws InterruptedException, ExecutionException {
        // Handle the OAuth login process here
        logger.info("Received OAuth email: {}", email);
        // init userLoginOAuthMap if not exist
        if (!userLoginOAuthMap.containsKey(email)) {
            userLoginOAuthMap.put(email, new CompletableFuture<>());
        }
        CompletableFuture<UserLoginOAuthDto> future = userLoginOAuthMap.get(email);
        if (future.isDone()) {
            UserLoginOAuthDto userLoginOAuthDto = future.get();
            return CompletableFuture.completedFuture(ResponseEntity.ok(userLoginOAuthDto));
        } else {
            return future.thenApply(userDto -> ResponseEntity.ok(userDto))
                .exceptionally(ex -> ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(null));
        }
    }
}
