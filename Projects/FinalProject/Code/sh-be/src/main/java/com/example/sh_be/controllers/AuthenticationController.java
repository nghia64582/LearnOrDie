package com.example.sh_be.controllers;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AuthenticationController {

    @PostMapping("/verify_token")
    public ResponseEntity<String> verifyToken() {
        return ResponseEntity.ok("Token is valid");
    }

}
