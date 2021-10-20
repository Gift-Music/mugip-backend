# mugip-backend

## Set-up requirement
- Python version >= 3.10
- Unix/Linux kernel (for uvloop)
- mugip-backend-environment


## Setup steps
1. `docker-compose up` in mugip-backend-environment
2. `cp ./configs/example.py ./configs/default.py`
3. `pip install -r requirements`
4. `pip install -e .[dev]` > for dev requirements
5. `alembic upgrade head` > for migration
6. `python launcher.py` > start app


## Migration guide
> If you modify table structure (include index)

> you shoud make the migration script with alembic

1. `alembic revision --autogenerate -m "migration message"`
2. Edit migration script in `migrations/versions/` and fit out style
3. `alembic upgrade +1`

If you want more information  for alembic go to this [page](https://alembic.sqlalchemy.org/en/latest/)
