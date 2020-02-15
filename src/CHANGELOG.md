# Refactor Changelog

A list of important changes that may break things

1. Login endpoint will return `role` as its ID rather than the object
2. `GET` `/password/?token=` is now `POST` `/password/validate` `{"token": ""}`
3. `PUT` `/lock/<string:customer_id>` now returns `204` instead of `200`
3. `DELETE` `/lock/<string:customer_id>` now returns `204` instead of `200`
4. `PUT` `/subscription` now returns `204` instead of `200`
5. `POST` `/task/assign` now returns `204` instead of `200`
6. `POST` `/task/cancel` now returns `204` instead of `200`
7. `POST` `/task/delay` now returns `204` instead of `200`
8. `GET` `/task/delay/{id}` returns `delayed_by` as str not User
9. `POST` `/task/drop/{id}` returns `204` instead of `200`
10. `GET` `/task/{id}` response payload has changed dramatically
11. `PUT` `/task/{id}` returns `204` instead of `200`
12. `POST` `/task/{id}` returns `204` instead of `200` (create and schedule)
13. Create, Update and Delete `/task-labels` now return `204`
14. Create, Update and Delete `/task-type` returns `204`
15. Transition task returns 204
16. Create user is a 204
17. Update user settings is a 204