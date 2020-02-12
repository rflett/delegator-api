# Refactor Changelog

A list of important changes that may break things

1. Login endpoint will return `role` as its ID rather than the object
2. `GET` `/password/?token=` is now `POST` `/password/validate` `{"token": ""}`
3. `PUT` `/lock/<string:customer_id>` now returns `204` instead of `200`
3. `DELETE` `/lock/<string:customer_id>` now returns `204` instead of `200`
4. `PUT` `/subscription` now returns `204` instead of `200`