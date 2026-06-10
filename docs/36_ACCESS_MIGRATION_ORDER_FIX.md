# Access hierarchy migration order fix

Your folder has these migrations:

```text
0001_initial_schema.py
0002_add_inspection_entries.py
0002_access_hierarchy.py
```

This is the problem: both `0002_add_inspection_entries.py` and `0002_access_hierarchy.py` were created as children of `0001_initial_schema.py`. Alembic sees two separate migration heads/branches.

The corrected chain should be:

```text
0001_initial_schema
  -> 0002_add_inspection_entries
  -> 0003_access_hierarchy
```

## Apply steps

1. Copy this patch into your project root.
2. Delete this old file:

```powershell
Remove-Item backend/alembic/versions/0002_access_hierarchy.py
```

3. Confirm this new file exists:

```powershell
ls backend/alembic/versions
```

Expected:

```text
0001_initial_schema.py
0002_add_inspection_entries.py
0003_access_hierarchy.py
```

4. Run migration:

```powershell
docker compose exec api alembic upgrade head
```

5. Restart API/frontend:

```powershell
docker compose restart api frontend
```

## If Alembic still says it cannot find revision 0002_add_inspection_entries

Open:

```text
backend/alembic/versions/0002_add_inspection_entries.py
```

Copy the exact value of:

```python
revision = "..."
```

Then open:

```text
backend/alembic/versions/0003_access_hierarchy.py
```

Set:

```python
down_revision = "that_exact_revision_value"
```

Then run `alembic upgrade head` again.
