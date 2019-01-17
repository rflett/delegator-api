insert into organisations (
    name,
    jwt_aud,
    jwt_secret
) values (
    'etemt',
    'ab585a01-6152-4eaf-af32-eba3e21d805e',
    '03dc5241a3f4a477727da827ba4b48316538ad49169954dd61a007ac42ef9c05'
);

insert into users (
    org_id,
    username,
    email,
    first_name,
    last_name,
    password,
    role
) values (
    1,
    'rflett',
    'ryan.flett1@gmail.com',
    'ryan',
    'flett',
    -- password is 'ryanflett'
    '37cc3ca4740b0bb3191fac7932c5099fe348400618f96198aa36cabfa11270d5124552c6d1fa460e1021e4654a4ccdb59d90d6d04838759ecff21263dfe39f823d4fb540edd15d528779cb85848c0a47b53a2c0b433b43601bc2596e999b8c21',
    'admin'
);
