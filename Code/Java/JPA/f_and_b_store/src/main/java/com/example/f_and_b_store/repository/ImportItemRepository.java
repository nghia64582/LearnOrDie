package com.example.f_and_b_store.repository;

import com.example.f_and_b_store.entity.ImportItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ImportItemRepository extends JpaRepository<ImportItem, Integer> {
    // Custom query methods can be added here if needed
}
