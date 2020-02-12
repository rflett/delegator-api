# Refactor Changelog

A list of important changes that may break things

1. Login endpoint will return `role` as its ID rather than the object
2. `GET` `/password/?token=` is now `POST` `/password/validate` `{"token": ""}`
