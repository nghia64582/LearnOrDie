package com.example.draft_spring;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
public class MainController {

    @PostMapping("/git-webhook")
    public ResponseEntity<String> handleWebhook(@RequestBody String payload,
                                                @RequestHeader Map<String, String> headers) {
        String decoded = URLDecoder.decode(payload, StandardCharsets.UTF_8);
        // Optional: log headers and payload
        System.out.println("Received webhook: ");
        headers.forEach((key, value) -> System.out.println(key + ": " + value));
        System.out.println("Payload: " + decoded);

        // TODO: Add your processing logic here (e.g., parse JSON, trigger build)

        return ResponseEntity.ok("Webhook received");
    }

    @GetMapping("/hello")
    public String hello() {
        return "Hello, World!";
    }
}
