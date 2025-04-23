package com.example.f_and_b_store.entity;

import jakarta.persistence.*;
import lombok.Data;

@Entity
@Data
@Table(name = "import_item")
public class ImportItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @ManyToOne
    @JoinColumn(name = "import_id", nullable = false)
    private Import importSession;

}
