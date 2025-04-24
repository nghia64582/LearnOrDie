package com.example.sh_be.dto.res;

import lombok.*;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserLoginOAuthDto {
    private String name;
    private String givenName;
    private String familyName;
    private String picture;
    private String email;
    private boolean emailVerified;
}
