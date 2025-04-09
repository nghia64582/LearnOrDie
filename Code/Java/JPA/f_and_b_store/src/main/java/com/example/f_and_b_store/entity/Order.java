package com.example.f_and_b_store.entity;

import java.time.LocalDateTime;
import java.util.List;

import jakarta.annotation.Nullable;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Data
@NoArgsConstructor
@Table(name = "order")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "created_at")
    private LocalDateTime time;

    @ManyToOne
    @JoinColumn(name = "customer_id")
    @Nullable
    private Customer customer;

    @OneToMany(mappedBy = "order")
    private List<OrderItem> items;
}
