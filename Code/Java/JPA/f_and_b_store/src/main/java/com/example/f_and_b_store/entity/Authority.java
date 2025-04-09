package com.example.f_and_b_store.entity;

import jakarta.persistence.*;
import lombok.Data;

@Entity
@Data
@Table(name = "authorities")
public class Authority {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne
    @Column(name = "user_id")
    private String username;

    @Column(name = "role")
    private String role;
}
