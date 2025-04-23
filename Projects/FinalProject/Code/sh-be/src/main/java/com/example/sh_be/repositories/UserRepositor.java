package com.example.sh_be.repositories;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.example.sh_be.entities.User;

@Repository
public interface UserRepositor extends JpaRepository<User, Long> {
    // Custom query methods can be defined here if needed

}
