# Migrations

- `v0__init.sql`: initial baseline schema.
- `VERSION`: latest applied/expected migration tag.

## Rule
- New migration files must be appended as `vN__description.sql`.
- Do not rewrite old migration files after they are used in an environment.
