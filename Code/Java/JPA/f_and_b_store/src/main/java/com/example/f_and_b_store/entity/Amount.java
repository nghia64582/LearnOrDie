package com.example.f_and_b_store.entity;

import jakarta.persistence.*;
import lombok.Data;

@Entity
@Data
@Table(name = "amount")
public class Amount {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @OneToOne
    @JoinColumn(name = "item_id")
    private Item item;

    @Column(name = "quantity")
    private Integer quantity;
    
}
