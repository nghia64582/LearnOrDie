package com.example.f_and_b_store.controller;

import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;

@RestController
public class FirstController {

    @GetMapping("first/hello")
    public String getMethodName() {
        return "Hello world 2";
    }
    
}
