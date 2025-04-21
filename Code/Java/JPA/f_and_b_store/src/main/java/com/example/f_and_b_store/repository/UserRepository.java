package com.example.f_and_b_store.repository;

import com.example.f_and_b_store.entity.User;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface UserRepository extends JpaRepository<User, Integer> {
    // Custom query methods can be added here if needed
    Optional<User> findByUsername(String username);
}
