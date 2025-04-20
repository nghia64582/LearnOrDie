package com.example.sh_be.dto.res;

import lombok.*;

@Data
@NoArgsConstructor
public class UserDto {
    private Long id;
    private String username;
    private String email;
    private String password; // Consider removing this for security reasons
    private String role;
}
