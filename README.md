# Setup

## Install UV Package Manager

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Install Python Using UV

```sh
uv python install 3.12
```

## Install Dependencies

### Local Env

```sh
uv sync
```

### On Deployment

```sh
uv sync --no-dev
```

## Database Setup

Database migrations are managed centrally by `bd-core`. See `bd-core/README.md` for migration commands.

# Run Application

## Run the Backend

```sh
uv run main.py
```
