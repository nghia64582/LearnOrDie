package com.example.sh_be.entities;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Data
@AllArgsConstructor
public class User {

    @Column(name = "username", unique = true) 
    private String username;

    private String password;

    private boolean isAdmin;
}
