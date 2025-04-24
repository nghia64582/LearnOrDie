package com.example.sh_be.controllers;

import org.springframework.web.bind.annotation.*;

import com.example.sh_be.entities.User;


@RestController
@RequestMapping("/api/v1/user")
public class UserController {
    @GetMapping("/test-1")
    public String test1() {
        User a = new User("nghia", "abc", true);
        return a.getPassword();
    }

    @GetMapping("/test-2")
    public String test2() {
        User a = new User("an", "abc", true);
        return a.getUsername();
    }
}
