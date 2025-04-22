package com.example.f_and_b_store.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.example.f_and_b_store.entity.Authority;

@Repository
public interface AuthorityRepository extends JpaRepository<Authority, Integer> {
    // Custom query methods can be added here if needed
}
